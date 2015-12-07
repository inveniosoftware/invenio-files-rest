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

"""Files download/upload REST API similar to S3 for Invenio."""

from __future__ import absolute_import, print_function

import uuid

from flask import Blueprint, abort, current_app, request
from invenio_db import db
from invenio_rest import ContentNegotiatedMethodView
from sqlalchemy.exc import SQLAlchemyError
from webargs import fields
from webargs.flaskparser import parser
from werkzeug import secure_filename

from .location import LocationFactory
from .models import Bucket, Location, Object
from .serializer import json_serializer
from .storage import StorageFactory

blueprint = Blueprint(
    'invenio_files_rest',
    __name__,
    url_prefix='/files'
)


class BucketCollectionResource(ContentNegotiatedMethodView):
    """"Bucket collection resource."""

    def __init__(self, serializers=None, *args, **kwargs):
        """Constructor."""
        super(BucketCollectionResource, self).__init__(
            serializers,
            *args,
            **kwargs
        )
        self.post_args = {
            'location_id': fields.Int(
                missing=None,
                location='json',
                validate=lambda val: val >= 0
            )
        }

    def get(self, **kwargs):
        """GET service that returns all the buckets.

        .. http:get:: /files

            Returns a JSON list with all the buckets.

            **Request**:

            .. sourcecode:: http

                GET /files HTTP/1.1
                Accept: */*
                Host: localhost:5000

            :reqheader Content-Type: application/json

            **Response**:

            .. sourcecode:: http

                HTTP/1.0 200 OK
                Content-Length: 999
                Content-Type: application/json

                [
                    {
                    "size": 0,
                    "url": "http://localhost:5000/files/37b1-4e1e-...-99995e8",
                    "uuid": "37b01a2d-5521-4e1e-bd76-5e28aaba8423"
                    },
                    {
                    "size": 0,
                    "url": "http://localhost:5000/files/43876228-...-9999495e",
                    "uuid": "43876228-db63-495e-8246-a38161344966"
                    }
                ]

            :resheader Content-Type: application/json
            :statuscode 200: no error
            :statuscode 400: invalid request
            :statuscode 403: access denied
        """
        bucket_list = []
        # FIXME: add pagination
        for bucket in Bucket.query.filter_by(
            deleted=False
        ).limit(1000):
            bucket_list.append(bucket.serialize())
        # FIXME: how to avoid returning a dict with key 'json'
        return {'json': bucket_list}

    def post(self, **kwargs):
        """Create bucket.

        .. http:post:: /files

            Creates a new bucket where objects can be uploaded.

            **Request**:

            .. sourcecode:: http

                POST /files HTTP/1.1
                Content-Type: application/json
                Host: localhost:5000

                {
                    "location_id": 1,
                    "url": "http://inspirehep.net"
                }

            :reqheader Content-Type: application/json
            :json body: A `location_id` can be passed (as an integer). If none
                        is passed, a random active location will be used.

            **Responses**:

            .. sourcecode:: http

                HTTP/1.0 200 OK
                Content-Length: 134
                Content-Type: application/json

                {
                    "size": 100,
                    "url": "http://localhost:5000/files/0ecc379...-9c3ef60562",
                    "uuid": "0ecc3794-2b57-4834-be61-cb9c3ef60562"
                }

            :resheader Content-Type: application/json
            :statuscode 200: no error
            :statuscode 400: invalid request
            :statuscode 403: access denied
            :statuscode 500: failed request
        """
        args = parser.parse(self.post_args, request)
        try:
            if args['location_id']:
                location = Location.query.filter_by(
                    id=args['location_id'],
                    active=True
                ).first()
            else:
                # Get one of the active locations
                location = Location.query.filter_by(
                    active=True
                ).first()
            if not location:
                abort(400, 'Invalid location.')
            bucket = Bucket(
                default_storage_class=current_app.config[
                    'FILES_REST_DEFAULT_STORAGE_CLASS'
                ],
                default_location=location.id
            )
            db.session.add(bucket)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception('Failed to create bucket.')
            abort(500, 'Failed to create bucket.')

        return {'json': bucket.serialize()}


