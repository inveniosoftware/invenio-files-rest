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

from invenio_files_rest.models import Bucket, FileInstance, ObjectVersion
from invenio_files_rest.tasks import verify_checksum


def test_verify_checksum(app, db, dummy_location):
    """Test celery tasks for checksum verification."""
    b = Bucket.create()
    with open('README.rst', 'rb') as fp:
        obj = ObjectVersion.create(b, 'README.rst', stream=fp)
    db.session.commit()

    verify_checksum(str(obj.file_id))

    f = FileInstance.query.get(obj.file_id)
    assert f.last_check_at
    assert f.last_check is True
