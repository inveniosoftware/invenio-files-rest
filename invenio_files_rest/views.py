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

import mimetypes
from collections import namedtuple
from functools import partial, wraps

from flask import Blueprint, abort, current_app, request, url_for
from flask_login import current_user
from invenio_db import db
from invenio_rest import ContentNegotiatedMethodView
from sqlalchemy.exc import SQLAlchemyError
from webargs import fields
from webargs.flaskparser import parser, use_kwargs
from werkzeug.local import LocalProxy

from .errors import FileSizeError, UnexpectedFileSizeError
from .models import Bucket, Location, ObjectVersion
from .proxies import current_bucket_collection_permission_factory, \
    current_bucket_permission_factory, current_files_rest, \
    current_object_permission_factory
from .serializer import bucket_collection_serializer, bucket_serializer, \
    json_serializer, object_serializer
from .signals import file_downloaded

blueprint = Blueprint(
    'invenio_files_rest',
    __name__,
    url_prefix='/files'
)


def pass_bucket(f):
    """Decorator to retrieve a bucket."""
    @wraps(f)
    def decorate(*args, **kwargs):
        bucket_id = kwargs.pop('bucket_id')
        bucket = Bucket.get(bucket_id)
        if not bucket:
            abort(404, 'Bucket does not exist.')
        return f(bucket=bucket, *args, **kwargs)
    return decorate


def pass_object(f):
    """Decorator to retrieve an object."""
    @wraps(f)
    def decorate(*args, **kwargs):
        key = kwargs.pop('key')
        obj = ObjectVersion.get(kwargs['bucket'].id, key)
        if not obj:
            obj = namedtuple('mock_obj', ('key'))(None)
        return f(obj=obj, *args, **kwargs)
    return decorate


def pass_file(f):
    """Decorator to retrieve uploaded file."""
    @wraps(f)
    def decorate(*args, **kwargs):
        uploaded_file = request.files.get('file')
        if not uploaded_file:
            abort(400, 'File is missing from the request.')
        return f(uploaded_file=uploaded_file, *args, **kwargs)
    return decorate


def need_permissions(factory, action):
    """"Get permission for buckets or abort."""
    def decorator_builder(f):
        @wraps(f)
        def decorate(*args, **kwargs):
            permission = factory(kwargs, action)
            if permission is not None and not permission.can():
                if current_user.is_authenticated:
                    abort(403,
                          'You do not have a permission for this action')
                abort(401)
            return f(*args, **kwargs)
        return decorate
    return decorator_builder


need_bucket_collection_permission = partial(
    need_permissions,
    lambda kwargs, action: current_bucket_collection_permission_factory(action)
)


need_bucket_permission = partial(
    need_permissions,
    lambda kwargs, action: current_bucket_permission_factory(
        kwargs['bucket'], action=action
    )
)


