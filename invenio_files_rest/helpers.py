# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
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

"""File serving helpers for Files REST API."""

from __future__ import absolute_import, print_function

import hashlib
import mimetypes
import os
from time import time

from flask import current_app, request
from werkzeug.datastructures import Headers
from werkzeug.wsgi import FileWrapper


def send_stream(stream, filename, size, mtime, mimetype=None, restricted=False,
                as_attachment=False, etag=None, content_md5=None,
                chunk_size=8192, conditional=True):
    """Send the contents of a file to the client."""
    # Guess mimetype from filename if not provided.
    if mimetype is None and filename:
        mimetype = mimetypes.guess_type(filename)[0]
    if mimetype is None:
        mimetype = 'application/octet-stream'

    # Construct headers
    headers = Headers()
    if as_attachment:
        headers.add('Content-Disposition', 'attachment', filename=filename)
    else:
        headers.add('Content-Disposition', 'inline')
    headers['Content-Length'] = size
    headers['Content-MD5'] = content_md5

    # Construct response object.
    rv = current_app.response_class(
        FileWrapper(stream, buffer_size=chunk_size),
        mimetype=mimetype,
        headers=headers,
        direct_passthrough=True,
    )

    # Set etag if defined
    if etag:
        rv.set_etag(etag)

    # Set last modified time
    if mtime is not None:
        rv.last_modified = int(mtime)

    # Set cache-control
    if not restricted:
        rv.cache_control.public = True
        cache_timeout = current_app.get_send_file_max_age(filename)
        if cache_timeout is not None:
            rv.cache_control.max_age = cache_timeout
            rv.expires = int(time() + cache_timeout)

    if conditional:
        rv = rv.make_conditional(request)

    return rv


def file_size_limiter(bucket):
    """Retrieve the internal quota from the provided bucket."""
    if bucket.quota_size:
        return (bucket.quota_size - bucket.size,
                'Bucket quota is {0} bytes. {1} bytes are currently '
                'used.'.format(bucket.quota_size, bucket.size))
    return (None, None)


def compute_md5_checksum(src, chunk_size=None, progress_callback=None):
    """Helper method to compute checksum from a stream.

    :param src: File-like object.
    :param chunk_size: Read at most size bytes from the file.
    :param progress_callback: Function accepting one argument with number
        of bytes read.
    """
    bytes_read = 0
    m = hashlib.md5()
    while 1:
        chunk = src.read(chunk_size)
        if not chunk:
            if progress_callback:
                progress_callback(bytes_read)
            break
        m.update(chunk)
        bytes_read += len(chunk)
        if progress_callback:
            progress_callback(bytes_read)
    return "md5:{0}".format(m.hexdigest())


def populate_from_path(bucket, source, checksum=True, key_prefix=''):
    """Populate a ``bucket`` from all files in path."""
    from .models import FileInstance, ObjectVersion

    def create_file(key, path):
        """Create new ``ObjectVersion`` from path or existing ``FileInstance``.

        It checks MD5 checksum and size of existing ``FileInstance``s.
        """
        key = key_prefix + key

        if checksum:
            file_checksum = compute_md5_checksum(open(path, 'rb'),
                                                 chunk_size=80960)
            file_instance = FileInstance.query.filter_by(
                checksum=file_checksum, size=os.path.getsize(path)
            ).first()
            if file_instance:
                return ObjectVersion.create(
                    bucket, key, _file_id=file_instance.id
                )
        return ObjectVersion.create(bucket, key, stream=open(path, 'rb'))

    if os.path.isfile(source):
        yield create_file(os.path.basename(source), source)
    else:
        for root, dirs, files in os.walk(source, topdown=False):
            for name in files:
                filename = os.path.join(root, name)
                assert filename.startswith(source)
                parts = [p for p in filename[len(source):].split(os.sep) if p]
                yield create_file('/'.join(parts), os.path.join(root, name))
