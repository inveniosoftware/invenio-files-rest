# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Admin model views for PersistentIdentifier."""

from __future__ import absolute_import, print_function

from flask import current_app
from flask_admin.contrib.sqla import ModelView
from flask_wtf import Form
from wtforms.validators import ValidationError

from .models import Bucket, FileInstance, Location, ObjectVersion, slug_pattern


def _(x):
    """Identity function for string extraction."""
    return x


def require_slug(form, field):
    """Validate location name."""
    if not slug_pattern.match(field.data):
        raise ValidationError(_("Invalid location name."))


class LazyChoices(object):
    """Lazy form choices."""

    def __init__(self, func):
        """Initialize lazy choices."""
        self._func = func

    def __iter__(self):
        """Iterate over lazy choices."""
        return iter(self._func())


class LocationModelView(ModelView):
    """ModelView for the locations."""

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    column_editable_list = ('default', )
    column_details_list = ('name', 'uri', 'default', 'created', 'updated', )
    column_list = ('name', 'uri', 'default', 'created', 'updated', )
    column_labels = dict(
        id=_('ID'),
        uri=_('URI'),
    )
    column_filters = ('default', 'created', 'updated', )
    column_searchable_list = ('uri', 'name')
    column_default_sort = 'name'
    form_base_class = Form
    form_columns = ('name', 'uri', 'default', )
    form_args = dict(
        name=dict(validators=[require_slug])
    )
    page_size = 25


class BucketModelView(ModelView):
    """ModelView for the buckets."""

    can_create = True
    can_delete = False
    can_edit = True
    can_view_details = True
    column_details_list = (
        'id', 'location', 'default_storage_class', 'deleted', 'locked',
        'created', 'updated', )
    column_list = (
        'id', 'location', 'default_storage_class', 'deleted', 'locked', 'size',
        'created', 'updated',
    )
    column_labels = dict(
        id=_('UUID'),
        default_location=_('Location'),
        pid_provider=_('Storage Class'),
    )
    column_filters = (
        'deleted', 'locked', 'default_location', 'default_storage_class',
        'created', 'updated')
    column_default_sort = ('updated', True)
    form_base_class = Form
    form_columns = ('location', 'default_storage_class', 'locked', 'deleted', )
    form_choices = dict(
        default_storage_class=LazyChoices(lambda: current_app.config[
            'FILES_REST_STORAGE_CLASS_LIST'].items()))
    page_size = 25


class ObjectModelView(ModelView):
    """ModelView for the objects."""

    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    column_labels = {
        'version_id': _('Version'),
        'file.uri': _('URI'),
        'file.size': _('Size'),
        'is_deleted': _('Deleted'),
    }
    column_list = (
        'bucket', 'key', 'version_id', 'file.uri', 'is_head', 'is_deleted',
        'file.size', 'created', 'updated', )
    column_searchable_list = ('key', )
    column_details_list = (
        'bucket', 'key', 'version_id', 'file_id', 'file.uri', 'file.checksum',
        'file.size', 'file.storage_class', 'is_head', 'is_deleted', 'created',
        'updated', )
    column_filters = (
        'bucket', 'key', 'is_head', 'file.storage_class', 'created', 'updated')
    column_default_sort = ('updated', True)
    page_size = 25


class FileInstanceModelView(ModelView):
    """ModelView for the objects."""

    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    column_labels = dict(
        uri=_('URI'),
    )
    column_list = (
        'id', 'uri', 'storage_class', 'size', 'checksum', 'read_only',
        'created', 'updated', )
    column_searchable_list = ('uri', 'size', 'checksum', )
    column_details_list = (
        'id', 'uri', 'storage_class', 'size', 'checksum', 'read_only',
        'created', 'updated', )
    column_filters = (
        'uri', 'size', 'checksum', 'read_only', 'created', 'updated')
    column_default_sort = ('updated', True)
    page_size = 25


location_adminview = dict(
    modelview=LocationModelView,
    model=Location,
    category=_('Files'))
bucket_adminview = dict(
    modelview=BucketModelView,
    model=Bucket,
    category=_('Files'))
object_adminview = dict(
    modelview=ObjectModelView,
    model=ObjectVersion,
    category=_('Files'))
fileinstance_adminview = dict(
    modelview=FileInstanceModelView,
    model=FileInstance,
    category=_('Files'))
