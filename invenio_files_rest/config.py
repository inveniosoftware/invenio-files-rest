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

"""Invenio Files Rest module configuration file."""

FILES_REST_STORAGE_CLASS_LIST = {
    'S': 'Standard',
    'A': 'Archive',
}
"""Storage class list defines the systems storage classes.

Storage classes are useful for e.g. defining the type of storage an object
is located on (e.g. offline/online), so that the system knowns if it can serve
the file and/or what is the reliability.
"""

FILES_REST_DEFAULT_STORAGE_CLASS = 'S'
"""Default storage class."""

FILES_REST_DEFAULT_QUOTA_SIZE = None
"""Default quota size for a bucket in bytes."""

FILES_REST_DEFAULT_MAX_FILE_SIZE = None
"""Default maximum file size for a bucket in bytes."""

FILES_REST_SIZE_LIMITERS = 'invenio_files_rest.limiters.file_size_limiters'
"""Import path of file size limiters factory."""

FILES_REST_STORAGE_FACTORY = 'invenio_files_rest.storage.pyfs_storage_factory'
"""Import path of factory used to create a storage instance."""

FILES_REST_BUCKET_COLLECTION_PERMISSION_FACTORY = \
    'invenio_files_rest.permissions.bucket_collection_permission_factory'

FILES_REST_BUCKET_PERMISSION_FACTORY = \
    'invenio_files_rest.permissions.bucket_permission_factory'

FILES_REST_OBJECT_PERMISSION_FACTORY = \
    'invenio_files_rest.permissions.object_permission_factory'
"""Import path of permission factory."""

FILES_REST_OBJECT_KEY_MAX_LEN = 255
"""Maximum length of the ObjectVersion.key field.

.. warning::
   Setting this variable to anything higher than 255 is only supported
   with PostgreSQL database.
"""

FILES_REST_FILE_URI_MAX_LEN = 255
"""Maximum length of the FileInstance.uri field.

.. warning::
   Setting this variable to anything higher than 255 is only supported
   with PostgreSQL database.
"""

FILES_REST_RECORD_FILE_FACTORY = None
"""Import path of factory used to extract file from record."""

FILES_REST_STORAGE_PATH_SPLIT_LENGTH = 2
"""Length of the filename that should be taken to create its root dir."""

FILES_REST_STORAGE_PATH_DIMENSIONS = 1
"""Number of directory levels created for the storage."""
