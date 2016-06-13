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

import uuid
from struct import pack

import pytest
from flask import json, url_for
from invenio_db import db
from six import BytesIO, b
from testutils import login_user

from invenio_files_rest import InvenioFilesREST
from invenio_files_rest.models import Bucket, Location, ObjectVersion
from invenio_files_rest.views import blueprint


def test_get_buckets_when_none_exist(app, db, client, headers):
    """Test get buckets without any created."""
    resp = client.get(
        url_for('invenio_files_rest.bucket_collection_api'),
        headers=headers,
    )
    assert resp.status_code == 200
    resp_json = json.loads(resp.data)
    assert json.loads(resp.data) == []


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket-collection', 200),
])
def test_get_buckets(app, client, headers, bucket, permissions,
                     user, expected):
    """Test get buckets."""
    expected_body = [{
        'uuid': str(bucket.id),
        'url': url_for(
            'invenio_files_rest.bucket_api',
            bucket_id=bucket.id,
            _external=True),
        'size': bucket.size,
    }]

    login_user(client, permissions[user])

    resp = client.get(
        url_for('invenio_files_rest.bucket_collection_api'),
        headers=headers,
    )

    assert resp.status_code == expected
    if resp.status_code == 200:
        assert json.loads(resp.data) == expected_body


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket-collection', 200),
])
def test_post_bucket(app, client, headers, dummy_location, permissions,
                     user, expected):
    """Test post a bucket."""
    expected_keys = ['uuid', 'url', 'size']
    params = [{}, {'location_name': dummy_location.name}]

    login_user(client, permissions[user])

    for data in params:
        resp = client.post(
            url_for('invenio_files_rest.bucket_collection_api'),
            data=data,
            headers=headers
        )
        assert resp.status_code == expected
        if resp.status_code == 200:
            resp_json = json.loads(resp.data)
            for key in expected_keys:
                assert key in resp_json
            assert Bucket.get(resp_json['uuid'])


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 200),
])
def test_head_bucket(app, client, headers, bucket, permissions,
                     user, expected):
    """Test checking existence of bucket."""
    login_user(client, permissions[user])

    resp = client.head(
        url_for('invenio_files_rest.bucket_api', bucket_id=bucket.id),
        headers=headers,
    )

    assert resp.status_code == expected
    assert not resp.data


@pytest.mark.parametrize('user, expected', [
    (None, 404),
    ('auth', 404),
    ('bucket', 404),
])
def test_head_non_existing_bucket(app, db, client, headers, permissions,
                                  user, expected):
    """Test checking for a non-existent bucket."""
    login_user(client, permissions[user])

    resp = client.head(
        url_for('invenio_files_rest.bucket_api', bucket_id=uuid.uuid4()),
        headers=headers,
    )
    assert resp.status_code == expected
    assert not resp.data


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 200),
])
def test_delete_bucket(app, client, headers, bucket, objects, permissions,
                       user, expected):
    """Test deleting a bucket."""
    login_user(client, permissions[user])
    resp = client.delete(
        url_for('invenio_files_rest.bucket_api', bucket_id=bucket.id),
        headers=headers,
    )
    assert resp.status_code == expected
    if resp.status_code == 200:
        assert not Bucket.exists(bucket.id)
    else:
        assert Bucket.exists(bucket.id)


