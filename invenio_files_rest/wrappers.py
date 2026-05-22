# SPDX-FileCopyrightText: 2015-2019 CERN.
# SPDX-License-Identifier: MIT

"""Request wrapper."""

from flask.wrappers import Request as RequestBase

from .formparser import FormDataParser


class Request(RequestBase):
    """Custom request class needed for using custom form data parser."""

    form_data_parser_class = FormDataParser
