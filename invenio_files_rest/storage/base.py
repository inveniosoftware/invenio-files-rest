# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""File storage base module."""

from __future__ import absolute_import, print_function

import hashlib
import warnings
from calendar import timegm
from datetime import datetime
from typing import Any, Callable, Dict, Tuple

import typing
from flask import current_app

from .legacy import FileStorage
from ..errors import StorageError
from ..helpers import chunk_size_or_default, compute_checksum, send_stream
from ..utils import check_size, check_sizelimit


__all__ = ('FileStorage', 'StorageBackend')


class StorageBackend:
    """Base class for storage interface to a single file."""

    checksum_hash_name = 'md5'

    def __init__(
        self, uri: str = None,
        size: int = None,
        modified: datetime = None
    ):
        """Initialize storage object."""
        self.uri = uri
        self._size = size
        self._modified = timegm(modified.timetuple()) if modified else None

    @classmethod
    def get_backend_name(cls):
        """Return the backend name for this StorageBackend.

        This performs a reverse-lookup in FILES_REST_STORAGE_BACKENDS and then
        caches the result.
        """
        try:
            return cls._backend_name
        except AttributeError:
            backends = current_app.config['FILES_REST_STORAGE_BACKENDS']
            for name, backend_cls in backends.items():
                if cls is backend_cls:
                    cls._backend_name = name
                    break
            else:
                raise RuntimeError(
                    "{} isn't listed in FILES_REST_STORAGE_BACKENDS "
                    "config".format(cls)
                )
            return cls._backend_name

    def open(self):
        """Open the file.

        The caller is responsible for closing the file.
        """
        raise NotImplementedError

    def delete(self):
        """Delete the file."""
        raise NotImplementedError

    def initialize(self, size=0):
        """Initialize the file on the storage and truncate to the given size."""
        return {
            'readable': False,
            'writable': True,
            'uri': self.uri,
            'size': size,
            **self._initialize(size=size),
        }

    def _initialize(self, size=0) -> Dict[Any, str]:
        """Override this to perform file storage initialization."""
        raise NotImplementedError

    def save(
        self,
        incoming_stream,
        size_limit=None,
        size=None,
        chunk_size=None,
        progress_callback: Callable[[int, int], None] = None
    ):
        """Save incoming stream to file storage."""
        with self.get_save_stream() as output_stream:
            result = self._write_stream(
                incoming_stream,
                output_stream,
                size_limit=size_limit,
                size=size,
                chunk_size=chunk_size,
                progress_callback=progress_callback,
            )
        self._size = result['size']
        if not result['checksum']:
            result['checksum'] = self.checksum(chunk_size=chunk_size)
        return {
            'uri': self.uri,
            'readable': True,
            'writable': False,
            'storage_class': 'S',
            **result,
        }

    def get_save_stream(self) -> typing.ContextManager:
        """Return a context manager for a file-like object for writing.

        The return value should be a context manager that provides a file-like
        object when entered, and performs any necessary clean-up when exited
        (e.g. closing the file).
        """
        raise NotImplementedError

    def update(self, incoming_stream, seek=0, size=None, chunk_size=None,
               progress_callback=None) -> Tuple[int, str]:
        """Update part of file with incoming stream."""
        with self.get_update_stream(seek) as output_stream:
            result = self._write_stream(
                    incoming_stream,
                    output_stream,
                    size=size,
                    chunk_size=chunk_size,
                    progress_callback=progress_callback,
                )
        self._size = seek + result['size']
        return result['size'], result['checksum']

    def get_update_stream(self, seek) -> typing.ContextManager:
        """Return a context manager for a file-like object for updating.

        The return value should be a context manager that provides a file-like
        object when entered, and performs any necessary clean-up when exited
        (e.g. closing the file).
        """
        raise NotImplementedError

    def _write_stream(
        self,
        incoming_stream,
        output_stream,
        *,
        size_limit=None,
        size=None,
        chunk_size=None,
        progress_callback=None,
    ):
        """Copy from one stream to another.

         This honors size limits and performs requested progress callbacks once
         data has been written to the output stream.
         """
        chunk_size = chunk_size_or_default(chunk_size)

        algo, checksum = self._init_hash()
        update_sum = checksum.update if checksum else lambda chunk: None

        bytes_written = 0

        while True:
            # Check that size limits aren't bypassed
            check_sizelimit(size_limit, bytes_written, size)

            chunk = incoming_stream.read(chunk_size)

            if not chunk:
                if progress_callback:
                    progress_callback(bytes_written, bytes_written)
                break

            output_stream.write(chunk)

            bytes_written += len(chunk)

            update_sum(chunk)

            if progress_callback:
                progress_callback(None, bytes_written)

        check_size(bytes_written, size)

        return {
            'checksum': (
                f'{self.checksum_hash_name}:{checksum.hexdigest()}'
                if checksum else None
            ),
            'size': bytes_written,
        }

    #
    # Default implementation
    #
    def send_file(
        self,
        filename,
        mimetype=None,
        restricted=True,
        checksum=None,
        trusted=False,
        chunk_size=None,
        as_attachment=False
    ):
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

    def checksum(self, chunk_size=None, progress_callback=None):
        """Compute checksum of file."""
        algo, m = self._init_hash()
        if not m:
            return None

        chunk_size = chunk_size_or_default(chunk_size)

        with self.open(mode='rb') as fp:
            algo, m = self._init_hash()
            return compute_checksum(
                fp, algo, m,
                chunk_size=chunk_size,
                progress_callback=progress_callback
            )

    def copy(self, src, chunk_size=None, progress_callback=None):
        """Copy data from another file instance.

        :param src: Source stream.
        :param chunk_size: Chunk size to read from source stream.
        """
        warnings.warn(
            "Call save() with the other already-open FileStorage passed in "
            "instead.",
            DeprecationWarning
        )
        with src.open() as fp:
            return self.save(
                fp, chunk_size=chunk_size, progress_callback=progress_callback)

    #
    # Helpers
    #
    def _init_hash(self):
        """Initialize message digest object.

        Overwrite this method if you want to use different checksum
        algorithm for your storage backend.
        """
        if self.checksum_hash_name:
            return self.checksum_hash_name, hashlib.new(self.checksum_hash_name)
        else:
            return None, None