@pytest.mark.parametrize('user, expected', [
    (None, 404),
    ('auth', 404),
    ('bucket', 404),
])
def test_delete_non_existent_bucket(app, db, client, headers, permissions,
                                    user, expected):
    """Test deleting a non-existent bucket."""
    login_user(client, permissions[user])
    resp = client.delete(
        url_for('invenio_files_rest.bucket_api', bucket_id=uuid.uuid4()),
        headers=headers
    )
    assert resp.status_code == expected


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 404),
    ('objects', 403),
])
def test_get_object_non_existing(app, client, headers, bucket, permissions,
                                 user, expected):
    """Test getting a non-existing object."""
    login_user(client, permissions[user])

    resp = client.get(
        url_for(
            'invenio_files_rest.object_api',
            bucket_id=bucket.id,
            key='non-existing.pdf',
        ),
        headers=headers,
    )
    assert resp.status_code == expected


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 200),
    ('objects', 200),
])
def test_get_object(app, client, headers, bucket, objects, permissions,
                    user, expected):
    """Test getting an object."""
    login_user(client, permissions[user])

    for obj in objects:
        resp = client.get(
            url_for(
                'invenio_files_rest.object_api',
                bucket_id=bucket.id,
                key=obj.key,
            ),
            headers=headers,
        )
        assert resp.status_code == expected
        if resp.status_code == 200:
            assert resp.content_md5 == obj.file.checksum
            assert resp.get_etag()[0] == obj.file.checksum


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 200),
])
def test_post_object(app, client, permissions, bucket, user, expected):
    """Test ObjectResource view POST method."""
    key = 'file.pdf'

    login_user(client, permissions[user])

    resp = client.post(
        url_for('invenio_files_rest.object_api', bucket_id=bucket.id, key=key),
        data={'file': (BytesIO(b'content_data'), key)},
        headers={'Accept': '*/*'},
    )
    assert resp.status_code == expected


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 400),
])
def test_post_object_missing_file(app, client, permissions, bucket,
                                  user, expected):
    """Test post object with file not included in the request."""
    key = 'file.pdf'

    login_user(client, permissions[user])

    resp = client.post(
        url_for('invenio_files_rest.object_api', bucket_id=bucket.id, key=key),
        data={},
        headers={'Accept': '*/*'},
    )
    assert resp.status_code == expected
    if resp.status_code == 400:
        assert 'File is missing from the request.' in resp.get_data(
            as_text=True)


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 200),
    ('objects', 200),
])
def test_put_object(app, client, bucket, objects, permissions,
                    user, expected):
    """Test updating an object."""
    login_user(client, permissions[user])

    for obj in objects:
        resp = client.put(
            url_for(
                'invenio_files_rest.object_api',
                bucket_id=bucket.id,
                key=obj.key,
            ),
            data={'file': (BytesIO(b'updated_content'), obj.key)}
        )
        assert resp.status_code == expected


@pytest.mark.parametrize('quota_size, max_file_size, expected', [
    (None, None, (200, '')),
    (50, None, (400, 'Bucket quota exceeded.')),
    (100, None, (200, '')),
    (150, None, (200, '')),
    (None, 50, (400, 'Maximum file size exceeded.')),
    (None, 100, (200, '')),
    (None, 150, (200, '')),
])
def test_file_size_errors(app, client, bucket, permissions,
                          quota_size, max_file_size, expected):
    """Test that file size errors are properly raised."""
    # Empty the bucket fixture
    ObjectVersion.query.delete()
    bucket.size = 0
    # Set new quota
    bucket.quota_size = quota_size
    bucket.max_file_size = max_file_size
    db.session.commit()

    key = 'file.dat'
    file_size = 100
    content = pack(
        ''.join('c' for i in range(file_size)),
        *[b'v' for i in range(file_size)]
    )

    login_user(client, permissions['bucket'])
    resp = client.post(
        url_for('invenio_files_rest.object_api', bucket_id=bucket.id, key=key),
        data={
            'file': (BytesIO(content), key),
        },
        headers={'Accept': '*/*'},
    )
    assert resp.status_code == expected[0]
    assert expected[1] in resp.get_data(as_text=True)


