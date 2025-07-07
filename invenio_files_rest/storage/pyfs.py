# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Storage related module."""


import os
import warnings
from pathlib import Path

from flask import current_app

from ..helpers import make_path
from .base import FileStorage


class FS:
    """An abstraction over the local filesystem.

    This is present for a "backward" compatibility with the PyFilesystem2 interface,
    but it is not a full implementation of PyFilesystem2's `osfs.OSFS`.

    When we remove this abstraction from the classes that inherit from PyFSFileStorage
    (such as in invenio-s3), we can remove this class and use `pathlib.Path` directly
    for file operations in PyFSFileStorage.
    """

    def __init__(self, base_directory, writeable=True, create=True):
        """Initialize the filesystem with a base directory.

        :param base_directory: The base directory for the filesystem.
        :param writeable: If True, the filesystem allows writing.
        :param create: If True, the base directory will be created if it does not exist.
        :raises FileNotFoundError: If the base directory does not exist and create is False
        """
        self._root_directory = Path(base_directory).resolve()
        self._writeable = writeable
        if create:
            self._root_directory.mkdir(parents=True, exist_ok=True)
        elif not self._root_directory.is_dir():
            raise FileNotFoundError(f"Directory {self._root_directory} does not exist.")

    def open(self, path, mode="rb"):
        """Open a file in the filesystem.

        :param path: The path to the file relative to the base directory.
        :param mode: The mode in which to open the file (e.g., 'rb', 'wb').
        :raises OSError: If trying to write to a read-only filesystem.
        :raises FileNotFoundError: If the file does not exist and mode is 'r'.
        :return: A file object opened in the specified mode.
        """
        full_path = self._get_full_path(path)
        if mode[0] == "w" and not self._writeable:
            raise OSError(f"Cannot write to {full_path}")
        return full_path.open(mode=mode)

    def exists(self, path):
        """Check if a file exists in the filesystem.

        :param path: The path to the file relative to the base directory.
        :return: True if the file exists, False otherwise.
        """
        full_path = self._get_full_path(path)
        return full_path.exists()

    def remove(self, path):
        """Remove a file from the filesystem.

        :param path: The path to the file relative to the base directory.
        :raises OSError: If the filesystem is not writeable.
        :raises FileNotFoundError: If the file does not exist.
        """
        full_path = self._get_full_path(path)
        if not self._writeable:
            raise OSError(f"Cannot remove {full_path} - not writeable")
        full_path.unlink()

    def removedir(self, path):
        """Remove a directory from the filesystem, provided it is empty.

        :param path: The path to the directory relative to the base directory.
        :raises OSError: If the filesystem is not writeable or if the directory is not empty.
        :raises FileNotFoundError: If the directory does not exist.
        """
        full_path = self._get_full_path(path)
        if not self._writeable:
            raise OSError(f"Cannot remove directory {full_path} - not writeable")
        full_path.rmdir()

    def walk(self, path):
        """Walk through the directory and yield file paths.

        :param path: The path to the directory relative to the base directory.
        :yield: A generator yielding file paths in the directory.

        Note: incompatible from the original PyFilesystem2 walk method as it returns
        a generator of tuples (dirpath, dirnames, filenames) where dirnames and filenames
        are lists of names, not FileInfo instances. It seems that this is used only
        in tests, so the implementation here should be good enough for that purpose.
        """
        full_path = self._get_full_path(path)
        yield from os.walk(full_path)

    def _get_full_path(self, path):
        """Concatenate root directory and the path.

        Checks that the resulting path is relative to the root directory and if not,
        raises a ValueError.
        """
        # make sure that path does not escape the base directory
        full_path = self._root_directory / path
        if not full_path.is_relative_to(self._root_directory):
            raise ValueError("Path must be relative to the root directory.")
        return full_path

    @classmethod
    def _get_path_from_uri(cls, uri_or_path):
        """Return the path from a URI or path string."""
        if uri_or_path.startswith("file://"):
            # Strip the 'file://' prefix
            uri_or_path = uri_or_path[7:]
        if "://" in uri_or_path:
            raise ValueError("Invalid URI format, expected a file URI or path.")

        return Path(uri_or_path)

    @classmethod
    def dirname(cls, uri_or_path):
        """Return the directory name of the given path."""
        return str(cls._get_path_from_uri(uri_or_path).parent)

    @classmethod
    def basename(cls, uri_or_path):
        """Return the base name of the given path."""
        return str(cls._get_path_from_uri(uri_or_path).name)

    @classmethod
    def split_path(cls, uri_or_path):
        """Split the path into directory and base name."""
        path = cls._get_path_from_uri(uri_or_path)
        return str(path.parent), str(path.name)


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

        if self._get_fs.__func__ is not PyFSFileStorage._get_fs:
            warnings.warn(
                "The _get_fs method is deprecated and will be removed. "
                "Please implement the abstract FileStorage instead of "
                "extending the PyFSFileStorage class.",
                DeprecationWarning,
            )

    def _get_fs(self, create_dir=True):
        """Return tuple with filesystem and filename."""
        filedir, filename = FS.split_path(self.fileurl)

        return (
            FS(filedir, writeable=True, create=create_dir),
            filename,
        )

    def open(self, mode="rb"):
        """Open file.

        The caller is responsible for closing the file.
        """
        if mode[0] == "r":
            create_dir = False
        else:
            create_dir = True
        fs, path = self._get_fs(create_dir=create_dir)
        return fs.open(path, mode=mode)

    def delete(self):
        """Delete a file.

        The base directory is also removed, as it is assumed that only one file
        exists in the directory.
        """
        fs, path = self._get_fs(create_dir=False)
        root_dir = FS.dirname(self.fileurl)
        if fs.exists(path):
            fs.remove(path)

        # PyFilesystem2 really doesn't want to remove the root directory,
        # so we need to be a bit creative
        root_path, dir_name = FS.split_path(root_dir)
        if self.clean_dir and dir_name:
            parent_fs = FS(root_path, writeable=True, create=False)
            if parent_fs.exists(dir_name):
                parent_fs.removedir(dir_name)

        return True

    def initialize(self, size=0):
        """Initialize file on storage and truncate to given size."""
        fs, path = self._get_fs()

        # Required for reliably opening the file on certain file systems:
        if fs.exists(path):
            fp = fs.open(path, mode="r+b")
        else:
            fp = fs.open(path, mode="wb")

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

    def save(
        self,
        incoming_stream,
        size_limit=None,
        size=None,
        chunk_size=None,
        progress_callback=None,
    ):
        """Save file in the file system."""
        fp = self.open(mode="wb")
        try:
            bytes_written, checksum = self._write_stream(
                incoming_stream,
                fp,
                chunk_size=chunk_size,
                progress_callback=progress_callback,
                size_limit=size_limit,
                size=size,
            )

            self._size = bytes_written
            return self.fileurl, bytes_written, checksum

        except Exception as e:
            fp.close()
            self.delete()
            raise e
        finally:
            fp.close()

    def update(
        self,
        incoming_stream,
        seek=0,
        size=None,
        chunk_size=None,
        progress_callback=None,
    ):
        """Update a file in the file system."""
        fp = self.open(mode="r+b")
        try:
            fp.seek(seek)
            bytes_written, checksum = self._write_stream(
                incoming_stream,
                fp,
                chunk_size=chunk_size,
                size=size,
                progress_callback=progress_callback,
            )
        finally:
            fp.close()

        return bytes_written, checksum


def pyfs_storage_factory(
    fileinstance=None,
    default_location=None,
    default_storage_class=None,
    filestorage_class=PyFSFileStorage,
    fileurl=None,
    size=None,
    modified=None,
    clean_dir=True,
):
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
                "data",
                current_app.config["FILES_REST_STORAGE_PATH_DIMENSIONS"],
                current_app.config["FILES_REST_STORAGE_PATH_SPLIT_LENGTH"],
            )

    return filestorage_class(fileurl, size=size, modified=modified, clean_dir=clean_dir)
