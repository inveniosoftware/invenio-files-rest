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
from functools import partial
from os.path import join

from fs.opener import opener

from .errors import StorageError, UnexpectedFileSizeError
from .helpers import compute_md5_checksum, send_stream


def pyfs_storage_factory(fileinstance, objectversion=None, location=None,
                         **kwargs):
    """Factory function for creating a PyFS storage instance."""
    base_uri = None
    if objectversion:
        base_uri = objectversion.bucket.location.uri
    elif location:
        base_uri = location.uri

    return PyFilesystemStorage(
        fileinstance,
        base_uri=base_uri,
    )


class Storage(object):
    """Base class for storage backends.

    :param fileinstance: A file instance.
    """

    def __init__(self, fileinstance, **kwargs):
        """Storage init."""
        self.file = fileinstance

    def open(self, **kwargs):
        """Open file.

        The caller is responsible for closing the file.
        """
        raise NotImplementedError

    def send_file(self, **kwargs):
        """Send the file to the client."""
        raise NotImplementedError

    def save(self, incoming_stream, chunk_size=None, progress_callback=None):
        """Create a new file in the storage."""
        raise NotImplementedError

    def copy(self, src, chunk_size=None, progress_callback=None):
        """Copy data from another file instance."""
        fp = src.storage().open()
        try:
            return self.save(
                fp, chunk_size=chunk_size, progress_callback=progress_callback)
        finally:
            fp.close()

    def compute_checksum(self, chunk_size=None, progress_callback=None):
        """Compute checksum of file."""
        raise NotImplementedError

    def _compute_checksum(self, src, chunk_size=None, progress_callback=None):
        """Helper method to compute checksum from a stream.

        Naive implementation that can be overwritten by subclasses in order to
        provide more efficient implementation.
        """
        total_size = self.file.size
        if progress_callback:
            progress_callback = partial(progress_callback, total_size)

        try:
            return compute_md5_checksum(
                src, chunk_size=chunk_size, progress_callback=progress_callback
            )
        except Exception as e:
            raise StorageError(
                'Could not compute checksum of file: {}'.format(e))

    def _write_stream(self, src, dst, size=None, chunk_size=None,
                      progress_callback=None):
        """Helper method to save stream from src to dest + compute checksum."""
        chunk_size = chunk_size or 1024 * 64

        m = hashlib.md5()
        bytes_written = 0

        while 1:
            chunk = src.read(chunk_size)
            if size is not None and bytes_written > size:
                raise UnexpectedFileSizeError('File is bigger than expected.')
            if not chunk:
                if progress_callback:
                    progress_callback(bytes_written, bytes_written)
                break
            dst.write(chunk)
            bytes_written += len(chunk)
            m.update(chunk)
            if progress_callback:
                progress_callback(None, bytes_written)

        if size and bytes_written < size:
            raise UnexpectedFileSizeError('File is smaller than '
                                          'expected.')

        return bytes_written, "md5:{0}".format(m.hexdigest())


class PyFilesystemStorage(Storage):
    """File system storage using PyFilesystem.

    This storage class will store files according to the following pattern::

        <base_uri>/<file instance uuid>/data

    :param fileinstance: A file instance.
    :param base_uri: Base URI for where to store the file. Injected by
        :py:data:`pyfs_storage_factory`.
    :param filename: Filename of data file. Default: ``data``.
    """

    def __init__(self, fileinstance, base_uri=None, filename='data'):
        """Storage initialization."""
        self.base_uri = base_uri
        self.filename = filename
        super(PyFilesystemStorage, self).__init__(fileinstance)

    def make_path(self):
        """Generate a path as base location for file instance."""
        assert self.base_uri
        return join(self.base_uri, str(self.file.id))

    def open(self):
        """Open file.

        The caller is responsible for closing the file.
        """
        return opener.open(self.file.uri, mode='rb')

    def save(self, incoming_stream, size=None, chunk_size=None,
             progress_callback=None):
        """Save file in the file system."""
        fs = opener.opendir(self.file.uri or self.make_path(), create_dir=True)
        fp = fs.open(self.filename, 'wb')
        try:
            bytes_written, checksum = self._write_stream(
                incoming_stream, fp, chunk_size=chunk_size,
                progress_callback=progress_callback,
                size=size)
        finally:
            fp.close()

        uri = fs.getpathurl(self.filename, allow_none=True) or \
            fs.getsyspath(self.filename, allow_none=True)

        return uri, bytes_written, checksum

    def send_file(self, restricted=False, mimetype=None):
        """Send file to the client."""
        try:
            fs, path = opener.parse(self.file.uri)
            fp = fs.open(path, 'rb')
            return send_stream(
                fp, path, self.file.size,
                time.mktime(self.file.updated.timetuple()),
                mimetype=mimetype,
                restricted=restricted, etag=self.file.checksum,
                content_md5=self.file.checksum)
        except Exception as e:
            raise StorageError('Could not send file: {}'.format(e))

    def compute_checksum(self, chunk_size=None, progress_callback=None):
        """Compute checksum of file."""
        fp = opener.open(self.file.uri, mode='rb')
        try:
            value = self._compute_checksum(
                fp, progress_callback=progress_callback)
        except StorageError:
            raise
        finally:
            fp.close()
        return value
