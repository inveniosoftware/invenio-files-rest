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


BucketCollectionRead = partial(
    ParameterizedActionNeed, 'files-rest-bucket-collection-read')
BucketCollectionCreate = partial(
    ParameterizedActionNeed, 'files-rest-bucket-collection-create')

BucketRead = partial(ParameterizedActionNeed, 'files-rest-bucket-read')
BucketCreate = partial(ParameterizedActionNeed, 'files-rest-bucket-create')
BucketUpdate = partial(ParameterizedActionNeed, 'files-rest-bucket-update')
BucketDelete = partial(ParameterizedActionNeed, 'files-rest-bucket-delete')

ObjectsRead = partial(ParameterizedActionNeed, 'files-rest-objects-read')
ObjectsUpdate = partial(ParameterizedActionNeed, 'files-rest-objects-update')
ObjectsDelete = partial(ParameterizedActionNeed, 'files-rest-objects-delete')

bucket_collection_read_all = BucketCollectionRead(None)
bucket_collection_create = BucketCollectionCreate(None)

bucket_read_all = BucketRead(None)
bucket_create = BucketCreate(None)
bucket_update_all = BucketUpdate(None)
bucket_delete_all = BucketDelete(None)

objects_read_all = ObjectsRead(None)
objects_update_all = ObjectsUpdate(None)
objects_delete_all = ObjectsDelete(None)

_action2need_map = {
    'bucket-collection-read': BucketCollectionRead,
    'bucket-collection-create': BucketCollectionCreate,  # Create bucket
    'bucket-read': BucketRead,
    'bucket-create': BucketCreate,  # Create object
    'bucket-update': BucketUpdate,
    'bucket-delete': BucketDelete,
    'objects-read': (BucketRead, ObjectsRead),
    'objects-update': (BucketUpdate, ObjectsUpdate),
    'objects-delete': (BucketDelete, ObjectsDelete),
}


def bucket_collection_permission_factory(action='bucket-collection-read'):
    """Permission factory for the actions on Bucket collections."""
    return DynamicPermission(_action2need_map[action](None))


def bucket_permission_factory(bucket, action='bucket-read'):
    """Permission factory actions on buckets."""
    return DynamicPermission(_action2need_map[action](str(bucket.id)))


def object_permission_factory(bucket, key, action='objects-read'):
    """Permission factory for the actions on Bucket and ObjectVersion items."""
    return DynamicPermission(
        _action2need_map[action][0](str(bucket.id)),
        _action2need_map[action][1]('{0}:{1}'.format(str(bucket.id), key))
    )
