# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Implementation of various utility functions."""
import hashlib
import mimetypes
from typing import Callable

import six
from flask import current_app
from werkzeug.utils import import_string

from invenio_files_rest.errors import FileSizeError, UnexpectedFileSizeError

ENCODING_MIMETYPES = {
    'gzip': 'application/gzip',
    'compress': 'application/gzip',
    'bzip2': 'application/x-bzip2',
    'xz': 'application/x-xz',
}
"""Mapping encoding to MIME types which are not in mimetypes.types_map."""


def obj_or_import_string(value, default=None):
    """Import string or return object.

    :params value: Import path or class object to instantiate.
    :params default: Default object to return if the import fails.
    :returns: The imported object.
    """
    if isinstance(value, six.string_types):
        return import_string(value)
    elif value:
        return value
    return default


def load_or_import_from_config(key, app=None, default=None):
    """Load or import value from config.

    :returns: The loaded value.
    """
    app = app or current_app
    imp = app.config.get(key)
    return obj_or_import_string(imp, default=default)


def guess_mimetype(filename):
    """Map extra mimetype with the encoding provided.

    :returns: The extra mimetype.
    """
    m, encoding = mimetypes.guess_type(filename)
    if encoding:
        m = ENCODING_MIMETYPES.get(encoding, None)
    return m or 'application/octet-stream'



def check_sizelimit(size_limit, bytes_written, total_size):
    """Check if size limit was exceeded.

    :param size_limit: The size limit.
    :param bytes_written: The total number of bytes written.
    :param total_size: The total file size.
    :raises invenio_files_rest.errors.UnexpectedFileSizeError: If the bytes
        written exceed the total size.
    :raises invenio_files_rest.errors.FileSizeError: If the bytes
        written are major than the limit size.
    """
    if size_limit is not None and bytes_written > size_limit:
        desc = 'File size limit exceeded.' \
            if isinstance(size_limit, int) else size_limit.reason
        raise FileSizeError(description=desc)

    # Never write more than advertised
    if total_size is not None and bytes_written > total_size:
        raise UnexpectedFileSizeError(
            description='File is bigger than expected.')


def check_size(bytes_written, total_size):
    """Check if expected amounts of bytes have been written.

    :param bytes_written: The total number of bytes written.
    :param total_size: The total file size.
    :raises invenio_files_rest.errors.UnexpectedFileSizeError: If the bytes
        written exceed the total size.
    """
    if total_size and bytes_written < total_size:
        raise UnexpectedFileSizeError(
            description='File is smaller than expected.')



class PassthroughChecksum:
    def __init__(
        self,
        fp,
        hash_name,
        progress_callback: Callable[[int, int], None] = None,
        offset: int = 0,
        size_limit: int = None,
        size: int=None
    ):
        """
        :param fp: A file-like option open for reading
        :param hash_name: A hashlib hash algorithm name
        :param progress_callback: An optional function that will receive the number of bytes read, and the total file
            size
        """
        self.hash_name = hash_name
        self._sum = hashlib.new(hash_name) if hash_name else None
        self._update_sum = self._sum.update if self._sum else lambda chunk: None
        self._fp = fp
        self._bytes_read = 0
        self._progress_callback = progress_callback
        self._offset = offset
        self._size_limit = size_limit
        self._size = size

    def read(self, size=-1):
        chunk = self._fp.read(size)
        self._bytes_read += len(chunk)
        print("CSL", self._size_limit, self.bytes_read, self._size)
        check_sizelimit(self._size_limit, self.bytes_read, self._size)
        self._update_sum(chunk)
        if self._progress_callback:
            self._progress_callback(self._bytes_read, self._bytes_read + self._offset)
        return chunk

    def __getattr__(self, item):
        return getattr(self._fp, item)

    @property
    def checksum(self):
        """The {hash_name}:{hash} string for the bytes read so far."""
        if self._sum:
            return '{0}:{1}'.format(
                self.hash_name, self._sum.hexdigest())

    @property
    def bytes_read(self):
        return self._bytes_read

    @property
    def total_size(self):
        return self._bytes_read + self._offset