class BucketResource(ContentNegotiatedMethodView):
    """"Bucket item resource."""

    def get(self, bucket_id, **kwargs):
        """Get list of objects in the bucket.

        .. http:get:: /files/(uuid:bucket_id)

            Returns a JSON list with all the objects in the bucket.

            **Request**:

            .. sourcecode:: http

                GET /files/0ecc3794-2b57-4834-be61-cb9c3ef60562 HTTP/1.1
                Accept: application/json
                Content-Type: application/json
                Host: localhost:5000

            :reqheader Content-Type: application/json

            **Response**:

            .. sourcecode:: http

                HTTP/1.0 200 OK
                Content-Length: 334
                Content-Type: application/json

                [
                    {
                        "checksum": "xxx",
                        "size": 110,
                        "url": "http://localhost:5000/files/c361fd5e.../f.pdf",
                        "uuid": "c361fd5e-5036-4387-8249-5fcc5a37e128"
                    },
                    {
                        "checksum": "xxx",
                        "size": 330,
                        "url": "http://localhost:5000/files/0ff1def.../f2.rst",
                        "uuid": "0ff1def0-5f09-4ba0-8ee8-ff42f99985ae"
                    }
                ]

            :resheader Content-Type: application/json
            :statuscode 200: no error
            :statuscode 403: access denied
            :statuscode 404: page not found
        """
        if bucket_id and Bucket.query.filter_by(
            id=bucket_id,
            deleted=False
        ).first():
            object_list = []
            for obj in Object.query.filter_by(
                bucket_id=bucket_id,
                deleted=False
            ).all():
                object_list.append(obj.serialize())
            return {'json': object_list}
        abort(404, 'The specified bucket does not exist or has been deleted.')

    def post(self, bucket_id, **kwargs):
        """Upload object file.

        .. http:post:: /files/(uuid:bucket_id)

            Uploads a new object file.

            **Request**:

            .. sourcecode:: http

                POST /files/14b0b1d3-71f3-4b6b-87a2-0796f1624bb6 HTTP/1.1
                Accept: */*
                Accept-Encoding: gzip, deflate
                Connection: keep-alive
                Content-Length: 15340
                Content-Type: multipart/form-data; boundary=44dea52ee18245e7...
                Host: localhost:5000

                -----------------------------44dea52ee18245e7...
                Content-Disposition: form-data; name="file"; filename="f.pdf"
                Content-Type: application/pdf

                [binary]

            :reqheader Content-Type: multipart/form-data
            :formparam file file: file object.

            **Responses**:

            .. sourcecode:: http

                HTTP/1.0 200 OK
                Content-Length: 165
                Content-Type: application/json

                {
                    "checksum": "xxxx",
                    "size": 0,
                    "url": "http://localhost:5000/files/322ea4c6-665.../f.pdf",
                    "uuid": "322ea4c6-6650-4143-a328-274eee55f45d"
                }

            :resheader Content-Type: application/json
            :statuscode 200: no error
            :statuscode 400: invalid request
            :statuscode 403: access denied
            :statuscode 500: failed request
        """
        bucket = Bucket.query.filter_by(
            id=bucket_id,
            deleted=False
        ).first()
        if bucket:
            uploaded_file = request.files['file']
            if uploaded_file:
                location_uri = bucket.location.uri
                filename = secure_filename(uploaded_file.filename)
                version_id = uuid.uuid4()
                path = LocationFactory.new(bucket_id, version_id)
                storage = StorageFactory.get(location_uri)
                file_loc = storage.save(
                    uploaded_file,
                    filename,
                    path
                )
                try:
                    obj = Object(
                        bucket_id=bucket_id,
                        filename=filename,
                        location=file_loc,
                        storage_class=bucket.default_storage_class,
                        version_id=version_id,
                        size=storage.get_size(file_loc, filename),
                    )
                    db.session.add(obj)
                    db.session.commit()
                    return {'json': obj.serialize()}
                except SQLAlchemyError:
                    db.session.rollback()
                    current_app.logger.exception('Failed to create object.')
                    abort(500, 'Failed to create object.')
            abort(400, 'Missing uploaded file.')
        else:
            abort(
                404,
                'The specified bucket does not exist or has been deleted.'
            )

    def delete(self, bucket_id, **kwargs):
        """Set bucket, and all files inside it, as deleted.

        .. http:head:: /files/(uuid:bucket_id)

            Deletes bucket if it exists.

            **Request**:

            .. sourcecode:: http

                DELETE /files/14b0b1d3-71f3-4b6b-87a2-0796f1624bb6 HTTP/1.1
                Accept: application/json
                Content-Type: application/json
                Host: localhost:5000

            :reqheader Content-Type: application/json

            **Response**:

            .. sourcecode:: http

                HTTP/1.0 200 OK
                Content-Length: 0
                Content-Type: application/json

            .. sourcecode:: http

                HTTP/1.0 500 INTERNAL SERVER ERROR
                Content-Type: application/json

            :resheader Content-Type: application/json
            :statuscode 200: no error
            :statuscode 403: access denied
            :statuscode 404: page not found
            :statuscode 500: exception while deleting
        """
        try:
            bucket = Bucket.query.filter_by(
                id=bucket_id,
                deleted=False
            ).first()
            if bucket:
                bucket.deleted = True
                for obj in Object.query.filter_by(
                    bucket_id=bucket_id,
                    deleted=False
                ).all():
                    obj.deleted = True
                db.session.commit()
            else:
                abort(
                    404,
                    'The specified bucket does not exist or has already been '
                    'deleted.'
                )
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception('Failed to delete bucket.')
            abort(500, 'Failed to delete bucket.')

    def head(self, bucket_id=None, **kwargs):
        """Check the existence of the bucket.

        .. http:head:: /files/(uuid:bucket_id)

            Checks if the bucket exists.

            **Request**:

            .. sourcecode:: http

                HEAD /files/98ff05d2-58bb-441b-9fc6-2a1992275158 HTTP/1.1
                Accept: application/json
                Content-Type: application/json
                Host: localhost:5000

            :reqheader Content-Type: application/json

            **Response**:

            .. sourcecode:: http

                HTTP/1.0 200 OK
                Content-Length: 0
                Content-Type: application/json

            .. sourcecode:: http

                HTTP/1.0 404 NOT FOUND
                Content-Length: 0
                Content-Type: text/html

            :resheader Content-Type: application/json
            :statuscode 200: the bucket exists
            :statuscode 403: access denied
            :statuscode 404: the bucket does not exist
        """
        if not bucket_id or not Bucket.query.filter_by(
            id=bucket_id,
            deleted=False
        ).first():
            abort(404, 'This bucket does not exist or has been deleted.')


