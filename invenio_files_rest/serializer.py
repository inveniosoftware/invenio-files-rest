# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""REST API serializers."""

import json

from flask import Response, current_app, url_for, request
from marshmallow import Schema, fields, missing, post_dump

from .models import Bucket, MultipartObject, ObjectVersion, Part


class BaseSchema(Schema):
    """Base schema for all serializations."""

    created = fields.DateTime(dump_only=True)
    updated = fields.DateTime(dump_only=True)
    links = fields.Method('dump_links', dump_only=True)

    def dump_links(self, o):
        """Base links."""
        return missing


class BucketSchema(BaseSchema):
    """Schema for bucket."""

    id = fields.UUID()
    size = fields.Integer()
    quota_size = fields.Integer()
    max_file_size = fields.Integer()
    locked = fields.Boolean()

    def dump_links(self, o):
        """Dump links."""
        return {
            'self': url_for('.bucket_api', bucket_id=o.id, _external=True),
            'versions': url_for(
                '.bucket_api', bucket_id=o.id, _external=True) + '?versions',
            'uploads': url_for(
                '.bucket_api', bucket_id=o.id, _external=True) + '?uploads',
        }


class ObjectVersionSchema(BaseSchema):
    """Schema for ObjectVersions."""

    key = fields.Str()
    version_id = fields.UUID()
    is_head = fields.Boolean()
    mimetype = fields.Str()
    size = fields.Integer(attribute='file.size')
    checksum = fields.Integer(attribute='file.checksum')
    delete_marker = fields.Boolean(attribute='deleted')

    def dump_links(self, o):
        """Dump links."""
        params = {}
        if not o.is_head or o.deleted:
            params = {'versionId': o.version_id}
        data = {
            'self': url_for(
                '.object_api',
                bucket_id=o.bucket_id,
                key=o.key,
                _external=True,
                **params
            )
        }

        if o.is_head and not o.deleted:
            data.update({'uploads': url_for(
                '.object_api',
                bucket_id=o.bucket_id,
                key=o.key,
                _external=True
            ) + '?uploads', })

        return data

    @post_dump(pass_many=True)
    def wrap(self, data, many):
        """Wrap response in envelope."""
        if not many:
            return data
        else:
            data = {'contents': data}
            bucket = self.context.get('bucket')
            if bucket:
                data.update(BucketSchema().dump(bucket).data)
            return data


class MultipartObjectSchema(BaseSchema):
    """Schema for ObjectVersions."""

    _endpoint = '.object_api'

    id = fields.UUID(attribute='upload_id', dump_only=True)
    bucket = fields.UUID(attribute='bucket_id', dump_only=True)
    key = fields.Str(dump_only=True)
    completed = fields.Boolean(dump_only=True)
    size = fields.Integer()
    part_size = fields.Integer(attribute='chunk_size')
    last_part_number = fields.Integer(dump_only=True)
    last_part_size = fields.Integer(dump_only=True)

    def dump_links(self, o):
        """Dump links."""
        links = {
            'self': url_for(
                '.object_api',
                bucket_id=o.bucket_id,
                key=o.key,
                uploadId=o.upload_id,
                _external=True,
            ),
            'object': url_for(
                '.object_api',
                bucket_id=o.bucket_id,
                key=o.key,
                _external=True,
            ),
        }

        bucket = self.context.get('bucket')
        if bucket:
            links.update({
                'bucket': url_for(
                    '.bucket_api',
                    bucket_id=o.bucket_id,
                    _external=True,
                )
            })

        return links


class PartSchema(BaseSchema):
    """Schema for parts."""

    part_number = fields.Integer()
    start_byte = fields.Integer()
    end_byte = fields.Integer()
    checksum = fields.Str()

    links = None

    @post_dump(pass_many=True)
    def wrap(self, data, many):
        """Wrap response in envelope."""
        if not many:
            return data
        else:
            data = {'parts': data}
            multipart = self.context.get('multipart')
            if multipart:
                data.update(MultipartObjectSchema(context={
                    'bucket': multipart.bucket}).dump(multipart).data)
            return data


serializer_mapping = {
    Bucket: BucketSchema,
    ObjectVersion: ObjectVersionSchema,
    MultipartObject: MultipartObjectSchema,
    Part: PartSchema,
}


def schema_from_context(context):
    """Determine which schema to use."""
    item_class = context.get('class')
    return (
        serializer_mapping[item_class] if item_class else BaseSchema,
        context.get('many', False)
    )


def _format_args():
    try:
        pretty_format = \
            current_app.config['JSONIFY_PRETTYPRINT_REGULAR'] and \
            not request.is_xhr
    except RuntimeError:
        pretty_format = False

    if pretty_format:
        return dict(
            indent=2,
            separators=(', ', ': '),
        )
    else:
        return dict(
            indent=None,
            separators=(',', ':'),
        )


def json_serializer(data=None, code=200, headers=None, context=None,
                    etag=None):
    """Build a json flask response using the given data.

    :returns: A flask response with json data.
    :returns type: :py:class:`flask.Response`
    """
    schema_class, many = schema_from_context(context or {})

    if data is not None:
        response = Response(
            json.dumps(
                schema_class(context=context).dump(data, many=many).data,
                **_format_args()
            ),
            mimetype='application/json'
        )
    else:
        response = Response(mimetype='application/json')

    response.status_code = code
    if headers is not None:
        response.headers.extend(headers)

    if etag:
        response.set_etag(etag)

    return response
