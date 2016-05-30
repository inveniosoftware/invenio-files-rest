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

"""REST API serializers."""

import json
from functools import wraps

from flask import Response, url_for


def json_serializer(data=None, code=200, headers=None):
    """Build a json flask response using the given data.

    :returns: A flask response with json data.
    :returns type: :py:class:`flask.Response`
    """
    if data is not None:
        response = Response(
            json.dumps(data['json']),
            mimetype='application/json'
        )
    else:
        response = Response(mimetype='application/json')

    response.status_code = code
    if headers is not None:
        response.headers.extend(headers)

    # ETag needed?
    # response.set_etag(str(record.model.version_id))
    return response


def empty_if_none(f):
    """Wrap a serialize to handle when data is None."""
    @wraps(f)
    def decorator(data=None, code=200, headers=None):
        data = data if not data else f(data, code, headers)
        return json_serializer({'json': data}, code, headers)
    return decorator


@empty_if_none
def bucket_collection_serializer(data=None, code=200, headers=None):
    """Serialize BucketCollectionResource responses."""
    def serialize(bucket):
        return {
            'size': bucket.size,
            'url': url_for('invenio_files_rest.bucket_api',
                           bucket_id=bucket.id, _external=True),
            'uuid': str(bucket.id),
        }

    return [serialize(bucket) for bucket in data] \
        if hasattr(data, '__iter__') \
        else serialize(data)


@empty_if_none
def bucket_serializer(data=None, code=200, headers=None):
    """Serialize BucketResource responses."""
    def serialize(obj):
        return {
            'checksum': obj.file.checksum,
            'size': obj.file.size,
            'url': url_for('invenio_files_rest.object_api',
                           bucket_id=obj.bucket.id,
                           key=obj.key,
                           _external=True),
            'uuid': str(obj.file.id),
        }

    return [serialize(obj) for obj in data]
