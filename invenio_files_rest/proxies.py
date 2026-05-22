# SPDX-FileCopyrightText: 2015-2019 CERN.
# SPDX-License-Identifier: MIT

"""Proxy definitions."""

from flask import current_app
from werkzeug.local import LocalProxy

current_files_rest = LocalProxy(lambda: current_app.extensions["invenio-files-rest"])
"""Helper proxy to access files rest state object."""

current_permission_factory = LocalProxy(lambda: current_files_rest.permission_factory)
"""Helper proxy to access to the configured permission factory."""
