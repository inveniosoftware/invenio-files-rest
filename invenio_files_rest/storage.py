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

"""Storage related module."""

from __future__ import absolute_import, print_function

import hashlib
import time
import tempfile
from os.path import join

from fs.opener import opener
from boto.s3.connection import S3Connection
from flask import current_app, redirect

from boto.s3.key import Key

from .errors import StorageError
from .helpers import send_stream


def storage_factory(obj=None, fileinstance=None):
    """Factory function for creating a storage instance."""
    return PyFilesystemStorage(obj, fileinstance)


class Storage(object):
    """Base class for storage backends.

    :param object: A dict with data used to initialize the backend.
    """

    def __init__(self, object, fileinstance):
        """Storage init."""
        self.obj = object
        self.file = fileinstance

    def make_path(self):
        """Make path to file in a given storage location."""
        return join(
            str(self.obj.bucket_id),
            str(self.obj.version_id),
        )

    def save(self, incoming_stream, size=None, chunk_size=None):
        """Create a new file in the storage.

        :param fileobj: A file-like object containing the file data as
                        bytes or a bytestring.
        :param filename: secure filename.
        """
        raise NotImplementedError

    def send_file(self, filename):
        """Send the file to the client.

        This returns a flask response that will eventually result in
        the user being offered to download the file (or view it in the
        browser).  Depending on the storage backend it may actually
        send a redirect to an external URL where the file is available.

        :param filename: The file name to use when sending the file to
                         the client.
        """
        raise NotImplementedError

    def _save_stream(self, src, dst, chunk_size=None):
        """Save stream from src to dest and compute checksum."""
        chunk_size = chunk_size or 1024 * 64

        m = hashlib.md5()
        bytes_written = 0

        while 1:
            chunk = src.read(chunk_size)
            if not chunk:
                break
            dst.write(chunk)
            bytes_written += len(chunk)
            m.update(chunk)

        return bytes_written, m.hexdigest()


class PyFilesystemStorage(Storage):
    """File system storage using PyFilesystem."""

    def save(self, incoming_stream, size=None, chunk_size=None):
        """Save file in the file system."""
        uri = self.obj.bucket.location.uri
        path = self.make_path()

        with opener.opendir(uri) as fs:
            dest_file = fs.makeopendir(path, recursive=True).open('data', 'wb')
            bytes_written, checksum = self._save_stream(
                incoming_stream, dest_file, chunk_size=chunk_size)
            dest_file.close()

        return join(uri, path, 'data'), bytes_written, checksum

    def send_file(self, restricted=False):
        """Send file to the client."""
        try:
            fs, path = opener.parse(self.file.uri)
            fp = fs.open(path, 'rb')
            return send_stream(
                fp, path, self.file.size,
                time.mktime(self.file.updated.timetuple()),
                restricted=restricted, etag=self.file.checksum,
                content_md5=self.file.checksum)
        except Exception as e:
            raise StorageError('Could not send file: {}'.format(e))


class AmazonS3(Storage):
    def __init__(self, object, fileinstance):
        super(AmazonS3, self).__init__(object, fileinstance)
        if "AWS_KEY" in current_app.config:
            raise StorageError("Missing AWS Key")
        if "AWS_SECRET" in current_app.config:
            raise StorageError("Missing AWS Secret")
        self.aws_connection = S3Connection(current_app.config.get("AWS_KEY", "AWS_KEY"),
                                           current_app.config.get("AWS_SECRET", "AWS_SECRET"))

    def get_size(self):
        bucket_name, key_name = self.obj.file.uri.replace("s3:", "").split(":")
        bucket = self.aws_connection.get_bucket(bucket_name)
        return bucket.lookup(key_name).size

    def open(self):

        temp = tempfile.NamedTemporaryFile()
        try:
            loc = self.obj.bucket.location.uri
            bucket = self.aws_connection.get_bucket(loc)
            element = Key(bucket)
            key_name = self.obj.file.uri.replace("s3:", "").split(":")[1]
            element.key = key_name
            element.get_contents_to_file(temp)
            temp.seek(0)
            return temp
        except:
            temp.close()
            return None

    def send_file(self, filename):
        """Send the file to the client.

        This returns a flask response that will eventually result in
        the user being offered to download the file (or view it in the
        browser).  Depending on the storage backend it may actually
        send a redirect to an external URL where the file is available.

        :param filename: The file name to use when sending the file to
                         the client.
        """
        loc = self.obj.bucket.location.uri
        bucket = self.aws_connection.get_bucket(loc)
        element = Key(bucket)
        element.key = self.obj.file.uri
        return redirect(element.generate_url(expires_in=300))

    def save(self, incoming_stream, size=None, chunk_size=None):

        # Retrieve the bucket name
        loc = self.obj.bucket.location.uri
        bucket = self.aws_connection.get_bucket(loc)
        element = Key(bucket)
        element.key = "".join((incoming_stream.name, self.make_path()))

        chunk_size = chunk_size or 1024 * 64
        m = hashlib.md5()
        bytes_written = 0

        while 1:
            chunk = incoming_stream.read(chunk_size)
            if not chunk:
                break
            element.set_contents_from_string(chunk, replace=False)
            bytes_written += len(chunk)
            m.update(chunk)
        element.close()
        s3_uri = "".join(("s3:", bucket.name, ":", element.key))
        self.obj.file.uri = s3_uri
        return s3_uri, bytes_written, m.hexdigest()

    def make_path_vid(self, vid):
        """Make path to file in a given storage location."""
        return join(
            str(self.obj.bucket_id),
            str(vid),
        )
