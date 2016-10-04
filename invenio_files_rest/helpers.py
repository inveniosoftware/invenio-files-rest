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

"""File serving helpers for Files REST API."""

from __future__ import absolute_import, print_function

import hashlib
import mimetypes
import os
from time import time

from flask import current_app, request
from werkzeug.datastructures import Headers
from werkzeug.wsgi import FileWrapper


def send_stream(stream, filename, size, mtime, mimetype=None, restricted=True,
                as_attachment=False, etag=None, content_md5=None,
                chunk_size=8192, conditional=True):
    """Send the contents of a file to the client.

    :param stream: The file stream to send.
    :param filename: The file name.
    :param size: The file size.
    :param mtime: A Unix timestamp that represents last modified time (UTC).
    :param mimetype: The file mimetype. If ``None``, the module will try to
        guess. (Default: ``None``)
    :param restricted: If the file is not restricted, the module will set the
        cache-control. (Default: ``True``)
    :param as_attachment: If the file is an attachment. (Default: ``False``)
    :param etag: If defined, it will be set as HTTP E-Tag.
    :param content_md5: If defined, a HTTP Content-MD5 header will be set.
    :param chunk_size: The chunk size. (Default: ``8192``)
    :param conditional: Make the response conditional to the request.
        (Default: ``True``)
    :returns: A Flask response instance.
    """
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
    if content_md5:
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


def make_path(base_uri, path, filename, path_dimensions, split_length):
    """Generate a path as base location for file instance.

    :param base_uri: The base URI.
    :param path: The relative path.
    :param path_dimensions: Number of chunks the path should be split into.
    :param split_length: The length of any chunk.
    :returns: A string representing the full path.
    """
    assert len(path) > path_dimensions * split_length

    uri_parts = []
    for i in range(path_dimensions):
        uri_parts.append(path[0:split_length])
        path = path[split_length:]
    uri_parts.append(path)
    uri_parts.append(filename)

    return os.path.join(base_uri, *uri_parts)


def compute_md5_checksum(stream, **kwargs):
    """Helper method to compute MD5 checksum from a stream.

    :param stream: The input stream.
    :returns: The MD5 checksum.
    """
    return compute_checksum(stream, 'md5', hashlib.md5(), **kwargs)


def compute_checksum(stream, algo, message_digest, chunk_size=None,
                     progress_callback=None):
    """Helper method to compute checksum from a stream.

    :param stream: File-like object.
    :param algo: Identifier for checksum algorithm.
    :param messsage_digest: A message digest instance.
    :param chunk_size: Read at most size bytes from the file.
        (Default: ``None``)
    :param progress_callback: Function accepting one argument with number
        of bytes read. (Default: ``None``)
    :returns: The checksum.
    """
    bytes_read = 0
    while 1:
        chunk = stream.read(chunk_size)
        if not chunk:
            if progress_callback:
                progress_callback(bytes_read)
            break
        message_digest.update(chunk)
        bytes_read += len(chunk)
        if progress_callback:
            progress_callback(bytes_read)
    return "{0}:{1}".format(algo, message_digest.hexdigest())


def populate_from_path(bucket, source, checksum=True, key_prefix=''):
    """Populate a ``bucket`` from all files in path.

    :param bucket: The bucket (instance or id) to create the object in.
    :param source: The file or directory path.
    :param checksum: If ``True`` then a MD5 checksum will be computed for each
        file. (Default: ``True``)
    :param key_prefix: The key prefix for the bucket.
    :returns: A iterator for all
        :class:`invenio_files_rest.models.ObjectVersion` instances.
    """
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
