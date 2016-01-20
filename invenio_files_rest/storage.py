# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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

"""Storage related module."""

import inspect
import sys

from flask import send_file
from fs.opener import fsopendir


class StorageError(Exception):

    """Exception raised when a storage operation fails."""


class StorageFactory(object):

    """Storage factory."""

    @staticmethod
    def get(uri, **kwargs):
        """Factory to create the storage object."""
        storage_classes = [obj
                           for (name, obj)
                           in inspect.getmembers(sys.modules[__name__])
                           if inspect.isclass(obj) and issubclass(obj, Storage)
                           ]
        for storage_class in storage_classes:
            if storage_class.uri_scheme and \
               uri.startswith(storage_class.uri_scheme):
                kwargs['_uri'] = uri
                return storage_class(kwargs)
        raise ValueError('No storage with uri scheme as in "{}".'.format(uri))


class Storage(object):

    """Base class for storage backends.

    :param data: A dict with data used to initialize the backend.
    """

    uri_scheme = None
    """URI scheme of the storage backend (e.g. s3://)."""

    def __init__(self, data):
        """Storage init."""
        self.uri = data['_uri']
        self.bucket_id = data.get('bucket_id', None)
        self.version_id = data.get('version_id', None)

    def make_path(self):
        """Make path to file in a given storage location."""
        if self.bucket_id and self.version_id:
            return "{}/{}".format(str(self.bucket_id), str(self.version_id))
        else:
            raise StorageError('Cannot make path because bucket and version '
                               'ids are missing.')

    def open(self, version_id):
        """Open a file in the storage for reading.

        :param version_id: The UUID of the file object.
        :returns: a file-like objec.
        """
        raise NotImplementedError

    def save(self, file_obj, filename):
        """Create a new file in the storage.

        :param fileobj: A file-like object containing the file data as
                        bytes or a bytestring.
        :param filename: secure filename.
        """
        raise NotImplementedError

    def get_size(self, file_loc, filename):
        """Get the size in bytes of a file.

        :param file_loc: The location of the file within the storage backend.
        :param filename: The filename of the file within the storage backend.
        """
        raise NotImplementedError

    def send_file(self, filename):
        """Send the file to the client.

        This returns a flask response that will eventually result in
        the user being offered to download the file (or view it in the
        browser).  Depending on the storage backend it may actually
        send a redirect to an external URL where the file is available.

        :param filename: The file name to use when sending the file to
                         the client.
        """
        raise NotImplementedError


class FileSystemStorage(Storage):

    """File system storage."""

    uri_scheme = 'file://'

    def save(self, file_obj, filename):
        """Save file in the file system."""
        try:
            with fsopendir(self.uri) as fs:
                path = self.make_path()
                if fs.exists(path):
                    raise ValueError('Conflict when creating target folder.')
                dest_folder = fs.makeopendir(path, recursive=True)
                file_obj.save(dest_folder.open(filename, 'wb'))
                return '{}{}'.format(
                    self.uri_scheme,
                    dest_folder.getsyspath('.')
                )
        except Exception as e:
            raise StorageError('Could not save file: {}'.format(e))

    def get_size(self, file_loc, filename):
        """Get file size."""
        try:
            with fsopendir(file_loc) as fs:
                return fs.getsize(filename)
        except Exception as e:
            raise StorageError(
                'Could not get size of "{}": {}'.format(filename, e)
            )

    def send_file(self, filename):
        """Send file to the client."""
        try:
            with fsopendir(self.uri) as fs:
                return send_file(
                    fs.getsyspath(filename),
                    attachment_filename=filename
                )
        except Exception as e:
            raise StorageError('Could not send file: {}'.format(e))


class AmazonS3(Storage):
    def get_size(self, file_loc, filename):
        raise NotImplementedError

    def send_file(self, filename):
        raise NotImplementedError

    def open(self, version_id):
        raise NotImplementedError

    def save(self, file_obj, filename):
        raise NotImplementedError