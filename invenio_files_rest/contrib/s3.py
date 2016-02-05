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

from __future__ import absolute_import, print_function

from boto.s3.connection import S3Connection
from flask import current_app, redirect
from boto.s3.key import Key

from invenio_files_rest.errors import StorageError
from invenio_files_rest.storage import Storage


class AmazonS3(Storage):
    """Represents a S3 storage for a given object.

    :param object: the object linked to the file
    :param fileinstance:the file instance.
    :raise StorageError: if it is missing critical config variable
    """

    def __init__(self, object, fileinstance):
        super(AmazonS3, self).__init__(object, fileinstance)
        if "FILES_REST_AWS_KEY" not in current_app.config:
            raise StorageError("Missing AWS Key")
        if "FILES_REST_AWS_SECRET" not in current_app.config:
            raise StorageError("Missing AWS Secret")
        self.aws_connection = S3Connection(current_app.config.get(
            "FILES_REST_AWS_KEY"), current_app.config.get(
            "FILES_REST_AWS_SECRET"))

    def get_size(self):
        """Get the size of the file linked to the storage.

        :return: Integer representing the size.
        """
        bucket_name, key_name = self.obj.file.uri.replace("s3:", "").split(":")
        bucket = self.aws_connection.get_bucket(bucket_name)
        return bucket.lookup(key_name).size

    def open(self):
        """Return a file descriptor that can be used later.

        :return: file descriptor that can be used later.
        """
        loc = self.obj.bucket.location.uri
        bucket = self.aws_connection.get_bucket(loc)
        element = Key(bucket)
        key_name = self.obj.file.uri.replace("s3:", "").split(":")[1]
        element.key = key_name
        return S3File(element)

    def send_file(self, restricted=False):
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
        """Save the file on S3.

        :param incoming_stream: file descriptor.
        :param size: Not used in this function.
        :param chunk_size: Size of the chunk written to S3
        :return: The uri, the size and the md5.
        """
        loc = self.obj.bucket.location.uri
        bucket = self.aws_connection.get_bucket(loc)
        element = Key(bucket)
        element.key = "".join((incoming_stream.name, self.make_path()))

        bytes_written, checksum = self._save_stream(
            incoming_stream, S3File(element), chunk_size=chunk_size)

        element.close()

        s3_uri = "".join(("s3:", bucket.name, ":", element.key))

        return s3_uri, bytes_written, checksum


class S3File(object):
    """Class that represent a S3 file.

    :param element: boto.s3.key.Key object representing element to read
    """

    def __init__(self, element):
        self.e = element
        self.index = 0
        self.aws_stream_chunk = 8192

    def write(self, data):
        self.e.set_contents_from_string(data, replace=False)

    def read(self, chunk=None):
        if not chunk:
            return self.e.get_contents_as_string()
        else:
            res = self.e.get_contents_as_string(
                headers={'Range': 'bytes={0}-{1}'.format(self.index,
                                                         self.index +
                                                         chunk - 1)})
            self.index += chunk
            return res

    def seek(self, indice):
        self.index = indice

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.e.close()
