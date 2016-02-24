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

"""Storage related module."""

from __future__ import absolute_import, print_function

import hashlib
import time
from os.path import join

from fs.opener import opener

from .errors import StorageError
from .helpers import send_stream


def storage_factory(obj=None, fileinstance=None):
    """Factory function for creating a storage instance."""
    return PyFilesystemStorage(obj, fileinstance)


class Storage(object):
    """Base class for storage backends.

    :param object: A dict with data used to initialize the backend.
    """

    def __init__(self, object, fileinstance):
        """Storage init."""
        self.obj = object
        self.file = fileinstance

    def make_path(self):
        """Make path to file in a given storage location."""
        return join(
            str(self.obj.bucket_id),
            str(self.obj.version_id),
        )

    def save(self, incoming_stream, size=None, chunk_size=None):
        """Create a new file in the storage."""
        raise NotImplementedError

    def send_file(self):
        """Send the file to the client."""
        raise NotImplementedError

    def compute_checksum(self):
        """Compute checksum of file."""
        raise NotImplementedError

    def _compute_checksum(self, src, chunk_size=None):
        """Helper method to compute checksum from a stream.

        Naive implementation that can be overwritten by subclasses in order to
        provide more efficient implementation.
        """
        try:
            m = hashlib.md5()
            while 1:
                chunk = src.read(chunk_size)
                if not chunk:
                    break
                m.update(chunk)
            return "md5:{0}".format(m.hexdigest())
        except Exception as e:
            raise StorageError(
                'Could not compute checksum of file: {}'.format(e))

    def _save_stream(self, src, dst, chunk_size=None):
        """Save stream from src to dest and compute checksum."""
        chunk_size = chunk_size or 1024 * 64

        m = hashlib.md5()
        bytes_written = 0

        while 1:
            chunk = src.read(chunk_size)
            if not chunk:
                break
            dst.write(chunk)
            bytes_written += len(chunk)
            m.update(chunk)

        return bytes_written, "md5:{0}".format(m.hexdigest())


class PyFilesystemStorage(Storage):
    """File system storage using PyFilesystem."""

    def save(self, incoming_stream, size=None, chunk_size=None):
        """Save file in the file system."""
        uri = self.obj.bucket.location.uri
        path = self.make_path()

        with opener.opendir(uri) as fs:
            dest_file = fs.makeopendir(path, recursive=True).open('data', 'wb')
            bytes_written, checksum = self._save_stream(
                incoming_stream, dest_file, chunk_size=chunk_size)
            dest_file.close()

        return join(uri, path, 'data'), bytes_written, checksum

    def send_file(self, restricted=False):
        """Send file to the client."""
        try:
            fs, path = opener.parse(self.file.uri)
            fp = fs.open(path, 'rb')
            return send_stream(
                fp, path, self.file.size,
                time.mktime(self.file.updated.timetuple()),
                restricted=restricted, etag=self.file.checksum,
                content_md5=self.file.checksum)
        except Exception as e:
            raise StorageError('Could not send file: {}'.format(e))

    def compute_checksum(self):
        """Compute checksum of file."""
        fs, path = opener.parse(self.file.uri)
        fp = fs.open(path, 'rb')
        try:
            value = self._compute_checksum(fp)
        except StorageError:
            fp.close()
            raise
        return value
