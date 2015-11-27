# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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

from flask import Blueprint
from invenio_rest import ContentNegotiatedMethodView

blueprint = Blueprint(
    'invenio_files_rest',
    __name__,
    url_prefix='/files'
)


class BucketListResource(ContentNegotiatedMethodView):
    """"Bucket list resource."""

    def get(self, **kwargs):
        """List buckets."""


class BucketItemResource(ContentNegotiatedMethodView):
    """"Bucket item resource."""

    def get(self, **kwargs):
        """List objects."""

    def post(self, **kwargs):
        """Create object."""

    def put(self, **kwargs):
        """Update object."""

    def delete(self, **kwargs):
        """Delete bucket/objects."""

    def head(self, **kwargs):
        """Check existence of bucket."""


class ObjectItemResource(ContentNegotiatedMethodView):
    """"Bucket item resource."""

    def get(self, **kwargs):
        """Get object."""

    def post(self, **kwargs):
        """?."""

    def put(self, **kwargs):
        """Update object."""

    def delete(self, **kwargs):
        """Delete object."""

    def head(self, **kwargs):
        """Check existence of object."""


blueprint.add_url_rule(
    '/', view_func=BucketListResource.as_view('bucket_list'))
blueprint.add_url_rule(
    '/<string:bucket_id>/',
    view_func=BucketItemResource.as_view('bucket_item'))
blueprint.add_url_rule(
    '/<string:bucket_id>/<path:object_key>',
    view_func=BucketItemResource.as_view('object_item'))
