# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""File storage base module."""

from __future__ import absolute_import, annotations, print_function

import hashlib
import urllib.parse
import warnings
from calendar import timegm
from datetime import datetime
from functools import partial
from typing import Any, Callable, Dict, TYPE_CHECKING, Tuple

from flask import current_app

from ..errors import FileSizeError, StorageError, UnexpectedFileSizeError
from ..helpers import chunk_size_or_default, compute_checksum, make_path, send_stream
from ..utils import check_size, check_sizelimit, PassthroughChecksum

from .legacy import FileStorage

if TYPE_CHECKING:
    from ..models import FileInstance


__all__ = ['FileStorage', 'StorageBackend']


class StorageBackendMeta(type):
    @property
    def backend_name(cls):
        try:
            return cls._backend_name
        except AttributeError:
            for name, backend_cls in current_app.config['FILES_REST_STORAGE_BACKENDS'].items():
                if cls is backend_cls:
                    cls._backend_name = name
                    break
            else:
                raise RuntimeError("{} isn't listed in FILES_REST_STORAGE_BACKENDS config".format(cls))
            return cls._backend_name


class StorageBackend(metaclass=StorageBackendMeta):
    """Base class for storage interface to a single file."""

    checksum_hash_name = 'md5'

    def __init__(self, uri: str=None, size: int=None, modified: datetime=None, *, filepath=None):
        """Initialize storage object."""
        self.uri = uri or filepath
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
        return {
            'readable': False,
            'writable': True,
            'uri': self.uri,
            'size': size,
            **self._initialize(size=size),
        }

    def _initialize(self, size=0):
        raise NotImplementedError

    def save(self, incoming_stream, size_limit=None, size=None,
             chunk_size=None, progress_callback: Callable[[int, int], None] = None
             ):
        """Save incoming stream to file storage."""

        incoming_stream = PassthroughChecksum(
            incoming_stream,
            hash_name=self.checksum_hash_name,
            progress_callback=progress_callback,
            size_limit=size_limit,
            size=size,
        )

        result = self._save(
            incoming_stream,
            size=None,
            chunk_size=None
        )

        check_size(incoming_stream.bytes_read, size)
        self._size = incoming_stream.total_size

        return {
            'checksum': incoming_stream.checksum,
            'size': incoming_stream.total_size,
            'uri': self.uri,
            'readable': True,
            'writable': False,
            'storage_class': 'S',
            **result,
        }

    def _save(self, incoming_stream, size_limit=None, size=None,
             chunk_size=None) -> Dict[str, Any]:
        """Save incoming stream to file storage."""
        raise NotImplementedError

    def update(self, incoming_stream, seek=0, size=None, chunk_size=None,
               progress_callback=None) -> Tuple[int, str]:
        """Update part of file with incoming stream."""
        incoming_stream = PassthroughChecksum(
            incoming_stream,
            hash_name=self.checksum_hash_name,
            progress_callback=progress_callback,
            size=size,
        )

        self._update(
            incoming_stream,
            seek=seek,
            size=None,
            chunk_size=chunk_size,
        )

        return incoming_stream.bytes_read, incoming_stream.checksum

    def _update(self, incoming_stream, seek=0, size=None, chunk_size=None):
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
        warnings.warn("Call save with the other already-open FileStorage passed in instead.", DeprecationWarning)
        fp = src.open(mode='rb')
        try:
            return self.save(
                fp, chunk_size=chunk_size, progress_callback=progress_callback)
        finally:
            fp.close()

    @classmethod
    def get_uri(self, fileinstance: FileInstance, base_uri: str) -> str:
        return make_path(
            base_uri,
            str(fileinstance.id),
            'data',
            current_app.config['FILES_REST_STORAGE_PATH_DIMENSIONS'],
            current_app.config['FILES_REST_STORAGE_PATH_SPLIT_LENGTH'],
        )

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
