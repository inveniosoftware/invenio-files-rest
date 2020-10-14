"""Contains the base storage factory implementation."""

from typing import Any, Dict, Optional, Type

from flask import current_app

from invenio_files_rest.models import FileInstance, Location
from .base import StorageBackend
from ..helpers import make_path


class StorageFactory:
    """A base storage factory, with sensible default behaviour.

    You may subclass this factory to implement custom behaviour. If you do
    this, remember to set FILES_REST_STORAGE_FACTORY to the right import path
    for your subclass.
    """

    def __init__(self, app):
        """Initialize the storage factory."""
        self.app = app

    def __call__(
        self,
        fileinstance: FileInstance,
    ) -> Optional[StorageBackend]:
        """Return a FileStorage instance for a file, for manipulating contents.

        This requires that the fileinstance already has an associated storage
        backend. If not, you should call initialize() instead to initialize
        storage for the file instance.
        """
        if not fileinstance.storage_backend:
            return None

        storage_backend_cls = self.resolve_storage_backend(
            fileinstance.storage_backend
        )
        storage_backend_kwargs = self.get_storage_backend_kwargs(
            fileinstance, storage_backend_cls
        )

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
        """Initialize storage for a new file.

        If provided, `preferred_location` will inform where the file will be
        stored, but may be ignored if this factory is subclassed and
        `get_location()` is overridden.
        """
        if fileinstance.storage_backend:
            return self(fileinstance)  # type: ignore

        location = self.get_location(fileinstance, preferred_location)

        fileinstance.storage_backend = location.storage_backend

        storage_backend_cls = self.resolve_storage_backend(
            fileinstance.storage_backend
        )
        storage_backend_kwargs = self.get_storage_backend_kwargs(
            fileinstance, storage_backend_cls
        )

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

    def get_location(
        self,
        fileinstance: FileInstance,
        preferred_location: Location = None
    ) -> Location:
        """Return a Location for storing a new file.

        This base implementation returns the preferred_location if it's
        provided, or the default location recorded in the database. This method
        can be overridden if some other methodology is required.
        """
        return preferred_location or Location.get_default()

    def resolve_storage_backend(
        self, backend_name: str
    ) -> Type[StorageBackend]:
        """Resolve a storage backend name to the associated backend class.

        This base implementation resolves backends from the
        FILES_REST_STORAGE_BACKENDS app config setting.
        """
        return self.app.config['FILES_REST_STORAGE_BACKENDS'][backend_name]

    def get_storage_backend_kwargs(
        self,
        fileinstance: FileInstance,
        storage_backend_cls: Type[StorageBackend],
    ) -> Dict[str, Any]:
        """Retrieve any instantiation kwargs for the storage backend.

        This returns an empty dict by defaut, but can be overridden to provide
        backend-specific instantiation parameters if necessary.
        """
        return {}

    def get_suggested_uri(
        self,
        fileinstance: FileInstance,
        location: Location,
        storage_backend_cls: Type[StorageBackend],
    ):
        """Generate a suggested URI for new files.

        This can be overridden if your implementation requires some other file
        layout for storage. Note that individual storage backends may choose to
        ignore the suggested URI if they organise files by some other scheme.
        """
        return make_path(
            location,
            str(fileinstance.id),
            'data',
            current_app.config['FILES_REST_STORAGE_PATH_DIMENSIONS'],
            current_app.config['FILES_REST_STORAGE_PATH_SPLIT_LENGTH'],
        )