need_objects_permission = partial(
    need_permissions,
    lambda kwargs, action: current_object_permission_factory(
        kwargs['bucket'],
        kwargs['obj'].key,
        action=action
    )
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


class BucketCollectionResource(ContentNegotiatedMethodView):
    """"Bucket collection resource."""

    post_args = {
        'location_name': fields.String(
            missing=None,
            location='json'
        )
    }

    def __init__(self, serializers=None, *args, **kwargs):
        """Constructor."""
        super(BucketCollectionResource, self).__init__(
            serializers,
            *args,
            **kwargs
        )

    @need_bucket_collection_permission('bucket-collection-read')
    def get(self, **kwargs):
        """List all the buckets.

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
        # TODO: Only get buckets that user has permission to.
        return Bucket.all()

    @use_kwargs(post_args)
    @need_bucket_collection_permission('bucket-collection-bucket-create')
    def post(self, location_name):
        """Create bucket.

        .. http:post:: /files

            Creates a new bucket where objects can be uploaded. A specific
            location can be passed through JSON.

            **Request**:

            .. sourcecode:: http

                POST /files HTTP/1.1
                Content-Type: application/json
                Host: localhost:5000

                {
                    "location_name": "storage_one"
                }

            :reqheader Content-Type: application/json
            :json body: A `location_name` can be passed (as an string). If none
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
        with db.session.begin_nested():
            bucket = Bucket.create(
                storage_class=current_app.config[
                    'FILES_REST_DEFAULT_STORAGE_CLASS'
                ],
                location=location_name
            )
        db.session.commit()

        return bucket


class BucketResource(ContentNegotiatedMethodView):
    """"Bucket item resource."""

    get_args = {
        'versions': fields.Boolean(
            location='query',
            missing=False,
        )
    }

    def __init__(self, serializers=None, *args, **kwargs):
        """Constructor."""
        super(BucketResource, self).__init__(
            serializers,
            *args,
            **kwargs
        )

    @use_kwargs(get_args)
    @pass_bucket
    @need_bucket_permission('bucket-read')
    def get(self, versions, bucket=None, **kwargs):
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
            :query boolean versions: 1 (or true) in order to  list all the
                                     versions of the files. 0 (or false) for
                                     the most recent versions of each file.

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
        return ObjectVersion.get_by_bucket(bucket.id, versions=versions)

    @pass_bucket
    @need_bucket_permission('bucket-delete')
    def delete(self, bucket=None, **kwargs):
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
        Bucket.delete(bucket.id)
        db.session.commit()

    @pass_bucket
    @need_bucket_permission('bucket-read')
    def head(self, bucket=None, **kwargs):
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
        pass


class ObjectResource(ContentNegotiatedMethodView):
    """"Object item resource."""

    get_args = dict(
        version_id=fields.UUID(
            location='query',
            load_from='versionId'),
    )
    """GET query arguments."""

    post_args = {}

    put_args = dict(
        content_md5=fields.Str(
            load_from='Content-MD5',
            location='headers', ),
    )
    """PUT header arguments."""

    def __init__(self, serializers=None, *args, **kwargs):
        """Constructor."""
        super(ObjectResource, self).__init__(
            serializers,
            *args,
            **kwargs
        )

    @classmethod
    def send_object(cls, bucket, obj, version_id=None, expected_chksum=None,
                    logger_data=None):
        """Send an object for a given bucket."""
        permission = current_object_permission_factory(
            bucket,
            obj.key,
            action='objects-read'
        )

        if permission is not None and not permission.can():
            if current_user.is_authenticated:
                abort(403, 'You do not have permissions to download the file.')
            # TODO: Send user to login page. (not for REST API)
            abort(401)

        if not ObjectVersion.exists(bucket.id, obj.key):
            abort(404, 'Object does not exist.')

        if expected_chksum and obj.file.checksum != expected_chksum:
            current_app.logger.warning(
                'File checksum mismatch detected.', extra=logger_data)

        file_downloaded.send(current_app._get_current_object(), obj=obj)
        return obj.file.send_file(mimetype=obj.mimetype)

    @use_kwargs(get_args)
    @pass_bucket
    @pass_object
    def get(self, bucket=None, obj=None, version_id=None, **kwargs):
        """Get object.

        .. http:get:: /files/(uuid:bucket_id)/(string:filename)

            Sends file to the client.

            **Request**:

            .. sourcecode:: http

                GET /files/4b60f39d-b960-442f-be68-b4b8b04c38a9/f.pdf HTTP/1.1
                Accept: application/json
                Connection: keep-alive
                Content-Type: application/json
                Host: localhost:5000

            :reqheader Content-Type: application/json
            :query uuid version_id: uuid of a specific version of a file.

            **Response**:

            .. sourcecode:: http

                HTTP/1.0 200 OK
                Content-Type: application/pdf
                ETag: "flask-1449350517.0-15192-1285496294"

                Downloading to "f.pdf"

            :resheader Content-Type: application/json
            :statuscode 200: no error
            :statuscode 401: authentication required
            :statuscode 403: access denied
            :statuscode 404: Object does not exist
        """
        return self.send_object(bucket, obj, version_id=version_id)

    @use_kwargs(post_args)
    @pass_bucket
    @need_bucket_permission('bucket-create-object')
    @pass_file
    def post(self, key, uploaded_file=None, bucket=None, content_md5=None):
        """Upload a new object."""
        # TODO: Support checking incoming MD5 header
        # TODO: Support setting content-type
        # TODO: Don't create a new file if content is identical.

        # TODO: Pass storage class to get_or_create
        with db.session.begin_nested():
            obj = ObjectVersion.create(bucket.id, key)
            obj.set_contents(uploaded_file)
        db.session.commit()

        # TODO: Fix response object to only include headers?
        return obj

    @use_kwargs(put_args)
    @pass_bucket
    @pass_object
    @need_objects_permission('objects-update')
    @pass_file
    def put(self, uploaded_file=None, obj=None, bucket=None, content_md5=None):
        """Update an existing object.

        .. http:put:: /files/(uuid:bucket_id)
            Uploads a new object file.

            **Request**:

            .. sourcecode:: http

                PUT /files/14b0b1d3-71f3-4b6b-87a2-0796f1624bb6 HTTP/1.1
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
                    "uuid": "322ea4c6-6650-4143-a328-274eee55f45d",
                    "updated": "2015-12-10T14:16:57.202795"
                }

            :resheader Content-Type: application/json
            :statuscode 200: no error
            :statuscode 400: invalid request
            :statuscode 403: access denied
            :statuscode 500: failed request
        """
        # TODO: Support checking incoming MD5 header
        # TODO: Support setting content-type
        # TODO: Don't create a new file if content is identical.

        # TODO: Pass storage class to get_or_create
        with db.session.begin_nested():
            obj = ObjectVersion.create(bucket.id, obj.key)
            obj.set_contents(uploaded_file)
        db.session.commit()

        # TODO: Fix response object to only include headers?
        return obj

    @pass_bucket
    @pass_object
    @need_objects_permission('objects-delete')
    def delete(self, obj=None, bucket=None, **kwargs):
        """Set object file as deleted.

        .. http:head:: /files/(uuid:bucket_id)/(string:filename)

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

                HTTP/1.0 404 NOT FOUND
                Content-Length: 0
                Content-Type: text/html

            :resheader Content-Type: application/json
            :statuscode 200: no error
            :statuscode 403: access denied
            :statuscode 404: page not found
            :statuscode 500: exception while deleting
        """
        with db.session.begin_nested():
            if not ObjectVersion.delete(bucket.id, obj.key):
                abort(
                    404,
                    'The specified object does not exist or has already been '
                    'deleted.'
                )
        db.session.commit()

    @pass_bucket
    @pass_object
    @need_objects_permission('objects-read')
    def head(self, obj=None, bucket=None, **kwargs):
        """Check the existence of the object file.

        .. http:head:: /files/(uuid:bucket_id)/(string:key)

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
        if not ObjectVersion.exists(bucket.id, obj.key):
            abort(404, 'Object does not exist.')


serializers = {'application/json': json_serializer}

bucket_collection_view = BucketCollectionResource.as_view(
    'bucket_collection_api',
    serializers={
        'application/json': bucket_collection_serializer,
    }
)
bucket_view = BucketResource.as_view(
    'bucket_api',
    serializers={
        'application/json': bucket_serializer,
    }
)
object_view = ObjectResource.as_view(
    'object_api',
    serializers={
        'application/json': object_serializer,
    }
)

blueprint.add_url_rule(
    '',
    view_func=bucket_collection_view,
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
