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

"""Storage s3 module tests."""

import hashlib
import pytest

import boto
from moto import mock_s3
from invenio_files_rest.errors import StorageError

from invenio_files_rest.models import Bucket, FileInstance, Object, Location
from invenio_files_rest.contrib.s3 import AmazonS3


@mock_s3
def test_s3filesystemstorage(app, db, dummy_location):
    """test aws storage"""

    conn = boto.connect_s3()
    conn.create_bucket('bucket_test')
    with db.session.begin_nested():
        l = Location()

        # s3 bucket name
        l.uri = "bucket_test"
        l.name = "buckettest1"
        db.session.add(l)
        b = Bucket.create(location_name=l.name)
        obj = Object.create(b, "LICENSE")
        obj.file = FileInstance()
        db.session.add(obj.file)

    # Test missing config
    pytest.raises(StorageError, AmazonS3, obj, obj.file)
    app.config["FILES_REST_AWS_KEY"] = "test_key"
    pytest.raises(StorageError, AmazonS3, obj, obj.file)
    app.config["FILES_REST_AWS_SECRET"] = "test_secret"
    storage = AmazonS3(obj, obj.file)
    pytest.raises(Exception, storage.open)

    with open('LICENSE', 'rb') as fp:
        loc, size, checksum = storage.save(fp)

    obj.file.set_uri(loc, size, checksum, storage_class=AmazonS3)

    assert size == len(open('LICENSE', 'rb').read())
    assert size == storage.get_size()
    assert obj.file.uri == loc
    with open('LICENSE', 'rb') as fp:
        m = hashlib.md5()
        m.update(fp.read())
        assert m.hexdigest() == checksum

    with storage.open() as fp:
        m = hashlib.md5()
        fp_content = fp.read()
        m.update(fp_content)
        assert len(fp_content) == size
        assert m.hexdigest() == checksum

    with storage.open() as fp:
        fp.seek(20)
        fp_content = fp.read(3)
        assert fp_content == "GNU"
        fp.seek(10056)
        fp_content = fp.read(1)
        assert fp_content == "6"
        # to be sure index does work
        fp_content = fp.read(1)
        assert fp_content == "."

    res = storage.send_file("")
    assert res.status_code == 302
    assert res.data.find("".join((l.uri, ".s3.amazonaws.com"))) > -1
