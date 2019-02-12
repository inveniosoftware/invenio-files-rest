# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2019 CERN.
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

"""Test serializer."""

from __future__ import absolute_import, print_function

from marshmallow import Schema, fields

from invenio_files_rest.serializer import json_serializer, serializer_mapping


def test_serialize_pretty(app):
    """Test pretty JSON."""
    class TestSchema(Schema):
        title = fields.Str(attribute='title')

    data = {'title': 'test'}
    context = {'bucket': '11111111-1111-1111-1111-111111111111',
               'class': 'TestSchema', 'many': False}

    serializer_mapping['TestSchema'] = TestSchema

    with app.test_request_context():
        assert json_serializer(data=data, context=context).data == \
            b'{"title":"test"}'

    with app.test_request_context('/?prettyprint=1'):
        assert json_serializer(data=data, context=context).data == \
            b'{\n  "title": "test"\n}'
