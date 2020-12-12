# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2020 CERN.
# Copyright (C) 2020 Cottage Labs LLP.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""The previous invenio_files_rest.storage implementation.

These classes and factory are included so that we can test that there are no
regressions against them when implementing the new storage interface, and so
ensure backwards compatibility.
"""

from __future__ import absolute_import, print_function

import hashlib
from calendar import timegm
from flask import current_app
from fs.opener import opener
from fs.path import basename, dirname
from functools import partial

from invenio_files_rest.errors import StorageError
from invenio_files_rest.helpers import chunk_size_or_default, \
    compute_checksum, make_path, send_stream
from invenio_files_rest.utils import check_size, check_sizelimit


class FileStorage(object):
    """Base class for storage interface to a single file."""

    def __init__(self, size=None, modified=None):
        """Initialize storage object."""
        self._size = size
        self._modified = timegm(modified.timetuple()) if modified else None

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
                  checksum=None, trusted=False, chunk_size=None,
                  as_attachment=False):
        """Send the file to the client."""
        try:
            fp = self.open(mode='rb')
        except Exception as e:
            raise StorageError('Could not send file: {}'.format(e))

        try:
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
                content_md5=md5_checksum,
                chunk_size=chunk_size,
                trusted=trusted,
                as_attachment=as_attachment,
            )
        except Exception as e:
            fp.close()
            raise StorageError('Could not send file: {}'.format(e))

    def checksum(self, chunk_size=None, progress_callback=None, **kwargs):
        """Compute checksum of file."""
        fp = self.open(mode='rb')
        try:
            value = self._compute_checksum(
                fp, size=self._size, chunk_size=None,
                progress_callback=progress_callback)
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
    def _init_hash(self):
        """Initialize message digest object.

        Overwrite this method if you want to use different checksum
        algorithm for your storage backend.
        """
        return 'md5', hashlib.md5()

    def _compute_checksum(self, stream, size=None, chunk_size=None,
                          progress_callback=None, **kwargs):
        """Get helper method to compute checksum from a stream.

        Naive implementation that can be overwritten by subclasses in order to
        provide more efficient implementation.
        """
        if progress_callback and size:
            progress_callback = partial(progress_callback, size)
        else:
            progress_callback = None

        try:
            algo, m = self._init_hash()
            return compute_checksum(
                stream, algo, m,
                chunk_size=chunk_size,
                progress_callback=progress_callback,
                **kwargs
            )
        except Exception as e:
            raise StorageError(
                'Could not compute checksum of file: {0}'.format(e))

    def _write_stream(self, src, dst, size=None, size_limit=None,
                      chunk_size=None, progress_callback=None):
        """Get helper to save stream from src to dest + compute checksum.

        :param src: Source stream.
        :param dst: Destination stream.
        :param size: If provided, this exact amount of bytes will be
            written to the destination file.
        :param size_limit: ``FileSizeLimit`` instance to limit number of bytes
            to write.
        """
        chunk_size = chunk_size_or_default(chunk_size)

        algo, m = self._init_hash()
        bytes_written = 0

        while 1:
            # Check that size limits aren't bypassed
            check_sizelimit(size_limit, bytes_written, size)

            chunk = src.read(chunk_size)

            if not chunk:
                if progress_callback:
                    progress_callback(bytes_written, bytes_written)
                break

            dst.write(chunk)

            bytes_written += len(chunk)

            if m:
                m.update(chunk)

            if progress_callback:
                progress_callback(None, bytes_written)

        check_size(bytes_written, size)

        return bytes_written, '{0}:{1}'.format(
            algo, m.hexdigest()) if m else None


class PyFSFileStorage(FileStorage):
    """File system storage using PyFilesystem for access the file.

    This storage class will store files according to the following pattern:
    ``<base_uri>/<file instance uuid>/data``.

    .. warning::

       File operations are not atomic. E.g. if errors happens during e.g.
       updating part of a file it will leave the file in an inconsistent
       state. The storage class tries as best as possible to handle errors
       and leave the system in a consistent state.
    """

    def __init__(self, fileurl, size=None, modified=None, clean_dir=True):
        """Storage initialization."""
        self.fileurl = fileurl
        self.clean_dir = clean_dir
        super(PyFSFileStorage, self).__init__(size=size, modified=modified)

    def _get_fs(self, create_dir=True):
        """Return tuple with filesystem and filename."""
        filedir = dirname(self.fileurl)
        filename = basename(self.fileurl)

        return (
            opener.opendir(filedir, writeable=True, create_dir=create_dir),
            filename
        )

    def open(self, mode='rb'):
        """Open file.

        The caller is responsible for closing the file.
        """
        fs, path = self._get_fs()
        return fs.open(path, mode=mode)

    def delete(self):
        """Delete a file.

        The base directory is also removed, as it is assumed that only one file
        exists in the directory.
        """
        fs, path = self._get_fs(create_dir=False)
        if fs.exists(path):
            fs.remove(path)
        if self.clean_dir and fs.exists('.'):
            fs.removedir('.')
        return True

    def initialize(self, size=0):
        """Initialize file on storage and truncate to given size."""
        fs, path = self._get_fs()

        # Required for reliably opening the file on certain file systems:
        if fs.exists(path):
            fp = fs.open(path, mode='r+b')
        else:
            fp = fs.open(path, mode='wb')

        try:
            fp.truncate(size)
        except Exception:
            fp.close()
            self.delete()
            raise
        finally:
            fp.close()

        self._size = size

        return self.fileurl, size, None

    def save(self, incoming_stream, size_limit=None, size=None,
             chunk_size=None, progress_callback=None):
        """Save file in the file system."""
        fp = self.open(mode='wb')
        try:
            bytes_written, checksum = self._write_stream(
                incoming_stream, fp, chunk_size=chunk_size,
                progress_callback=progress_callback,
                size_limit=size_limit, size=size)
        except Exception:
            fp.close()
            self.delete()
            raise
        finally:
            fp.close()

        self._size = bytes_written

        return self.fileurl, bytes_written, checksum

    def update(self, incoming_stream, seek=0, size=None, chunk_size=None,
               progress_callback=None):
        """Update a file in the file system."""
        fp = self.open(mode='r+b')
        try:
            fp.seek(seek)
            bytes_written, checksum = self._write_stream(
                incoming_stream, fp, chunk_size=chunk_size,
                size=size, progress_callback=progress_callback)
        finally:
            fp.close()

        return bytes_written, checksum


def pyfs_storage_factory(fileinstance=None, default_location=None,
                         default_storage_class=None,
                         filestorage_class=PyFSFileStorage, fileurl=None,
                         size=None, modified=None, clean_dir=True):
    """Get factory function for creating a PyFS file storage instance."""
    # Either the FileInstance needs to be specified or all filestorage
    # class parameters need to be specified
    assert fileinstance or (fileurl and size)

    if fileinstance:
        # FIXME: Code here should be refactored since it assumes a lot on the
        # directory structure where the file instances are written
        fileurl = None
        size = fileinstance.size
        modified = fileinstance.updated

        if fileinstance.uri:
            # Use already existing URL.
            fileurl = fileinstance.uri
        else:
            assert default_location
            # Generate a new URL.
            fileurl = make_path(
                default_location,
                str(fileinstance.id),
                'data',
                current_app.config['FILES_REST_STORAGE_PATH_DIMENSIONS'],
                current_app.config['FILES_REST_STORAGE_PATH_SPLIT_LENGTH'],
            )

    return filestorage_class(
        fileurl, size=size, modified=modified, clean_dir=clean_dir)
