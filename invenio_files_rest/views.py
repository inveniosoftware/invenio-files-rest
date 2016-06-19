# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
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

"""Files download/upload REST API similar to S3 for Invenio."""

from __future__ import absolute_import, print_function

import uuid
from functools import partial, wraps

from flask import Blueprint, abort, current_app, request
from flask_login import current_user
from invenio_db import db
from invenio_rest import ContentNegotiatedMethodView
from webargs import fields
from webargs.flaskparser import parser, use_kwargs
from werkzeug.exceptions import UnprocessableEntity

from .errors import FileSizeError, MultipartInvalidChunkSize, \
    MultipartInvalidPartNumber
from .models import Bucket, MultipartObject, ObjectVersion, Part
from .proxies import current_files_rest, current_permission_factory
from .serializer import json_serializer
from .signals import file_downloaded
from .tasks import merge_multipartobject, remove_file_data

blueprint = Blueprint(
    'invenio_files_rest',
    __name__,
    url_prefix='/files'
)

default_partnumber_schema = {
    'part_number': fields.Int(
        load_from='partNumber',
        location='query',
        required=True,
    ),
}

ngfileupload_partnumber_schema = {
    'part_number': fields.Int(
        load_from='_chunkNumber',
        location='query',
        required=True,
    ),
}


def as_uuid(val):
    """Convert to UUID."""
    try:
        return uuid.UUID(val)
    except ValueError:
        abort(404)


def minsize_validator(val):
    """Validate Content-Length header."""
    if val < current_app.config['FILES_REST_MIN_FILE_SIZE']:
        raise FileSizeError()


def pass_bucket(f):
    """Decorator to retrieve a bucket."""
    @wraps(f)
    def decorate(*args, **kwargs):
        bucket_id = kwargs.pop('bucket_id')
        bucket = Bucket.get(as_uuid(bucket_id))
        if not bucket:
            abort(404, 'Bucket does not exist.')
        return f(bucket=bucket, *args, **kwargs)
    return decorate


def pass_multipart(with_completed=False):
    """Decorator to retrieve an object."""
    def decorate(f):
        @wraps(f)
        def inner(self, bucket, key, upload_id, *args, **kwargs):
            obj = MultipartObject.get(
                bucket, key, upload_id, with_completed=with_completed)
            if obj is None:
                abort(404, 'uploadId does not exists.')
            return f(self, obj, *args, **kwargs)
        return inner
    return decorate


def check_permission(permission, hidden=True):
    """Check if permission is allowed.

    :param hidden: Determine if a 404 error (``True``) or 401/403 error
        (``False``) should be returned if the permission is rejected (i.e.
        hide or reveal the existence of a particular object).

    if existence of a particular object should be
        hidden if the permission is
    """
    if permission is not None and not permission.can():
        if hidden:
            abort(404)
        else:
            if current_user.is_authenticated:
                abort(403,
                      'You do not have a permission for this action')
            abort(401)


def need_permissions(object_getter, action, hidden=True):
    """"Get permission for buckets or abort."""
    def decorator_builder(f):
        @wraps(f)
        def decorate(*args, **kwargs):
            check_permission(current_permission_factory(
                object_getter(*args, **kwargs),
                action(*args, **kwargs) if callable(action) else action,

            ), hidden=hidden)
            return f(*args, **kwargs)
        return decorate
    return decorator_builder


need_location_permission = partial(
    need_permissions,
    lambda *args, **kwargs: kwargs.get('location')
)


need_bucket_permission = partial(
    need_permissions,
    lambda *args, **kwargs: kwargs.get('bucket')
)


def file_download_ui(pid, record, **kwargs):
    """File download view for a given record.

    Plug this method into your ``RECORDS_UI_ENDPOINTS`` configuration:

    .. code-block:: python

        RECORDS_UI_ENDPOINTS = dict(
            recid=dict(
                # ...
                route='/records/<pid_value/files/<filename>',
                view_imp='invenio_files_rest.views.file_download_ui',
                record_class='invenio_records_files.api:Record',
            )
        )
    """
    # Extract file from record.
    fileobj = current_files_rest.record_file_factory(
        pid, record, request.view_args.get('filename'))
    if not fileobj:
        abort(404)

    # Send file.
    return ObjectResource.send_object(
        fileobj.bucket, fileobj,
        expected_chksum=fileobj.get('checksum'),
        logger_data=dict(
            bucket_id=fileobj.bucket_id,
            pid_type=pid.pid_type,
            pid_value=pid.pid_value,
        ))


class LocationResource(ContentNegotiatedMethodView):
    """"Service resource."""

    @need_location_permission('location-update', hidden=False)
    def post(self):
        """Create bucket."""
        with db.session.begin_nested():
            bucket = Bucket.create(
                storage_class=current_app.config[
                    'FILES_REST_DEFAULT_STORAGE_CLASS'
                ],
            )
        db.session.commit()
        return self.make_response(
            data=bucket,
            context={
                'class': Bucket,
            }
        )


