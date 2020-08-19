import os
from typing import Any, Dict, Type

from invenio_files_rest.models import FileInstance
from .base import FileStorage


class StorageFactory:
    """A base storage factory, with sensible default behaviour."""

    def __init__(self, app):
        self.app = app

    def __call__(self, fileinstance: FileInstance) -> FileStorage:
        """Returns a FileStorage instance for a file, for manipulating file contents."""

        if not fileinstance.storage_backend:
            fileinstance.storage_backend = self.get_storage_backend_name(fileinstance)

        storage_backend_cls = self.app.config['FILES_REST_STORAGE_BACKENDS'][fileinstance.storage_backend]
        storage_backend_kwargs = self.get_storage_backend_kwargs(fileinstance, storage_backend_cls)

        if not fileinstance.uri:
            fileinstance.uri = self.get_uri(fileinstance, storage_backend_cls)

        return storage_backend_cls(fileinstance.uri, **storage_backend_kwargs)

    def get_storage_backend_name(self, fileinstance: FileInstance) -> str:
        return self.app.config['FILES_REST_DEFAULT_STORAGE_BACKEND']

    def get_storage_backend_kwargs(self, fileinstance: FileInstance, storage_backend_cls: Type[FileStorage]) -> Dict[str, Any]:
        return {}

    def get_uri(self, fileinstance: FileInstance, storage_backend_cls: Type[FileStorage]) -> str:
        id = fileinstance.id.hex
        return os.path.join(id[0:2], id[2:4], id[4:6], id)
