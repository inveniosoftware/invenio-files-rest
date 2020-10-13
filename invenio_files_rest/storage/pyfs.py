# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Storage related module."""

from __future__ import absolute_import, print_function

import contextlib
import shutil

from flask import current_app
from fs.opener import opener
from fs.path import basename, dirname

from ..helpers import chunk_size_or_default, make_path
from .base import StorageBackend
from .legacy import PyFSFileStorage, pyfs_storage_factory

__all__ = ('PyFSFileStorage', 'pyfs_storage_factory', 'PyFSStorageBackend')

from ..utils import check_size, check_sizelimit


class PyFSStorageBackend(StorageBackend):
    """File system storage using PyFilesystem for access the file.

    This storage class will store files according to the following pattern:
    ``<base_uri>/<file instance uuid>/data``.

    .. warning::

       File operations are not atomic. E.g. if errors happens during e.g.
       updating part of a file it will leave the file in an inconsistent
       state. The storage class tries as best as possible to handle errors
       and leave the system in a consistent state.

    """

    def __init__(self, *args, clean_dir=True, **kwargs):
        """Storage initialization."""
        # if isinstance(args[0], str):
        #     raise NotImplementedError
        self.clean_dir = clean_dir
        super().__init__(*args, **kwargs)

    def _get_fs(self, create_dir=True):
        """Return tuple with filesystem and filename."""
        filedir = dirname(self.uri)
        filename = basename(self.uri)

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

    def _initialize(self, size=0):
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

        return {}

    @contextlib.contextmanager
    def get_save_stream(self):
        """Open the underlying file for writing, and delete it if there was a problem."""
        fp = self.open(mode='wb')
        try:
            yield fp
        except Exception:
            self.delete()
            raise
        finally:
            fp.close()

    def get_update_stream(self, seek):
        """Open the underlying file for updates, seeking as requested."""
        fp = self.open(mode='r+b')
        fp.seek(seek)
        return contextlib.closing(fp)
