# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

"""Marshmallow based JSON serializer for buckets."""

from __future__ import absolute_import, print_function

from flask import current_app, json, request

from .marshmallow import MarshmallowSerializer


class JSONSerializer(MarshmallowSerializer):
    """Marshmallow based JSON serializer for buckets.

    Note: This serializer is not suitable for serializing large number of
    buckets.
    """

    @staticmethod
    def _format_args():
        """Get JSON dump indentation and separates."""
        if current_app.config['JSONIFY_PRETTYPRINT_REGULAR'] and \
                not request.is_xhr:
            return dict(
                indent=2,
                separators=(', ', ': '),
            )
        else:
            return dict(
                indent=None,
                separators=(',', ':'),
            )

    def serialize_buckets(self, buckets, links_factory=None):
        """Serialize a bucket list result.

        :param buckets: List of Buckets.
        """
        def transform(x): return self.transform_bucket(x, links_factory)
        bucket_list = [transform(bucket) for bucket in buckets]
        return json.dumps(dict(
            Contents=bucket_list,
        ), **self._format_args())

    def serialize_bucket(self, bucket, links_factory=None):
        """Serialize a bucket result.

        :param bucket: A bucket.
        """
        return json.dumps(dict(self.transform_bucket(bucket, links_factory)),
                          **self._format_args())

    def serialize_objects(self, bucket_id, object_list,
                          links_factory=None):
        """Serialize a list of Objects result.

        # TODO: Is the bucket id a string?
        :param bucket_id: String with the Bucket ID.
        :param object_list: List of file ObjectVersion.
        """
        def transform(x): return self.transform_object(x, links_factory)
        obj_list = [transform(obj) for obj in object_list]
        return json.dumps(dict(
            # TODO: Name? as in S3 or use bucket_id?
            Name=bucket_id,
            Contents=obj_list,
        ), **self._format_args())
