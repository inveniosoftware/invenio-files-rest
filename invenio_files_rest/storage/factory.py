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
        storage_backend_cls = self.get_storage_backend_for_file_instance(fileinstance)
        storage_backend_kwargs = self.get_storage_backend_kwargs(storage_backend_cls, fileinstance)

        if not fileinstance.uri:
            fileinstance.uri = self.get_filepath_for_file_instance(fileinstance)
        if not fileinstance.storage_backend:
            fileinstance.storage_backend = storage_backend_cls.backend_name

        return storage_backend_cls(fileinstance.uri, **storage_backend_kwargs)

    def get_storage_backend_for_file_instance(self, fileinstance: FileInstance) -> Type[FileStorage]:
        storage_backend = fileinstance.storage_backend or self.app.config['FILES_REST_DEFAULT_STORAGE_BACKEND']
        return self.app.config['FILES_REST_STORAGE_BACKENDS'][storage_backend]

    def get_filepath_for_file_instance(self, fileinstance: FileInstance) -> str:
        id = fileinstance.id.hex
        return os.path.join(id[0:2], id[2:4], id[4:6], id)

    def get_storage_backend_kwargs(self, storage_backend_cls: Type[FileStorage], fileinstance: FileInstance) -> Dict[str, Any]:
        return {}
