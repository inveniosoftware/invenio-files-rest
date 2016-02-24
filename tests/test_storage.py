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

import hashlib
from os.path import getsize, join

from invenio_files_rest.models import Bucket, FileInstance, ObjectVersion
from invenio_files_rest.storage import PyFilesystemStorage


def test_pyfilesystemstorage(app, db, dummy_location):
    """Test pyfs storage."""
    # Create bucket and object
    with db.session.begin_nested():
        b = Bucket.create()
        obj = ObjectVersion.create(b, "LICENSE")
        obj.file = FileInstance()
        db.session.add(obj.file)

    storage = PyFilesystemStorage(obj, obj.file)
    with open('LICENSE', 'rb') as fp:
        loc, size, checksum = storage.save(fp)

    # Verify checksum, size and location.
    with open('LICENSE', 'rb') as fp:
        m = hashlib.md5()
        m.update(fp.read())
        assert m.hexdigest() == checksum

    assert size == getsize('LICENSE')
    assert size == getsize('LICENSE')
    assert loc == \
        join(
            dummy_location.uri,
            str(b.id),
            str(obj.version_id),
            "data")


def test_pyfs_send_file(app, db, dummy_location):
    """Test send file."""
    with db.session.begin_nested():
        b = Bucket.create()
        obj = ObjectVersion.create(b, "LICENSE")
        with open('LICENSE', 'rb') as fp:
            obj.set_contents(fp)

    with app.test_request_context():
        res = obj.send_file()
        assert res.status_code == 200
        h = res.headers
        assert h['Content-Length'] == str(obj.file.size)
        assert h['Content-MD5'] == obj.file.checksum
        assert h['ETag'] == '"{0}"'.format(obj.file.checksum)

        # Content-Type: application/octet-stream
        # ETag: "b234ee4d69f5fce4486a80fdaf4a4263"
        # Last-Modified: Sat, 23 Jan 2016 06:21:04 GMT
        # Cache-Control: max-age=43200, public
        # Expires: Sat, 23 Jan 2016 19:21:04 GMT
        # Date: Sat, 23 Jan 2016 07:21:04 GMT
        # print(res.headers)
