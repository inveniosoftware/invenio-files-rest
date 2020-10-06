import os
import urllib.parse
from typing import Any, Dict, Optional, Type

from flask import current_app

from invenio_files_rest.models import FileInstance, Location
from .base import StorageBackend
from ..helpers import make_path


class StorageFactory:
    """A base storage factory, with sensible default behaviour."""

    def __init__(self, app):
        self.app = app

    def __call__(
        self,
        fileinstance: FileInstance,
    ) -> Optional[StorageBackend]:
        """Returns a FileStorage instance for a file, for manipulating file contents.
        """
        if not fileinstance.storage_backend:
            return None

        storage_backend_cls = self.resolve_storage_backend(fileinstance.storage_backend)
        storage_backend_kwargs = self.get_storage_backend_kwargs(fileinstance, storage_backend_cls)

        return storage_backend_cls(
            uri=fileinstance.uri,
            size=fileinstance.size,
            **storage_backend_kwargs
        )

    def initialize(
        self,
        fileinstance: FileInstance,
        size: int = 0,
        preferred_location: Location = None
    ) -> StorageBackend:
        if fileinstance.storage_backend:
            return self(fileinstance)  # type: ignore

        location = self.get_location(fileinstance, preferred_location)

        fileinstance.storage_backend = location.storage_backend

        storage_backend_cls = self.resolve_storage_backend(fileinstance.storage_backend)
        storage_backend_kwargs = self.get_storage_backend_kwargs(fileinstance, storage_backend_cls)

        uri = self.get_suggested_uri(
            fileinstance=fileinstance,
            location=location,
            storage_backend_cls=storage_backend_cls,
        )

        return storage_backend_cls(
            uri=uri,
            **storage_backend_kwargs,
        ).initialize(
            size=size,
        )

    def get_location(self, fileinstance: FileInstance, preferred_location: Location = None) -> Location:
        return preferred_location or Location.get_default()

    def get_storage_backend_name(self, fileinstance: FileInstance, preferred_location: Location) -> str:
        """"""
        if not preferred_location:
            raise ValueError("preferred_location required for default storage factory")
        return preferred_location.storage_backend

    def resolve_storage_backend(self, backend_name: str) -> Type[StorageBackend]:
        return self.app.config['FILES_REST_STORAGE_BACKENDS'][backend_name]

    def get_storage_backend_kwargs(
        self,
        fileinstance: FileInstance,
        storage_backend_cls: Type[StorageBackend],
    ) -> Dict[str, Any]:
        return {}

    def get_suggested_uri(
        self,
        fileinstance: FileInstance,
        location: Location,
        storage_backend_cls: Type[StorageBackend],
    ):
        return make_path(
            location,
            str(fileinstance.id),
            'data',
            current_app.config['FILES_REST_STORAGE_PATH_DIMENSIONS'],
            current_app.config['FILES_REST_STORAGE_PATH_SPLIT_LENGTH'],
        )
