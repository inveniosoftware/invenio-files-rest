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

"""Serialization response factories.

Responsible for creating a HTTP response given the output of a serializer.
"""

from __future__ import absolute_import, print_function

from flask import current_app


def buckets_responsify(serializer, mimetype):
    """Create a Buckets-REST response serializer.

    :param serializer: Serializer instance.
    :param mimetype: MIME type of response.
    """
    def view(buckets, code=200, headers=None, links_factory=None):
        response = current_app.response_class(
            serializer.serialize_buckets(buckets,
                                         links_factory=links_factory),
            mimetype=mimetype)
        response.status_code = code
        # TODO: Set etag here.
        # response.set_etag("etag")
        if headers is not None:
            response.headers.extend(headers)
        return response
    return view


def bucket_post_responsify(serializer, mimetype):
    """Create a Bucket POST REST response serializer.

    :param serializer: Serializer instance.
    :param mimetype: MIME type of response.
    """
    def view(bucket, code=200, headers=None, links_factory=None):
        response = current_app.response_class(
            serializer.serialize_bucket(bucket,
                                        links_factory=links_factory),
            mimetype=mimetype)
        response.status_code = code
        # TODO: Set etag here.
        # response.set_etag("etag")
        if headers is not None:
            response.headers.extend(headers)
        return response
    return view


def objects_responsify(serializer, mimetype):
    """Create a Objects-REST response serializer.

    :param serializer: Serializer instance.
    :param mimetype: MIME type of response.
    """
    def view(bucket_id, object_list, code=200, headers=None,
             links_factory=None):
        response = current_app.response_class(
            serializer.serialize_objects(bucket_id, object_list,
                                         links_factory=links_factory),
            mimetype=mimetype)
        response.status_code = code
        # TODO: Set etag here.
        # response.set_etag("etag")
        if headers is not None:
            response.headers.extend(headers)
        return response
    return view
