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

from flask import Response


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
