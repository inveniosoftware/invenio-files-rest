# SPDX-FileCopyrightText: 2019 CERN.
# SPDX-License-Identifier: MIT

"""Test serializer."""

from marshmallow import fields

from invenio_files_rest.serializer import (
    BaseSchema,
    json_serializer,
    serializer_mapping,
)


def test_serialize_pretty(app):
    """Test pretty JSON."""

    class TestSchema(BaseSchema):
        title = fields.Str(attribute="title")

    data = {"title": "test"}
    context = {
        "bucket": "11111111-1111-1111-1111-111111111111",
        "class": "TestSchema",
        "many": False,
    }

    serializer_mapping["TestSchema"] = TestSchema

    # TODO This test should be checked if it shouldn't have
    #  BaseSchema instead of Schema
    with app.test_request_context():
        assert json_serializer(data=data, context=context).data == b'{"title":"test"}'

    with app.test_request_context("/?prettyprint=1"):
        assert (
            json_serializer(data=data, context=context).data
            == b'{\n  "title": "test"\n}'
        )
