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

"""Celery tasks for Invenio-Files-REST."""

from __future__ import absolute_import, print_function

import uuid
from datetime import datetime

from celery import current_task, shared_task
from celery.states import state
from celery.utils.log import get_task_logger
from flask import current_app
from invenio_db import db
from sqlalchemy.exc import IntegrityError

from .models import FileInstance, Location, MultipartObject, ObjectVersion

logger = get_task_logger(__name__)


def progress_updater(size, total):
    """Progress reporter for checksum verification."""
    current_task.update_state(
        state=state('PROGRESS'),
        meta=dict(size=size, total=total)
    )


@shared_task(ignore_result=True)
def verify_checksum(file_id):
    """Verify checksum of a file instance.

    :param file_id: The file ID.
    """
    f = FileInstance.query.get(uuid.UUID(file_id))
    f.verify_checksum(progress_callback=progress_updater)
    db.session.commit()


@shared_task(ignore_result=True, max_retries=3, default_retry_delay=20 * 60)
def migrate_file(src_id, location_name, post_fixity_check=False):
    """Task to migrate a file instance to a new location.

    .. note:: If something goes wrong during the content copy, the destination
        file instance is removed.

    :param src_id: The :class:`invenio_files_rest.models.FileInstance` ID.
    :param location_name: Where to migrate the file.
    :param post_fixity_check: Verify checksum after migration.
        (Default: ``False``)
    """
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
            default_location=location.uri,
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


@shared_task(ignore_result=True)
def remove_file_data(file_id, silent=True):
    """Remove file instance and associated data.

    :param file_id: The :class:`invenio_files_rest.models.FileInstance` ID.
    :param silent: It stops propagation of a possible arised IntegrityError
        exception. (Default: ``True``)
    :raises sqlalchemy.exc.IntegrityError: Raised if the database removal goes
        wrong and silent is set to ``False``.
    """
    try:
        # First remove FileInstance from database and commit transaction to
        # ensure integrity constraints are checked and enforced.
        f = FileInstance.get(file_id)
        if not f.writable:
            return
        f.delete()
        db.session.commit()
        # Next, remove the file on disk. This leaves the possibility of having
        # a file on disk dangling in case the database removal works, and the
        # disk file removal doesn't work.
        f.storage().delete()
    except IntegrityError:
        if not silent:
            raise


@shared_task()
def merge_multipartobject(upload_id, version_id=None):
    """Merge multipart object.

    :param upload_id: The :class:`invenio_files_rest.models.MultipartObject`
        upload ID.
    :param version_id: Optionally you can define which file version.
        (Default: ``None``)
    :returns: The :class:`invenio_files_rest.models.ObjectVersion` version
        ID.
    """
    mp = MultipartObject.query.filter_by(upload_id=upload_id).one_or_none()
    if not mp:
        raise RuntimeError('Upload ID does not exists.')
    if not mp.completed:
        raise RuntimeError('MultipartObject is not completed.')

    try:
        obj = mp.merge_parts(
            version_id=version_id,
            progress_callback=progress_updater
        )
        db.session.commit()
        return str(obj.version_id)
    except Exception:
        db.session.rollback()
        raise


@shared_task(ignore_result=True)
def remove_expired_multipartobjects():
    """Remove expired multipart objects."""
    delta = current_app.config['FILES_REST_MULTIPART_EXPIRES']
    expired_dt = datetime.utcnow() - delta

    file_ids = []
    for mp in MultipartObject.query_expired(expired_dt):
        file_ids.append(str(mp.file_id))
        mp.delete()

    for fid in file_ids:
        remove_file_data.delay(fid)
