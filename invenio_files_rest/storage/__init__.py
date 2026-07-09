# SPDX-FileCopyrightText: 2015-2019 CERN.
# SPDX-License-Identifier: MIT

"""File storage interface."""

from .base import FileStorage
from .pyfs import PyFSFileStorage, pyfs_storage_factory
from .router import storage_factory_router

__all__ = (
    "FileStorage",
    "pyfs_storage_factory",
    "PyFSFileStorage",
    "storage_factory_router",
)
