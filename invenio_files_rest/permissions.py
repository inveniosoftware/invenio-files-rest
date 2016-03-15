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

"""Permissions for files."""

from functools import partial

from flask_principal import ActionNeed
from invenio_access.permissions import DynamicPermission, \
    ParameterizedActionNeed

BucketRead = partial(ParameterizedActionNeed, 'files-rest-bucket-read')
BucketUpdate = partial(ParameterizedActionNeed, 'files-rest-bucket-update')
BucketDelete = partial(ParameterizedActionNeed, 'files-rest-bucket-delete')

ObjectsRead = partial(ParameterizedActionNeed, 'files-rest-objects-read')
ObjectsUpdate = partial(ParameterizedActionNeed, 'files-rest-objects-update')
ObjectsDelete = partial(ParameterizedActionNeed, 'files-rest-objects-delete')

bucket_create = ActionNeed('files-rest-bucket-create')
bucket_read_all = BucketRead(None)
bucket_update_all = BucketUpdate(None)
bucket_delete_all = BucketDelete(None)

objects_create = ActionNeed('files-rest-objects-create')
objects_read_all = ObjectsRead(None)
objects_update_all = ObjectsUpdate(None)
objects_delete_all = ObjectsDelete(None)

_action2need_map = {
    'objects-read': ObjectsRead,
    'objects-update': ObjectsUpdate,
    'objects-delete': ObjectsRead,
}


def permission_factory(bucket, action='objects-read'):
    """Permission factory for the actions on Bucket and ObjectVersion items."""
    return DynamicPermission(_action2need_map[action](str(bucket.id)))
