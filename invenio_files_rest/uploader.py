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

"""Uploader factory for REST API.

The default factory allows you to use chunks with ``plupload`` javascript
plugin.

The API expects three arguments from the uploader:
    * ``total`` - the total number of chunks
    * ``current`` - the current chunk
    * ``upload_id`` the upload id
"""


def plupload(params):
    """Plupload factory.

    :param dict params: the request object arguments.

    .. note::

        Plupload sends chunk either as multipart/form-data (default) or as
        binary system, depending on the value of multipart option. Also three
        arguments sent with each chunk of data:

        * ``chunks`` - the total number of chunks in the file
        * ``chunk`` - the ordinal number of the current chink in the set
        * ``name`` - the name of the file

        See Plupload documentation for full details of chunk upload:
        http://www.plupload.com/docs/Chunking
    """
    return dict(
        total=int(params.get('chunks')),
        current=int(params.get('chunk')),
        upload_id=int(params.get('upload_id'))
    )


def ng_file_upload(params):
    """Ng-File-Fploade factory.

    :param dict params: the request object arguments.

    .. note::

        ng-file-upoad sends chunk either as multipart/form-data (default) or as
        binary system, depending on the value of multipart option. Also three
        arguments sent with each chunk of data:

        * ``_chunkSize`` - the average size of chunks
        * ``_currentChunkSize`` - the current chunk size
        * ``_chunkNumber`` - the number of chunks
        * ``_totalSize`` - the total file size of chunks

        Example headers:

            ------WebKitFormBoundaryH8TTM9gIEgNACDMt
            Content-Disposition: form-data; name="_chunkSize"

            3072
            ------WebKitFormBoundaryH8TTM9gIEgNACDMt
            Content-Disposition: form-data; name="_currentChunkSize"

            3072
            ------WebKitFormBoundaryH8TTM9gIEgNACDMt
            Content-Disposition: form-data; name="_chunkNumber"

            0
            ------WebKitFormBoundaryH8TTM9gIEgNACDMt
            Content-Disposition: form-data; name="_totalSize"

            2969101


        See Ng-File-Upload documentation for full details of chunk upload:
        https://github.com/danialfarid/ng-file-upload
    """
    return dict(
        total=int(params.get('_totalSize', 0)),
        current=int(params.get('_currentChunkSize', 0)),
        size=int(params.get('_chunkSize', 0)),
        upload_id=params.get('upload_id', 0),
    )
