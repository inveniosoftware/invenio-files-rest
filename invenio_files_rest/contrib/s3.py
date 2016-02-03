# coding=utf-8

from __future__ import absolute_import, print_function

import hashlib
import tempfile
from os.path import join

from boto.s3.connection import S3Connection
from flask import current_app, redirect

from boto.s3.key import Key

from invenio_files_rest.errors import StorageError
from invenio_files_rest.storage import Storage


class AmazonS3(Storage):
    """
    Represents a S3 storage for a given object.

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
        """
        Get the size of the file linked to the storage.

        :return: Integer representing the size.
        """
        bucket_name, key_name = self.obj.file.uri.replace("s3:", "").split(":")
        bucket = self.aws_connection.get_bucket(bucket_name)
        return bucket.lookup(key_name).size

    def open(self):
        """
        Return a file descriptor that can be used later.

        :return: file descriptor that can be used later.
        """
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
        except Exception:
            temp.close()
            raise

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
        """
        Save the file on S3.

        :param incoming_stream: file descriptor.
        :param size: Not used in this function.
        :param chunk_size: Size of the chunck written to S3
        :return: The uri, the size and the md5.
        """
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
