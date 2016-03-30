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


"""Module test views."""

from __future__ import absolute_import, print_function

import pytest
from flask import json, url_for
from invenio_db import db
from six import BytesIO, b
from test_helpers import CONSTANT_FILE_SIZE_LIMIT

from invenio_files_rest import InvenioFilesREST
from invenio_files_rest.views import blueprint


def test_get_buckets(app, dummy_location):
    """Test get buckets."""
    with app.test_client() as client:
        resp = client.get(
            '/files',
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200

        # With location_name
        resp = client.post(
            '/files',
            data=json.dumps({'location_name': dummy_location.name}),
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200


def test_post_bucket(app, dummy_location):
    """Test post a bucket."""
    with app.test_client() as client:
        resp = client.post(
            '/files',
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'url' in data


# def test_head_bucket(app, db):
#     """Test that checks if a bucket exists."""
#     with app.test_client() as client:
#         # Create bucket
#         resp = client.post(
#             '/files',
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 200
#         data = json.loads(resp.data)
#         assert 'url' in data
#         i = data['url'].index('/files')
#         bucket_url = data['url'][i:]
#         resp = client.head(
#             bucket_url,
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 200


# def test_delete_bucket(app, db, dummy_location):
#     """Test deleting a bucket."""
#     with app.test_client() as client:
#         # Create bucket
#         resp = client.post(
#             '/files',
#             data=json.dumps({'location_name': dummy_location.name}),
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 200
#         data = json.loads(resp.data)
#         assert 'url' in data
#         i = data['url'].index('/files')
#         bucket_url = data['url'][i:]

#         # Upload file to bucket
#         with open('LICENSE', 'rb') as f:
#             resp = client.put(
#                 bucket_url,
#                 data={'file': (f, 'LICENSE')},
#                 headers={'Accept': '*/*'}
#             )
#         assert resp.status_code == 200
#         data = json.loads(resp.data)
#         i = data['url'].index('/files')
#         object_url = data['url'][i:]

#         # Delete bucket
#         resp = client.delete(
#             bucket_url,
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 200

#         resp = client.head(
#             bucket_url,
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 404

#         resp = client.head(
#             object_url,
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 404

#         # Delete a non-existant bucket
#         resp = client.delete(
#             bucket_url,
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 404

# def test_get_object_list(app, dummy_objects):


def test_get_object_permissions(app, objects, bucket, users_data, permissions):
    """Test ObjectResource view GET method."""
    # Bucket and object
    obj = objects[0]
    key = obj.key

    # Users
    u1_data = users_data[0]  # Privileged user
    u2_data = users_data[1]  # Unprivileged user

    # URLs
    login_url = url_for('security.login')
    object_url = "/files/{0}/{1}".format(bucket.id, key)
    object_url_invalid = "/files/{0}/{1}".format(bucket.id, key + "XYZ")

    headers = {'Content-Type': 'application/json', 'Accept': '*/*'}

    with app.test_client() as client:
        # Get object that doesn't exist. Gets the "401 Unauthorized" before 404
        resp = client.get(object_url_invalid, headers=headers)
        assert resp.status_code == 401
        # Get 404 after login
        client.post(login_url, data=u1_data)
        resp = client.get(object_url_invalid, headers=headers)
        assert resp.status_code == 404

    with app.test_client() as client:
        # Request the object anonymously, get "401 Unauthorized"
        resp = client.get(object_url, headers=headers)
        assert resp.status_code == 401

        # Request the object with user2 (no permissions), get "403 Forbidden"
        client.post(login_url, data=u2_data)  # Login with user2
        resp = client.get(object_url, headers=headers)
        assert resp.status_code == 403

    with app.test_client() as client:
        # Login with privileged user and get object
        client.post(login_url, data=u1_data)
        resp = client.get(object_url, headers=headers)
        assert resp.status_code == 200

        # Check headers
        assert resp.content_md5 == obj.file.checksum
        assert resp.get_etag()[0] == obj.file.checksum


@pytest.mark.parametrize('limiter, bucket_quota, file_size_limit', [
    # use the default file size limiter
    (None, 50, 50),
    # internal quota is not used by the constant_file_size_limiter
    ('test_helpers:constant_file_size_limiter', CONSTANT_FILE_SIZE_LIMIT + 2,
     CONSTANT_FILE_SIZE_LIMIT),
])
def test_put_object(limiter, bucket_quota, file_size_limit, base_app, objects,
                    bucket, users_data, permissions):
    """Test ObjectResource view PUT method."""
    if limiter is not None:
        base_app.config['FILES_REST_FILE_SIZE_LIMITER'] = limiter
    InvenioFilesREST(base_app)
    base_app.register_blueprint(blueprint)

    key = objects[0].key
    u1_data = users_data[0]  # Privileged user
    u2_data = users_data[1]  # Unprivileged user
    login_url = url_for('security.login')
    object_url = "/files/{0}/{1}".format(bucket.id, key)

    with base_app.app_context():
        bucket.quota_size = bucket_quota
        db.session.merge(bucket)
        db.session.commit()

    with base_app.test_client() as client:
        # Get object that doesn't exist. Gets the "401 Unauthorized" before 404
        # Try to update the file under 'key' (with 'contents2')
        data_bytes = b'contents2'
        headers = {'Accept': '*/*', 'Content-Length': str(len(data_bytes))}
        data = {'file': (BytesIO(data_bytes), 'file.dat')}
        resp = client.put(object_url, data=data, headers=headers)
        assert resp.status_code == 401

        # Login with 'user2' (no permissions), try to PUT, receive 403
        client.post(login_url, data=u2_data)
        data = {'file': (BytesIO(data_bytes), 'file.dat')}
        resp = client.put(object_url, data=data, headers=headers)
        assert resp.status_code == 403

        # FIXME: check that the file is not created

    with base_app.test_client() as client:
        # Login with 'user1' (has permissions)
        client.post(login_url, data=u1_data)
        # Test with an mismatching Content-Length
        headers = {'Accept': '*/*', 'Content-Length': str(len(data_bytes) - 1)}
        data = {'file': (BytesIO(data_bytes), 'mismatching1.dat')}
        resp = client.put(object_url, data=data, headers=headers)
        assert resp.status_code == 400

        headers = {'Accept': '*/*', 'Content-Length': str(len(data_bytes) + 1)}
        data = {'file': (BytesIO(data_bytes), 'mismatching2.dat')}
        resp = client.put(object_url, data=data, headers=headers)
        assert resp.status_code == 400

        # FIXME: check that the file is not created

        # Test exceeding the file size limit
        data_bytes2 = b(''.join('a' for i in
                                range(file_size_limit + 1)))
        headers = {'Accept': '*/*', 'Content-Length': str(len(data_bytes2))}
        data = {'file': (BytesIO(data_bytes2), 'exceeding.dat')}
        resp = client.put(object_url, data=data, headers=headers)
        assert resp.status_code == 400

        # FIXME: check that the file is not created

    # if the default limiter is used
    if limiter is None:
        # set the bucket quota to unlimited
        with base_app.app_context():
            bucket.quota_size = None
            db.session.merge(bucket)
            db.session.commit()
        # Test again with the precedly exceeding size
        with base_app.test_client() as client:
            # Login with 'user1' (has permissions)
            client.post(login_url, data=u1_data)
            data_bytes2 = b(''.join('a' for i in
                                    range(file_size_limit + 1)))
            headers = {'Accept': '*/*',
                       'Content-Length': str(len(data_bytes2))}
            data = {'file': (BytesIO(data_bytes2), 'exceeding.dat')}
            resp = client.put(object_url, data=data, headers=headers)
            assert resp.status_code == 200

# def test_get_object_get_access_denied_403(app, objects):
#     """Test object download 403 access denied"""
#     with app.test_client() as client:
#         for obj in objects:
#             resp = client.get(
#                 "/files/{}/{}".format(obj.bucket_id, obj.key),
#                 headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#             )
#             assert resp.status_code == 403

# def test_get_objects(app, db):
#     """Test get all objects in a bucket."""
#     with app.test_client() as client:
#         # Get a non-existant bucket
#         bucket_id = uuid.uuid4()
#         resp = client.get(
#             "files/{}".format(bucket_id),
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 404
#         # Create a bucket
#         resp = client.post(
#             '/files',
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 200
#         data = json.loads(resp.data)
#         assert 'url' in data
#         i = data['url'].index('/files')
#         bucket_url = data['url'][i:]
#         resp = client.get(
#             bucket_url,
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 200
#         data = json.loads(resp.data)
#         assert len(data) == 0
#         # Upload file to bucket
#         with open('LICENSE', 'rb') as f:
#             resp = client.put(
#                 bucket_url,
#                 data={'file': (f, 'LICENSE')},
#                 headers={'Accept': '*/*'}
#             )
#         assert resp.status_code == 200
#         data = json.loads(resp.data)
#         ini_version_id = data['version_id']
#         resp = client.get(
#             bucket_url,
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 200
#         data = json.loads(resp.data)
#         assert len(data) == 1
#         # Upload a new version of the file to bucket
#         with open('LICENSE', 'rb') as f:
#             resp = client.put(
#                 bucket_url,
#                 data={'file': (f, 'LICENSE')},
#                 headers={'Accept': '*/*'}
#             )
#         assert resp.status_code == 200
#         resp = client.get(
#             bucket_url,
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 200
#         data = json.loads(resp.data)
#         assert len(data) == 1
#         # Get all versions included
#         resp = client.get(
#             "{}?versions=1".format(bucket_url),
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 200
#         data = json.loads(resp.data)
#         assert len(data) == 2
#         # Get old version of the file
#         resp = client.get(
#             "{}/LICENSE?version_id={}".format(bucket_url, ini_version_id),
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 200


# def test_object_complete_cycle(app, db, dummy_location):
#     """Test the full life cylce of a file.

#     This test will cover:
#         - POST Creation of a temporary bucket
#         - POST Upload of a file
#         - GET the file
#         - POST Upload without the file (400)
#         - POST Upload to a non-existant bucket (404)
#         - HEAD file
#         - DELETE file
#     """
#     with app.test_client() as client:
#         # Create bucket
#         resp = client.post(
#             '/files',
#             data=json.dumps({'location_name': dummy_location.name}),
#             headers={'Content-Type': 'application/json',
#                      'Accept': '*/*'}
#         )
#         assert resp.status_code == 200
#         data = json.loads(resp.data)
#         assert 'url' in data
#         i = data['url'].index('/files')
#         bucket_url = data['url'][i:]

#         # Upload file to bucket
#         with open('LICENSE', 'rb') as f:
#             resp = client.put(
#                 bucket_url,
#                 data={'file': (f, 'LICENSE')},
#                 headers={'Accept': '*/*'}
#             )
#         assert resp.status_code == 200
#         data = json.loads(resp.data)
#         i = data['url'].index('/files')
#         object_url = data['url'][i:]

#         # Retrive uploaded file
#         res = client.get(object_url)
#         assert res.status_code == 200

#         # Try upload without file
#         resp = client.put(
#             bucket_url,
#             headers={'Accept': '*/*'}
#         )
#         assert resp.status_code == 400

#         # Try to upload to a non existant bucket
#         bucket_id = uuid.uuid4()
#         with open('LICENSE', 'rb') as f:
#             resp = client.put(
#                 '/files/{}'.format(bucket_id),
#                 data={'file': (f, 'LICENSE')},
#                 headers={'Accept': '*/*'}
#             )
#         assert resp.status_code == 404

#         # Verify the file was uploaded
#         resp = client.head(
#             object_url,
#             headers={'Accept': '*/*'}
#         )
#         assert resp.status_code == 200

#         # Delete file
#         resp = client.delete(
#             object_url,
#             headers={'Accept': '*/*'}
#         )
#         assert resp.status_code == 200

#         # Verify it was deleted
#         resp = client.head(
#             object_url,
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 404

#         # Get a non-existant file
#         resp = client.get(
#             object_url,
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 404

#         # Delete a non-existant file
#         resp = client.delete(
#             object_url,
#             headers={'Content-Type': 'application/json', 'Accept': '*/*'}
#         )
#         assert resp.status_code == 404
