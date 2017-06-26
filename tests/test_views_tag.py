# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
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

"""Test object related views."""

from __future__ import absolute_import, print_function

from io import BytesIO

from flask import url_for

from invenio_files_rest.models import ObjectVersion


def test_tags_api(client, bucket):
    """Test upload of an object with tags in the headers."""

    key = 'test.txt'
    obj = ObjectVersion.create(bucket, key, stream=BytesIO(b'hello'))

    tag_url = url_for(
        'invenio_files_rest.tag_api', bucket_id=bucket.id, key=key)
    resp = client.put(
        tag_url,
        data='{"tag1": "value1", "tag2": "value2", "tag3": "value3"}',
        content_type='application/json',
    )
    assert resp.status_code == 200

    tags = obj.get_tags()

    assert tags['tag1'] == 'value1'
    assert tags['tag2'] == 'value2'
    assert tags['tag3'] == 'value3'

    resp = client.put(
        tag_url,
        data='{"tag1": "updated", "tag2": "updated2"}',
        content_type='application/json',
    )

    assert resp.status_code == 200

    tags = obj.get_tags()

    assert tags['tag1'] == 'updated'
    assert tags['tag2'] == 'updated2'
    assert tags['tag3'] == 'value3'

    resp = client.delete(
        tag_url,
        data='["tag2", "tag3"]',
        content_type='application/json',
    )

    assert resp.status_code == 200

    tags = obj.get_tags()

    assert tags['tag1'] == 'updated'
    assert 'tag2' not in tags
    assert 'tag3' not in tags
