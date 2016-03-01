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

"""Celery tasks for Invenio-Files-REST."""

from __future__ import absolute_import, print_function

import uuid

from celery import current_task, shared_task
from celery.states import state
from celery.utils.log import get_task_logger
from invenio_db import db

from .models import FileInstance, Location, ObjectVersion

logger = get_task_logger(__name__)


def progress_updater(size, total):
    """Progress reporter for checksum verification."""
    current_task.update_state(
        state=state('PROGRESS'),
        meta=dict(size=size, total=total)
    )


@shared_task(ignore_result=True)
def verify_checksum(file_id):
    """Verify checksum of a file instance."""
    f = FileInstance.query.get(uuid.UUID(file_id))
    f.verify_checksum(progress_callback=progress_updater)
    db.session.commit()


@shared_task(ignore_result=True, max_retries=3, default_retry_delay=20 * 60)
def migrate_file(src_id, location_name, post_fixity_check=False):
    """Task to migrate a file instance to a new location."""
    location = Location.get_by_name(location_name)
    f_src = FileInstance.get(src_id)

    # Create destination
    f_dst = FileInstance.create()
    db.session.commit()

    try:
        # Copy contents
        f_dst.copy_contents(
            f_src,
            progress_callback=progress_updater,
            location=location,
        )
        db.session.commit()
    except Exception:
        # Remove destination file instance if an error occurred.
        db.session.delete(f_dst)
        db.session.commit()
        raise

    # Update all objects pointing to file.
    ObjectVersion.relink_all(f_src, f_dst)
    db.session.commit()

    # Start a fixity check
    if post_fixity_check:
        verify_checksum.delay(str(f_dst.id))
