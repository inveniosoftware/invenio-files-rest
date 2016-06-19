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

from ..errors import FileSizeError, StorageError, UnexpectedFileSizeError
from ..helpers import compute_md5_checksum, send_stream


class FileStorage(object):
    """Base class for storage interface to a single file."""

    def __init__(self, size=None, modified=None):
        """Initialize storage object."""
        self._size = size
        self._modified = \
            time.mktime(modified.timetuple()) if modified else None

    def open(self, mode=None):
        """Open the file.

        The caller is responsible for closing the file.
        """
        raise NotImplementedError

    def delete(self):
        """Delete the file."""
        raise NotImplementedError

    def initialize(self, size=0):
        """Initialize the file on the storage + truncate to the given size."""
        raise NotImplementedError

    def save(self, incoming_stream, size_limit=None, size=None,
             chunk_size=None, progress_callback=None):
        """Save incoming stream to file storage."""
        raise NotImplementedError

    def update(self, incoming_stream, seek=0, size=None, chunk_size=None,
               progress_callback=None):
        """Update part of file with incoming stream."""
        raise NotImplementedError

    #
    # Default implementation
    #
    def send_file(self, filename, mimetype=None, restricted=True,
                  checksum=None):
        """Send the file to the client."""
        try:
            fp = self.open(mode='rb')

            md5_checksum = None
            if checksum:
                algo, value = checksum.split(':')
                if algo == 'md5':
                    md5_checksum = value

            # Send stream is responsible for closing the file.
            return send_stream(
                fp,
                filename,
                self._size,
                self._modified,
                mimetype=mimetype,
                restricted=restricted,
                etag=checksum,
                content_md5=md5_checksum)
        except Exception as e:
            fp.close()
            raise StorageError('Could not send file: {}'.format(e))

    def checksum(self, chunk_size=None, progress_callback=None):
        """Compute checksum of file."""
        fp = self.open(mode='rb')
        try:
            value = self._compute_checksum(
                fp, size=self._size, progress_callback=progress_callback)
        except StorageError:
            raise
        finally:
            fp.close()
        return value

    def copy(self, src, chunk_size=None, progress_callback=None):
        """Copy data from another file instance.

        :param src: Source stream.
        :param chunk_size: Chunk size to read from source stream.
        """
        fp = src.open(mode='rb')
        try:
            return self.save(
                fp, chunk_size=chunk_size, progress_callback=progress_callback)
        finally:
            fp.close()

    #
    # Helpers
    #
    def _compute_checksum(self, stream, size=None, chunk_size=None,
                          progress_callback=None):
        """Helper method to compute checksum from a stream.

        Naive implementation that can be overwritten by subclasses in order to
        provide more efficient implementation.
        """
        if progress_callback and size:
            progress_callback = partial(progress_callback, size)
        else:
            progress_callback = None

        try:
            return compute_md5_checksum(
                stream,
                chunk_size=chunk_size,
                progress_callback=progress_callback
            )
        except Exception as e:
            raise StorageError(
                'Could not compute checksum of file: {0}'.format(e))

    def _write_stream(self, src, dst, size=None, size_limit=None,
                      chunk_size=None, progress_callback=None):
        """Helper method to save stream from src to dest + compute checksum.

        :param src: Source stream.
        :param dst: Destination stream.
        :param size: If provided, this exact amount of bytes will be
            written to the destination file.
        :param size_limit: ``FileSizeLimit`` instance to limit number of bytes
            to write.
        """
        chunk_size = chunk_size or 1024 * 64

        m = hashlib.md5()
        bytes_written = 0

        while 1:
            # Check that size limits aren't bypassed
            if size_limit is not None and bytes_written > size_limit:
                desc = 'File size limit exceeded.' \
                    if isinstance(size_limit, int) else size_limit.reason
                raise FileSizeError(description=desc)

            # Never write more than advertised
            if size is not None and bytes_written > size:
                raise UnexpectedFileSizeError(
                    description='File is bigger than expected.')

            chunk = src.read(chunk_size)
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
            raise UnexpectedFileSizeError(
                description='File is smaller than expected.')

        return bytes_written, "md5:{0}".format(m.hexdigest())
