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

from pkg_resources import DistributionNotFound, get_distribution
from werkzeug.utils import cached_property, import_string

from . import config
from .cli import files as files_cmd
from .storage import pyfs_storage_factory
from .views import blueprint


class _FilesRESTState(object):
    """Invenio Files REST state."""

    def __init__(self, app):
        """Initialize state."""
        self.app = app

    @cached_property
    def record_file_factory(self):
        """Load default storage factory."""
        imp = self.app.config.get("FILES_REST_RECORD_FILE_FACOTRY")
        if imp:
            import_string(imp)
        else:
            try:
                get_distribution('invenio-records-files')
                from invenio_records_files.utils import record_file_factory
                return record_file_factory
            except DistributionNotFound:
                return lambda pid, record, filename: None

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

    @cached_property
    def file_size_limiter(self):
        r"""Load the file size limiter.

        The file size limiter is a function used to get the maximum size a file
        can have. This function can use anything to decide this maximum size,
        example: bucket quota, user quota, custom limit.
        Its prototype is:
            py::function: limiter(bucket=None\
                ) -> (size limit: int, reason: str)

        The `reason` is the message displayed to the user when the limit is
        exceeded.
        The `size limit` and `reason` can be None if there is no limit.

        This function is used by the REST API and any other file creation
        input.
        """
        imp = self.app.config.get("FILES_REST_FILE_SIZE_LIMITER")
        if imp:
            return import_string(imp)
        else:
            from invenio_files_rest.helpers import file_size_limiter
            return file_size_limiter


class InvenioFilesREST(object):
    """Invenio-Files-REST extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        if hasattr(app, 'cli'):
            app.cli.add_command(files_cmd)
        app.register_blueprint(blueprint)
        app.extensions['invenio-files-rest'] = _FilesRESTState(app)

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith('FILES_REST_'):
                app.config.setdefault(k, getattr(config, k))