class BucketResource(ContentNegotiatedMethodView):
    """"Bucket item resource."""

    get_args = {
        'versions': fields.Raw(
            location='query',
            missing=False,
        ),
        'uploads': fields.Raw(
            location='query',
            missing=False,
        )
    }

    @need_permissions(lambda self, bucket: bucket, 'bucket-listmultiparts')
    def multipart_listuploads(self, bucket):
        """List objects in a bucket."""
        return self.make_response(
            data=MultipartObject.query_by_bucket(bucket).limit(1000).all(),
            context={
                'class': MultipartObject,
                'bucket': bucket,
                'many': True,
            }
        )

    @need_permissions(
        lambda self, bucket, versions: bucket,
        'bucket-read',
    )
    def listobjects(self, bucket, versions):
        """List objects in a bucket."""
        if versions is not False:
            check_permission(
                current_permission_factory(bucket, 'bucket-read-versions'),
                hidden=False
            )
        return self.make_response(
            data=ObjectVersion.get_by_bucket(
                bucket.id, versions=versions is not False).limit(1000).all(),
            context={
                'class': ObjectVersion,
                'bucket': bucket,
                'many': True,
            }
        )

    @use_kwargs(get_args)
    @pass_bucket
    def get(self, bucket=None, versions=None, uploads=None):
        """Get list of objects in the bucket."""
        if uploads is not False:
            return self.multipart_listuploads(bucket)
        else:
            return self.listobjects(bucket, versions)

    @pass_bucket
    @need_bucket_permission('bucket-read')
    def head(self, bucket=None, **kwargs):
        """Check the existence of the bucket."""