@pytest.mark.parametrize('user, expected', [
    (None, 404),
    ('auth', 404),
    ('bucket', 404),
])
def test_get_objects_non_existent_bucket(app, db, client, headers, permissions,
                                         user, expected):
    """Test getting objects from a non-existing bucket."""
    login_user(client, permissions[user])

    resp = client.get(
        url_for(
            'invenio_files_rest.bucket_api', bucket_id=uuid.uuid4()
        ),
        headers=headers
    )
    assert resp.status_code == expected


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 200),
])
def test_get_objects_from_empty_bucket(app, client, headers, bucket, objects,
                                       permissions, user, expected):
    """Test getting objects from an empty bucket"""
    # Delete the objects created in the fixtures to have an empty bucket with
    # permissions set up.
    for obj in objects:
        ObjectVersion.delete(obj.bucket_id, obj.key)
    db.session.commit()

    login_user(client, permissions[user])

    resp = client.get(
        url_for(
            'invenio_files_rest.bucket_api', bucket_id=bucket.id
        ),
        headers=headers
    )

    assert resp.status_code == expected
    if resp.status_code == 200:
        assert json.loads(resp.data) == []


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 200),
])
def test_get_objects_in_bucket(app, client, headers, bucket, objects,
                               permissions, user, expected):
    """Test getting objects from bucket."""
    expected_body = [
        {
            'uuid': str(obj.file.id),
            'checksum': obj.file.checksum,
            'url': url_for('invenio_files_rest.object_api',
                           bucket_id=bucket.id,
                           key=obj.key,
                           _external=True),
            'size': obj.file.size,
        } for obj in objects
    ]

    login_user(client, permissions[user])

    resp = client.get(
        url_for('invenio_files_rest.bucket_api', bucket_id=bucket.id),
        headers=headers,
    )
    assert resp.status_code == expected
    if resp.status_code == 200:
        resp_json = json.loads(resp.data)
        assert len(resp_json) == len(expected_body)
        for obj in expected_body:
            assert obj in resp_json


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 200),
])
def test_get_objects_with_versions(app, client, headers, bucket, versions,
                                   permissions, user, expected):
    """Test getting objects with all their versions."""
    login_user(client, permissions[user])

    expected_body = [
        {
            'uuid': str(obj.file.id),
            'checksum': obj.file.checksum,
            'url': url_for('invenio_files_rest.object_api',
                           bucket_id=bucket.id,
                           key=obj.key,
                           _external=True),
            'size': obj.file.size,
        } for obj in versions
    ]

    resp = client.get(
        url_for('invenio_files_rest.bucket_api', bucket_id=bucket.id),
        query_string=dict(versions=True),
        headers=headers,
    )
    assert resp.status_code == expected
    if resp.status_code == 200:
        resp_json = json.loads(resp.data)
        assert len(resp_json) == len(expected_body)
        for obj in expected_body:
            assert obj in resp_json


@pytest.mark.parametrize('user, expected', [
    (None, 404),
    ('auth', 404),
    ('objects', 404),
])
def test_get_object_from_non_existent_bucket(app, db, client, permissions,
                                             user, expected):
    """Test getting an object from a non-existent bucket."""
    login_user(client, permissions[user])

    resp = client.get(url_for(
        'invenio_files_rest.object_api',
        bucket_id=uuid.uuid4(),
        key='non-existent.pdf',
    ))
    assert resp.status_code == expected


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('bucket', 200),
])
def test_delete_object(app, client, bucket, objects, permissions,
                       user, expected):
    """Test deleting an object."""
    login_user(client, permissions[user])

    for obj in objects:
        resp = client.delete(url_for(
            'invenio_files_rest.object_api',
            bucket_id=bucket.id,
            key=obj.key,
        ))
        assert resp.status_code == expected
        if resp.status_code == 200:
            assert not ObjectVersion.exists(bucket.id, obj.key)
        else:
            assert ObjectVersion.exists(bucket.id, obj.key)


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 404),
])
def test_delete_non_existent_object(app, client, bucket, permissions,
                                    user, expected):
    """Test deleting a non existent object."""
    login_user(client, permissions[user])

    resp = client.delete(url_for(
        'invenio_files_rest.object_api',
        bucket_id=bucket.id,
        key='non-existent.pdf',
    ))
    assert resp.status_code == expected


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 200),
    ('objects', 200),
])
def test_head_object(app, client, bucket, objects, permissions,
                     user, expected):
    """Test checking for existence of an object."""
    login_user(client, permissions[user])

    for obj in objects:
        resp = client.head(url_for(
            'invenio_files_rest.object_api',
            bucket_id=bucket.id,
            key=obj.key,
        ))
        assert resp.status_code == expected


@pytest.mark.parametrize('user, expected', [
    (None, 401),
    ('auth', 403),
    ('bucket', 404),
])
def test_head_object_non_existing(app, client, bucket, permissions,
                                  user, expected):
    """Test checking for existence of a non-existing object."""
    login_user(client, permissions[user])

    resp = client.head(url_for(
        'invenio_files_rest.object_api',
        bucket_id=bucket.id,
        key='non-existing.pdf',
    ))
    assert resp.status_code == expected

# def test_get_objects_old(app, db, dummy_location):
#     """Test get all objects in a bucket."""
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
