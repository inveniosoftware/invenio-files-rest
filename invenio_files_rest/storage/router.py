# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2026 CESNET z.s.p.o.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""A router for directing file storage requests to the appropriate storage backend."""

from invenio_files_rest.proxies import current_files_rest


def storage_factory_router(*, fileinstance, **kwargs):
    """Find the appropriate storage factory for a given file instance.

    :param fileinstance: The file instance for which to find the storage factory.
    :return: A storage factory function that can create a storage instance
             for the given file instance
             If a specific storage factory for the file instance's storage class
             is not found, the default storage factory will be returned.
    """
    storage_class = fileinstance.storage_class
    storage_factory = current_files_rest.storage_factories.get(
        storage_class, current_files_rest.default_storage_factory
    )
    return storage_factory(fileinstance=fileinstance, **kwargs)
