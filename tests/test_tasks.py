# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

import errno
from os.path import exists, join

import pytest
from fs.errors import FSError
from mock import MagicMock, patch

from invenio_files_rest.models import Bucket, FileInstance, ObjectVersion
from invenio_files_rest.tasks import migrate_file, verify_checksum


def test_verify_checksum(app, db, dummy_location):
    """Test celery tasks for checksum verification."""
    b1 = Bucket.create()
    with open('README.rst', 'rb') as fp:
        obj = ObjectVersion.create(b1, 'README.rst', stream=fp)
    db.session.commit()

    verify_checksum(str(obj.file_id))

    f = FileInstance.query.get(obj.file_id)
    assert f.last_check_at
    assert f.last_check is True


def test_migrate_file(app, db, dummy_location, extra_location, bucket,
                      objects):
    """Test file migration."""
    obj = objects[0]

    # Test pre-condition
    old_uri = obj.file.uri
    assert exists(old_uri)
    assert old_uri == join(dummy_location.uri, str(obj.file.id)[0:2],
                           str(obj.file.id)[2:], 'data')
    assert FileInstance.query.count() == 4

    # Migrate file
    with patch('invenio_files_rest.tasks.verify_checksum') as verify_checksum:
        migrate_file(
            obj.file_id, location_name=extra_location.name,
            post_fixity_check=True)
        assert verify_checksum.delay.called

    # Get object again
    obj = ObjectVersion.get(bucket, obj.key)
    new_uri = obj.file.uri
    assert exists(old_uri)
    assert exists(new_uri)
    assert new_uri != old_uri
    assert FileInstance.query.count() == 5


def test_migrate_file_copyfail(app, db, dummy_location, extra_location,
                               bucket, objects):
    """Test a failed copy."""
    obj = objects[0]

    assert FileInstance.query.count() == 4
    with patch('fs.osfs.io') as io:
        e = OSError()
        e.errno = errno.EPERM
        io.open = MagicMock(side_effect=e)
        pytest.raises(
            FSError,
            migrate_file,
            obj.file_id,
            location_name=extra_location.name
        )
    assert FileInstance.query.count() == 4