class ObjectResource(ContentNegotiatedMethodView):
    """"Object item resource."""

    def get(self, version_id, filename, **kwargs):
        """Get object.

        .. http:get:: /files/(uuid:version_id)/(string:filename)

            Sends file to the client.

            **Request**:

            .. sourcecode:: http

                GET /files/4b60f39d-b960-442f-be68-b4b8b04c38a9/f.pdf HTTP/1.1
                Accept: application/json
                Connection: keep-alive
                Content-Type: application/json
                Host: localhost:5000

            :reqheader Content-Type: application/json

            **Response**:

            .. sourcecode:: http

                HTTP/1.0 200 OK
                Content-Type: application/pdf
                ETag: "flask-1449350517.0-15192-1285496294"

                Downloading to "f.pdf"

            :resheader Content-Type: application/json
            :statuscode 200: no error
            :statuscode 403: access denied
            :statuscode 404: page not found
        """
        obj = Object.query.filter_by(
            version_id=str(version_id),
            filename=filename,
            deleted=False
        ).first()
        if obj:
            storage = StorageFactory.get(obj.location)
            return storage.send_file(obj.filename)
        abort(404, 'This object file does not exist or has been deleted.')

    def put(self, version_id, filename, **kwargs):
        """Upload new version of a file.

        .. http:put:: /files/(uuid:version_id)/(string:filename)

            Uploads a new version of an object file using the same URL as to
            download it.

            **Request**:

            .. sourcecode:: http

                PUT /files/2d4f8e99-1aa7-400f-b649-f1c570fc61fb/f.pdf HTTP/1.1
                Accept: */*
                Accept-Encoding: gzip, deflate
                Connection: keep-alive
                Content-Length: 15340
                Content-Type: multipart/form-data; boundary=cd134c08b9974cff...
                Host: localhost:5000

                -----------------------------cd134c08b9974cff81d86b5257b3cc5f
                Content-Disposition: form-data; name="file"; filename="f.pdf"
                Content-Type: application/pdf

                [binary]

            :reqheader Content-Type: multipart/form-data
            :formparam file file: file object.

            **Responses**:

            .. sourcecode:: http

                HTTP/1.0 200 OK
                Content-Length: 165
                Content-Type: application/json

                {
                    "checksum": null,
                    "size": 0,
                    "url": "http://localhost:5000/files/8ed32f12-be8.../f.pdf",
                    "uuid": "8ed32f12-be8e-47e2-b4cc-35802b6fe1de"
                }

            :resheader Content-Type: application/json
            :statuscode 200: no error
            :statuscode 400: invalid request
            :statuscode 403: access denied
            :statuscode 500: failed request
        """
        obj = Object.query.filter_by(
            version_id=str(version_id),
            filename=filename,
            deleted=False
        ).first()
        if obj:
            uploaded_file = request.files['file']
            if uploaded_file:
                location_uri = obj.bucket.location.uri
                filename = secure_filename(uploaded_file.filename)
                version_id = uuid.uuid4()
                path = LocationFactory.new(obj.bucket_id, version_id)
                storage = StorageFactory.get(location_uri)
                file_loc = storage.save(
                    uploaded_file,
                    filename,
                    path
                )
                try:
                    obj = Object(
                        id=obj.id,
                        bucket_id=obj.bucket_id,
                        filename=filename,
                        location=file_loc,
                        storage_class=obj.bucket.default_storage_class,
                        version_id=version_id,
                        size=storage.get_size(file_loc, filename),
                    )
                    db.session.add(obj)
                    db.session.commit()
                    return {'json': obj.serialize()}
                except SQLAlchemyError:
                    db.session.rollback()
                    current_app.logger.exception('Failed to create object.')
                    abort(500, 'Failed to create object.')
            abort(400, 'Missing uploaded file.')
        else:
            abort(
                404,
                'The specified object file does not exist or has been '
                'deleted.'
            )

    def delete(self, version_id, filename, **kwargs):
        """Set object file as deleted.

        .. http:head:: /files/(uuid:version_id)/(string:filename)

            Deletes file if it exists.

            **Request**:

            .. sourcecode:: http

                DELETE /files/0dde7eb7-e2af-4777-8cb9-29a3480e22/f.pdf HTTP/1.1
                Accept: application/json
                Content-Length: 0
                Content-Type: application/json
                Host: localhost:5000

            :reqheader Content-Type: application/json

            **Response**:

            .. sourcecode:: http

                HTTP/1.0 200 OK
                Content-Length: 0
                Content-Type: application/json

            .. sourcecode:: http

                HTTP/1.0 500 INTERNAL SERVER ERROR
                Content-Type: application/json

            :resheader Content-Type: application/json
            :statuscode 200: no error
            :statuscode 403: access denied
            :statuscode 404: page not found
            :statuscode 500: exception while deleting
        """
        try:
            obj = Object.query.filter_by(
                version_id=version_id,
                filename=filename,
                deleted=False
            ).first()
            if obj:
                obj.deleted = True
                db.session.commit()
            else:
                abort(
                    404,
                    'The specified object does not exist or has already been '
                    'deleted.'
                )
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception('Failed to delete object.')
            abort(500, 'Failed to delete object.')

    def head(self, version_id, filename, **kwargs):
        """Check the existence of the object file.

        .. http:head:: /files/(uuid:version_id)/(string:filename)

            Checks if the file exists.

            **Request**:

            .. sourcecode:: http

                HEAD /files/4b60f39d-b960-442f-be68-b4b8b04c38a9/f.pdf HTTP/1.1
                Content-Type: application/json
                Host: localhost:5000

            :reqheader Content-Type: application/json

            **Response**:

            .. sourcecode:: http

                HTTP/1.0 200 OK
                Content-Length: 0
                Content-Type: application/json

            .. sourcecode:: http

                HTTP/1.0 404 NOT FOUND
                Content-Length: 0
                Content-Type: text/html

            :resheader Content-Type: application/json
            :statuscode 200: the file exists
            :statuscode 403: access denied
            :statuscode 404: the file does not exist
        """
        if not version_id or not Object.query.filter_by(
            version_id=version_id,
            filename=filename,
            deleted=False
        ).first():
            abort(404, 'The object file does not exist or has been deleted.')


serializers = {'application/json': json_serializer}

bucket_collection_view = BucketCollectionResource.as_view(
    'bucket_collection_api',
    serializers=serializers
)
bucket_view = BucketResource.as_view(
    'bucket_api',
    serializers=serializers
)
object_view = ObjectResource.as_view(
    'object_api',
    serializers=serializers
)

blueprint.add_url_rule(
    '',
    view_func=bucket_collection_view,
    methods=['GET', 'POST']
)
blueprint.add_url_rule(
    '/<string:bucket_id>',
    view_func=bucket_view,
    methods=['GET', 'POST', 'DELETE', 'HEAD']
)
blueprint.add_url_rule(
    '/<string:version_id>/<string:filename>',
    view_func=object_view,
    methods=['GET', 'PUT', 'DELETE', 'HEAD']
)
