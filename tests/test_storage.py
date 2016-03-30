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

"""Storage module tests."""

from __future__ import absolute_import, print_function

import errno
import hashlib
from os.path import getsize, join

import pytest
from mock import patch
from six import BytesIO, b

from invenio_files_rest.errors import StorageError, UnexpectedFileSizeError
from invenio_files_rest.models import Bucket, FileInstance, ObjectVersion
from invenio_files_rest.storage import PyFilesystemStorage, Storage


def test_pyfilesystemstorage(app, db, dummy_location):
    """Test pyfs storage."""
    # Create bucket and object
    with db.session.begin_nested():
        b1 = Bucket.create()
        obj = ObjectVersion.create(b1, "LICENSE")
        obj.file = FileInstance.create()

    storage = PyFilesystemStorage(obj.file, base_uri=obj.bucket.location.uri)
    counter = dict(size=0)

    def callback(total, size):
        counter['size'] = size

    def test_file_save(data, **kwargs):
        stream = BytesIO(data)
        loc, size, checksum = storage.save(stream, progress_callback=callback,
                                           **kwargs)

        # Verify checksum, size and location.
        m = hashlib.md5()
        m.update(data)
        assert "md5:{0}".format(m.hexdigest()) == checksum

        assert size == len(data)
        assert loc == join(
            dummy_location.uri,
            str(obj.file.id),
            "data")

    data = b("this is some content")
    # test without size
    test_file_save(data)
    # test with correct size
    test_file_save(data, size=len(data))
    # test with wrong sizes
    with pytest.raises(UnexpectedFileSizeError):
        test_file_save(data, size=len(data) - 1)
    with pytest.raises(UnexpectedFileSizeError):
        test_file_save(data, size=len(data) + 1)


def test_pyfilesystemstorage_checksum(app, db, dummy_location):
    """Test fixity."""
    # Compute checksum of license file/
    with open("LICENSE", "rb") as fp:
        m = hashlib.md5()
        m.update(fp.read())
        checksum = "md5:{0}".format(m.hexdigest())

    counter = dict(size=0)

    def callback(total, size):
        counter["size"] = size

    # Now do it with storage interfacee
    storage = PyFilesystemStorage(
        FileInstance(uri="LICENSE", size=getsize("LICENSE")))
    assert checksum == storage.compute_checksum(
        chunk_size=2, progress_callback=callback)
    assert counter["size"] == getsize("LICENSE")


def test_pyfilesystemstorage_checksum_fail(app, db, dummy_location):
    """Test fixity problems."""
    # Raise an error during checksum calculation
    def callback(total, size):
        raise OSError(errno.EPERM, "Permission")

    f = FileInstance.create()
    f.set_contents(BytesIO(b("test")), location=dummy_location)

    pytest.raises(
        StorageError, PyFilesystemStorage(f).compute_checksum,
        progress_callback=callback)


def test_pyfs_send_file(app, db, dummy_location):
    """Test send file."""
    with db.session.begin_nested():
        b = Bucket.create()
        obj = ObjectVersion.create(b, "LICENSE")
        with open("LICENSE", "rb") as fp:
            obj.set_contents(fp)

    with app.test_request_context():
        res = obj.file.send_file()
        assert res.status_code == 200
        h = res.headers
        assert h["Content-Length"] == str(obj.file.size)
        assert h["Content-MD5"] == obj.file.checksum
        assert h["ETag"] == '"{0}"'.format(obj.file.checksum)

        # Content-Type: application/octet-stream
        # ETag: "b234ee4d69f5fce4486a80fdaf4a4263"
        # Last-Modified: Sat, 23 Jan 2016 06:21:04 GMT
        # Cache-Control: max-age=43200, public
        # Expires: Sat, 23 Jan 2016 19:21:04 GMT
        # Date: Sat, 23 Jan 2016 07:21:04 GMT
        # print(res.headers)


def test_pyfs_send_file_fail(app, db, dummy_location):
    """Test send file."""
    f = FileInstance.create()
    f.set_contents(BytesIO(b("test")), location=dummy_location)

    with patch('invenio_files_rest.storage.send_stream') as send_stream:
        send_stream.side_effect = OSError(errno.EPERM, "Permission problem")
        with app.test_request_context():
            pytest.raises(StorageError, f.send_file)


def test_storage_interface():
    """Test storage interface."""
    f = FileInstance.create()
    s = Storage(f)

    pytest.raises(NotImplementedError, s.open)
    pytest.raises(NotImplementedError, s.send_file)
    pytest.raises(NotImplementedError, s.save, None)
    pytest.raises(NotImplementedError, s.compute_checksum, None)
