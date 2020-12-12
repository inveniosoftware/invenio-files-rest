# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
# Copyright (C) 2020 Cottage Labs LLP.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""File storage interface."""

from __future__ import absolute_import, print_function

from .base import FileStorage, StorageBackend
from .factory import StorageFactory
from .pyfs import PyFSFileStorage, PyFSStorageBackend, pyfs_storage_factory

__all__ = (
    'FileStorage',
    'StorageBackend',
    'pyfs_storage_factory',
    'PyFSFileStorage',
    'PyFSStorageBackend',
    'StorageFactory',
)
