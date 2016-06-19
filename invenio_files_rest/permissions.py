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

"""Permissions for files using Invenio-Access."""

from functools import partial

from invenio_access.permissions import DynamicPermission, \
    ParameterizedActionNeed

from .models import Bucket, Location, MultipartObject, ObjectVersion

#
# Action needs
#
# Create buckets
LocationUpdate = partial(
    ParameterizedActionNeed, 'files-rest-location-update')

# List objects in bucket
BucketRead = partial(
    ParameterizedActionNeed, 'files-rest-bucket-read')
# List object versions in bucket
BucketReadVersions = partial(
    ParameterizedActionNeed, 'files-rest-bucket-read-versions')
# Create objects and multipart uploads in bucket
BucketUpdate = partial(
    ParameterizedActionNeed, 'files-rest-bucket-update')
# List multipart uploads in bucket
BucketListMultiparts = partial(
    ParameterizedActionNeed, 'files-rest-bucket-listmultiparts')

# Get object in bucket
ObjectRead = partial(
    ParameterizedActionNeed, 'files-rest-object-read')
# Get object version in bucket
ObjectReadVersion = partial(
    ParameterizedActionNeed, 'files-rest-object-read-version')
# Delete object in bucket
ObjectDelete = partial(
    ParameterizedActionNeed, 'files-rest-object-delete')
# Permanently delete specific object version in bucket
ObjectDeleteVersion = partial(
    ParameterizedActionNeed, 'files-rest-object-delete-version')

# List parts of a multipart upload in a bucket
MultipartRead = partial(
    ParameterizedActionNeed, 'files-rest-multipart-read')
# Abort a multipart upload
MultipartDelete = partial(
    ParameterizedActionNeed, 'files-rest-multipart-delete')


#
# Global action needs
#
location_update_all = LocationUpdate(None)

bucket_read_all = BucketRead(None)
bucket_read_versions_all = BucketReadVersions(None)
bucket_update_all = BucketUpdate(None)
bucket_listmultiparts_all = BucketListMultiparts(None)

object_read_all = ObjectRead(None)
object_read_version_all = ObjectReadVersion(None)
object_delete_all = ObjectDelete(None)
object_delete_version_all = ObjectDeleteVersion(None)

multipart_read_all = MultipartRead(None)
multipart_delete_all = MultipartDelete(None)

#
# Mapping of action names to action needs.
#
_action2need_map = {
    'location-update': LocationUpdate,
    'bucket-read': BucketRead,
    'bucket-read-versions': BucketReadVersions,
    'bucket-update': BucketUpdate,
    'bucket-listmultiparts': BucketListMultiparts,
    'object-read': ObjectRead,
    'object-read-version': ObjectReadVersion,
    'object-delete': ObjectDelete,
    'object-delete-version': ObjectDeleteVersion,
    'multipart-read': MultipartRead,
    'multipart-delete': MultipartDelete,
}


def permission_factory(obj, action):
    """Permission factory."""
    need_class = _action2need_map[action]

    if obj is None:
        return DynamicPermission(need_class(None))

    arg = None
    if isinstance(obj, Bucket):
        arg = str(obj.id)
    elif isinstance(obj, ObjectVersion):
        arg = str(obj.bucket_id)
    elif isinstance(obj, MultipartObject):
        arg = str(obj.bucket_id)
    else:
        raise RuntimeError('Unknown object')

    return DynamicPermission(need_class(arg))
