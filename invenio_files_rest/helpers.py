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

from flask import abort, current_app, request
from invenio_db import db
from werkzeug.datastructures import Headers
from werkzeug.local import LocalProxy
from werkzeug.wsgi import FileWrapper

from .models import MultipartObject

current_files_rest = LocalProxy(
    lambda: current_app.extensions['invenio-files-rest'])


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


def file_size_limiter(bucket):
    """Retrieve the internal quota from the provided bucket."""
    if bucket.quota_size:
        return (bucket.quota_size - bucket.size,
                'Bucket quota is {0} bytes. {1} bytes are currently '
                'used.'.format(bucket.quota_size, bucket.size))
    return (None, None)


def proccess_chunked_upload(bucket, key, content_length=None):
    """Proccess chunked upload.

    :param bucket: The bucket
    :param key: The filename
    """
    if request.args.get('uploads') is not None:
        size = int(request.headers.get('Uploader-File-Size', 0))
        # check content size limit
        size_limit, size_limit_reason = current_files_rest.file_size_limiter(
            bucket=bucket)
        if size_limit is not None and size > size_limit:
            abort(400, size_limit_reason)
        # requesting a new uplaod_id
        obj = MultipartObject.create(bucket, key, size)
        db.session.commit()
        return obj
    elif request.form.get('upload_id') is not None:
        params = current_app.extensions[
            'invenio-files-rest'].upload_factory(
            request.form)
        # Get the upload_id
        upload_id = request.form.get('upload_id')
        if upload_id:
            # Get the upload object
            obj = MultipartObject.get(upload_id)
            # If it has chunks proccess them otherwise throw error
            if params.get('current'):
                # Update the file
                uploaded_file = request.files['file']
                if not uploaded_file:
                    abort(400, 'file missing in request.')
                # If current chunk less than total chunks
                if params.get('current') <= params.get('total'):
                    obj.set_contents(
                        uploaded_file, size=content_length
                    )
                    # If the current chunk < avg size finalize
                    if params.get('current') < params.get('size'):
                        obj.finalize()
                    db.session.commit()
                    return obj
    abort(400, 'Not valid chunk parameters.')