class ObjectResource(ContentNegotiatedMethodView):
    """"Object item resource."""

    get_args = {
        'version_id': fields.UUID(
            location='query',
            load_from='versionId',
            missing=None,
        ),
        'upload_id': fields.UUID(
            location='query',
            load_from='uploadId',
            missing=None,
        )
    }

    delete_args = get_args

    post_args = {
        'uploads': fields.Raw(
            location='query',
            missing=False,
        ),
        'upload_id': fields.UUID(
            location='query',
            load_from='uploadId',
            missing=None,
        )
    }

    put_args = {
        'upload_id': fields.UUID(
            location='query',
            load_from='uploadId',
            missing=None,
        ),
    }

    upload_headers = {
        'content_md5': fields.Str(
            load_from='Content-MD5',
            location='headers',
            missing=None,
        ),
        'content_length': fields.Int(
            load_from='Content-Length',
            location='headers',
            required=True,
            validate=minsize_validator,

        )
    }

    multipart_init_args = {
        'size': fields.Int(
            locations=('query', 'json'),
            required=True,
        ),
        'part_size': fields.Int(
            locations=('query', 'json'),
            required=True,
        ),
    }

    #
    # ObjectVersion helpers
    #
    @staticmethod
    def get_object(bucket, key, version_id):
        """Retrieve object and abort if it doesn't exists."""
        obj = ObjectVersion.get(bucket, key, version_id=version_id)
        if not obj:
            abort(404, 'Object does not exists.')

        check_permission(current_permission_factory(
            obj,
            'object-read'
        ))
        if not obj.is_head:
            check_permission(
                current_permission_factory(obj, 'object-read-version'),
                hidden=False
            )
        return obj

    @staticmethod
    @use_kwargs(upload_headers)
    def create_object(bucket, key, uploaded_file=None, content_md5=None,
                      content_length=None):
        """Create a new object."""
        # Initial validation of size based on Content-Length.
        # User can tamper with Content-Length, so this is just an initial up
        # front check. The storage subsystem must validate the size limit as
        # well.
        size_limit = bucket.size_limit
        if size_limit and content_length > size_limit:
            desc = 'File size limit exceeded.' \
                if isinstance(size_limit, int) else size_limit.reason
            raise FileSizeError(description=desc)

        with db.session.begin_nested():
            obj = ObjectVersion.create(bucket, key)
            obj.set_contents(
                request.stream, size=content_length, size_limit=size_limit)
        db.session.commit()
        return obj

    @need_permissions(
        lambda self, bucket, obj, *args: obj,
        'object-delete',
        hidden=False,  # Because get_object permission check has already run
    )
    def delete_object(self, bucket, obj, version_id):
        """Delete an existing object."""
        if version_id is None:
            # Create a delete marker.
            with db.session.begin_nested():
                ObjectVersion.delete(bucket, obj.key)
            db.session.commit()
        else:
            # Permanently delete specific object version.
            check_permission(
                current_permission_factory(bucket, 'object-delete-version'),
                hidden=False,
            )
            obj.remove()
            db.session.commit()
            if obj.file_id:
                remove_file_data.delay(str(obj.file_id))

        return self.make_response('', 204)

    @staticmethod
    def send_object(bucket, obj, expected_chksum=None, logger_data=None,
                    restricted=True):
        """Send an object for a given bucket."""
        if not obj.is_head:
            check_permission(
                current_permission_factory(obj, 'object-read-version'),
                hidden=False
            )

        if expected_chksum and obj.file.checksum != expected_chksum:
            current_app.logger.warning(
                'File checksum mismatch detected.', extra=logger_data)

        file_downloaded.send(current_app._get_current_object(), obj=obj)
        return obj.send_file(restricted=restricted)

    #
    # MultipartObject helpers
    #
    @pass_multipart(with_completed=True)
    @need_permissions(
        lambda self, multipart: multipart,
        'multipart-read'
    )
    def multipart_listparts(self, multipart):
        """Get parts of a multpart upload."""
        return self.make_response(
            data=Part.query_by_multipart(
                multipart).order_by(Part.part_number).limit(1000).all(),
            context={
                'class': Part,
                'multipart': multipart,
                'many': True,
            }
        )

    @use_kwargs(multipart_init_args)
    def multipart_init(self, bucket, key, size=None, part_size=None):
        """Initiate a multipart upload."""
        multipart = MultipartObject.create(bucket, key, size, part_size)
        db.session.commit()
        return self.make_response(
            data=multipart,
            context={
                'class': MultipartObject,
                'bucket': bucket,
            }
        )

    @use_kwargs(upload_headers)
    @pass_multipart(with_completed=True)
    def multipart_uploadpart(self, multipart, content_md5=None,
                             content_length=None):
        """Upload a part."""
        if content_length != multipart.chunk_size:
            raise MultipartInvalidChunkSize()

        # Extract part number from request.
        data = None
        for schema in current_files_rest.uploadparts_schema_factory:
            try:
                data = parser.parse(schema)
                if data:
                    break
            except UnprocessableEntity:
                pass

        if not data or data.get('part_number') is None:
            raise MultipartInvalidPartNumber()
        part_number = data['part_number']

        # Create part
        try:
            p = Part.get_or_create(multipart, part_number)
            p.set_contents(request.stream)
            db.session.commit()
        except Exception:
            # We remove the Part since incomplete data may have been written to
            # disk (e.g. client closed connection etc.)
            db.session.rollback()
            Part.delete(multipart, part_number)
            raise
        return self.make_response(
            data=p,
            context={
                'class': Part,
            },
            etag=p.checksum
        )

    @pass_multipart(with_completed=True)
    def multipart_complete(self, multipart):
        """Complete a multipart upload."""
        multipart.complete()
        db.session.commit()
        merge_multipartobject.delay(str(multipart.upload_id))
        return self.make_response(
            data=multipart,
            context={
                'class': MultipartObject,
                'bucket': multipart.bucket,
            }
        )

    @pass_multipart()
    @need_permissions(
        lambda self, multipart: multipart,
        'multipart-delete',
    )
    def multipart_delete(self, multipart):
        """Abort a multipart upload."""
        multipart.delete()
        db.session.commit()
        if multipart.file_id:
            remove_file_data.delay(str(multipart.file_id))
        return self.make_response('', 204)

    #
    # HTTP methods implementations
    #
    @use_kwargs(get_args)
    @pass_bucket
    def get(self, bucket=None, key=None, version_id=None, upload_id=None):
        """Get object or list parts of a multpart upload."""
        if upload_id:
            return self.multipart_listparts(bucket, key, upload_id)
        else:
            obj = self.get_object(bucket, key, version_id)
            return self.send_object(bucket, obj)

    @use_kwargs(post_args)
    @pass_bucket
    @need_bucket_permission('bucket-update')
    def post(self, bucket=None, key=None, uploads=None, upload_id=None):
        """Upload a new object or start/complete a multipart upload."""
        if uploads is not False:
            return self.multipart_init(bucket, key)
        elif upload_id is not None:
            return self.multipart_complete(bucket, key, upload_id)
        abort(403)

    @use_kwargs(put_args)
    @pass_bucket
    @need_bucket_permission('bucket-update')
    def put(self, bucket=None, key=None, upload_id=None):
        """Update a new object or upload a part of a multipart upload."""
        if upload_id is not None:
            return self.multipart_uploadpart(bucket, key, upload_id)
        else:
            return self.create_object(bucket, key)

    @use_kwargs(delete_args)
    @pass_bucket
    def delete(self, bucket=None, key=None, version_id=None, upload_id=None):
        """Delete an object or abort a multipart upload."""
        if upload_id is not None:
            return self.multipart_delete(bucket, key, upload_id)
        else:
            obj = self.get_object(bucket, key, version_id)
            return self.delete_object(bucket, obj, version_id)

#
# Blueprint definition
#
location_view = LocationResource.as_view(
    'location_api',
    serializers={
        'application/json': json_serializer,
    }
)
bucket_view = BucketResource.as_view(
    'bucket_api',
    serializers={
        'application/json': json_serializer,
    }
)
object_view = ObjectResource.as_view(
    'object_api',
    serializers={
        'application/json': json_serializer,
    }
)

blueprint.add_url_rule(
    '',
    view_func=location_view,
    methods=['GET', 'POST']
)
blueprint.add_url_rule(
    '/<string:bucket_id>',
    view_func=bucket_view,
    methods=['GET', 'PUT', 'DELETE', 'HEAD']
)
blueprint.add_url_rule(
    '/<string:bucket_id>/<path:key>',
    view_func=object_view,
    methods=['GET', 'POST', 'PUT', 'DELETE', 'HEAD']
)
