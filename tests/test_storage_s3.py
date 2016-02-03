# coding=utf-8

"""Storage s3 module tests."""

import hashlib
from os.path import getsize

import boto
from moto import mock_s3
from invenio_files_rest.errors import StorageError

from invenio_files_rest.models import Bucket, FileInstance, Object, Location
from invenio_files_rest.contrib.s3 import AmazonS3


@mock_s3
def test_s3filesystemstorage(app, db, dummy_location):
    """test aws storage"""

    conn = boto.connect_s3()
    conn.create_bucket('bucket_test')
    with db.session.begin_nested():
        l = Location()

        # s3 bucket name
        l.uri = "bucket_test"
        l.name = "buckettest1"
        db.session.add(l)
        b = Bucket.create(location_name=l.name)
        obj = Object.create(b, "LICENSE")
        obj.file = FileInstance()
        db.session.add(obj.file)

    # Test missing config
    try:
        AmazonS3(obj, obj.file)
    except StorageError as e:
        assert e.message == "Missing AWS Key"

    app.config["FILES_REST_AWS_KEY"] = "test_key"

    try:
        AmazonS3(obj, obj.file)
    except StorageError as e:
        assert e.message == "Missing AWS Secret"

    app.config["FILES_REST_AWS_SECRET"] = "test_secret"

    storage = AmazonS3(obj, obj.file)
    try:
        storage.open()
        assert False
    except Exception as e:
        assert True

    with open('LICENSE', 'rb') as fp:
        loc, size, checksum = storage.save(fp)

    assert size == len(open('LICENSE', 'rb').read())
    assert size == storage.get_size()
    assert obj.file.uri == loc
    with open('LICENSE', 'rb') as fp:
        m = hashlib.md5()
        m.update(fp.read())
        assert m.hexdigest() == checksum

    with storage.open() as fp:
        m = hashlib.md5()
        fp_content = fp.read()
        m.update(fp_content)
        assert len(fp_content) == size
        assert m.hexdigest() == checksum

    assert size == getsize('LICENSE')
    assert size == getsize('LICENSE')
    res = storage.send_file("")
    assert res.status_code == 302
    assert res.data.find("".join((l.uri, ".s3.amazonaws.com"))) > -1
