# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Files download/upload REST API similar to S3 for Invenio."""

from __future__ import absolute_import, print_function

from werkzeug.utils import cached_property, import_string

from . import config
from .storage import pyfs_storage_factory
from .views import blueprint


class _FilesRESTState(object):
    """Invenio Files REST state."""

    def __init__(self, app):
        """Initialize state."""
        self.app = app

    @cached_property
    def storage_factory(self):
        """Load default storage factory."""
        imp = self.app.config.get("FILES_REST_STORAGE_FACTORY")
        return import_string(imp) if imp else pyfs_storage_factory

    @cached_property
    def permission_factory(self):
        """Load default permission factory."""
        imp = self.app.config.get("FILES_REST_PERMISSION_FACTORY")
        if imp:
            return import_string(imp)
        else:
            from invenio_files_rest.permissions import permission_factory
            return permission_factory


class InvenioFilesREST(object):
    """Invenio-Files-REST extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        app.register_blueprint(blueprint)
        app.extensions['invenio-files-rest'] = _FilesRESTState(app)

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith('FILES_REST_'):
                app.config.setdefault(k, getattr(config, k))
