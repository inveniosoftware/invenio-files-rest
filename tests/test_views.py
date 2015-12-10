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


"""Module test views."""

from __future__ import absolute_import, print_function

import uuid

from flask import json


def test_get_buckets(app, db, dummy_location):
    """Test get buckets."""
    with app.test_client() as client:
        resp = client.get(
            '/files',
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200

        # With location_id
        resp = client.post(
            '/files',
            data=json.dumps({'location_id': dummy_location.id}),
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200


def test_post_bucket(app, db):
    """Test post a bucket."""
    with app.test_client() as client:
        resp = client.post(
            '/files',
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'url' in data


def test_head_bucket(app, db):
    """Test that checks if a bucket exists."""
    with app.test_client() as client:
        # Create bucket
        resp = client.post(
            '/files',
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'url' in data
        i = data['url'].index('/files')
        bucket_url = data['url'][i:]
        resp = client.head(
            bucket_url,
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200


def test_delete_bucket(app, db, dummy_location):
    """Test deleting a bucket."""
    with app.test_client() as client:
        # Create bucket
        resp = client.post(
            '/files',
            data=json.dumps({'location_id': dummy_location.id}),
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'url' in data
        i = data['url'].index('/files')
        bucket_url = data['url'][i:]

        # Upload file to bucket
        with open('LICENSE', 'rb') as f:
            resp = client.put(
                bucket_url,
                data={'file': (f, 'LICENSE')},
                headers={'Accept': '*/*'}
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        i = data['url'].index('/files')
        object_url = data['url'][i:]

        # Delete bucket
        resp = client.delete(
            bucket_url,
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200

        resp = client.head(
            bucket_url,
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 404

        resp = client.head(
            object_url,
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 404

        # Delete a non-existant bucket
        resp = client.delete(
            bucket_url,
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 404


def test_get_objects(app, db):
    """Test get all objects in a bucket."""
    with app.test_client() as client:
        # Get a non-existant bucket
        bucket_id = uuid.uuid4()
        resp = client.get(
            "files/{}".format(bucket_id),
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 404
        # Create a bucket
        resp = client.post(
            '/files',
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'url' in data
        i = data['url'].index('/files')
        bucket_url = data['url'][i:]
        resp = client.get(
            bucket_url,
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 0
        # Upload file to bucket
        with open('LICENSE', 'rb') as f:
            resp = client.put(
                bucket_url,
                data={'file': (f, 'LICENSE')},
                headers={'Accept': '*/*'}
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        ini_version_id = data['version_id']
        resp = client.get(
            bucket_url,
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1
        # Upload a new version of the file to bucket
        with open('LICENSE', 'rb') as f:
            resp = client.put(
                bucket_url,
                data={'file': (f, 'LICENSE')},
                headers={'Accept': '*/*'}
            )
        assert resp.status_code == 200
        resp = client.get(
            bucket_url,
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1
        # Get all versions included
        resp = client.get(
            "{}?versions=1".format(bucket_url),
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 2
        # Get old version of the file
        resp = client.get(
            "{}/LICENSE?version_id={}".format(bucket_url, ini_version_id),
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 200


def test_object_complete_cycle(app, db, dummy_location):
    """Test the full life cylce of a file.

    This test will cover:
        - POST Creation of a temporary bucket
        - POST Upload of a file
        - GET the file
        - POST Upload without the file (400)
        - POST Upload to a non-existant bucket (404)
        - HEAD file
        - DELETE file
    """
    with app.test_client() as client:
        # Create bucket
        resp = client.post(
            '/files',
            data=json.dumps({'location_id': dummy_location.id}),
            headers={'Content-Type': 'application/json',
                     'Accept': '*/*'}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'url' in data
        i = data['url'].index('/files')
        bucket_url = data['url'][i:]

        # Upload file to bucket
        with open('LICENSE', 'rb') as f:
            resp = client.put(
                bucket_url,
                data={'file': (f, 'LICENSE')},
                headers={'Accept': '*/*'}
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        i = data['url'].index('/files')
        object_url = data['url'][i:]

        # Retrive uploaded file
        res = client.get(object_url)
        assert res.status_code == 200

        # Try upload without file
        resp = client.put(
            bucket_url,
            headers={'Accept': '*/*'}
        )
        assert resp.status_code == 400

        # Try to upload to a non existant bucket
        bucket_id = uuid.uuid4()
        with open('LICENSE', 'rb') as f:
            resp = client.put(
                '/files/{}'.format(bucket_id),
                data={'file': (f, 'LICENSE')},
                headers={'Accept': '*/*'}
            )
        assert resp.status_code == 404

        # Verify the file was uploaded
        resp = client.head(
            object_url,
            headers={'Accept': '*/*'}
        )
        assert resp.status_code == 200

        # Delete file
        resp = client.delete(
            object_url,
            headers={'Accept': '*/*'}
        )
        assert resp.status_code == 200

        # Verify it was deleted
        resp = client.head(
            object_url,
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 404

        # Get a non-existant file
        resp = client.get(
            object_url,
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 404

        # Delete a non-existant file
        resp = client.delete(
            object_url,
            headers={'Content-Type': 'application/json', 'Accept': '*/*'}
        )
        assert resp.status_code == 404
