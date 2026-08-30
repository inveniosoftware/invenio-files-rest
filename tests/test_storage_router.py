import pytest

from invenio_files_rest.models import FileInstance


class StandardStorage:
    """A dummy storage class for testing purposes."""

    def __init__(self, fileinstance, **kwargs):
        self.fileinstance = fileinstance
        self.kwargs = kwargs


class ArchiveStorage:
    """A dummy archive storage class for testing purposes."""

    def __init__(self, fileinstance, **kwargs):
        self.fileinstance = fileinstance
        self.kwargs = kwargs


def standard_storage_factory(fileinstance, **kwargs):
    return StandardStorage(fileinstance=fileinstance, **kwargs)


def archive_storage_factory(fileinstance, **kwargs):
    return ArchiveStorage(fileinstance=fileinstance, **kwargs)


def reset_cached_properties(obj, *property_names):
    """Reset cached properties on an object."""
    for property_name in property_names:
        try:
            del obj.__dict__[property_name]
        except KeyError:
            pass


@pytest.fixture
def app_with_router(app):
    # TODO: we need a new setup to test it properly. This should go to fixtures.
    previous_storage_factories = app.config["FILES_REST_STORAGE_FACTORIES"]
    previous_default_storage_factory = app.config["FILES_REST_STORAGE_FACTORY"]
    app.config["FILES_REST_STORAGE_FACTORIES"] = {
        "A": archive_storage_factory,
    }
    app.config["FILES_REST_STORAGE_FACTORY"] = standard_storage_factory
    reset_cached_properties(
        app.extensions["invenio-files-rest"],
        "storage_factory",
        "default_storage_factory",
        "storage_factories",
    )

    yield app

    # reset back
    app.config["FILES_REST_STORAGE_FACTORIES"] = previous_storage_factories
    app.config["FILES_REST_STORAGE_FACTORY"] = previous_default_storage_factory
    reset_cached_properties(
        app.extensions["invenio-files-rest"],
        "storage_factory",
        "default_storage_factory",
        "storage_factories",
    )


def test_storage_factory_router(app_with_router):
    fi = FileInstance(storage_class="S")
    storage = app_with_router.extensions["invenio-files-rest"].storage_factory(
        fileinstance=fi
    )
    assert isinstance(storage, StandardStorage)

    fi = FileInstance(storage_class="A")
    storage = app_with_router.extensions["invenio-files-rest"].storage_factory(
        fileinstance=fi
    )
    assert isinstance(storage, ArchiveStorage)
