
# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Storage module tests."""

from __future__ import absolute_import, print_function

import errno
import os
from os.path import dirname, exists, getsize, join

import pytest
from fs.errors import DirectoryNotEmptyError, ResourceNotFoundError
from mock import patch
from six import BytesIO

from invenio_files_rest.errors import FileSizeError, StorageError, \
    UnexpectedFileSizeError
from invenio_files_rest.limiters import FileSizeLimit
from invenio_files_rest.storage import FileStorage, PyFSFileStorage

def test_storage_interface():
    """Test storage interface."""
    s = FileStorage('some-path')
    pytest.raises(NotImplementedError, s.open)
    pytest.raises(NotImplementedError, s.initialize, 'file:///some/path')
    pytest.raises(NotImplementedError, s.delete)
    pytest.raises(NotImplementedError, s.save, None)
    pytest.raises(NotImplementedError, s.update, None)
    pytest.raises(NotImplementedError, s.checksum)


def test_pyfs_initialize(legacy_pyfs, pyfs_testpath):
    """Test init of files."""
    # Create file object.
    assert not exists(pyfs_testpath)
    uri, size, checksum = legacy_pyfs.initialize(size=100)

    assert size == 100
    assert checksum is None
    assert os.stat(pyfs_testpath).st_size == size

    uri, size, checksum = legacy_pyfs.initialize()
    assert size == 0
    assert size == os.stat(pyfs_testpath).st_size


def test_pyfs_delete(app, db, dummy_location):
    """Test init of files."""
    testurl = join(dummy_location.uri, 'subpath/data')
    s = PyFSFileStorage(testurl)
    s.initialize(size=100)
    assert exists(testurl)

    s.delete()
    assert not exists(testurl)

    s = PyFSFileStorage(join(dummy_location.uri, 'anotherpath/data'))
    pytest.raises(ResourceNotFoundError, s.delete)


def test_pyfs_delete_fail(legacy_pyfs, pyfs_testpath):
    """Test init of files."""
    legacy_pyfs.save(BytesIO(b'somedata'))
    os.rename(pyfs_testpath, join(dirname(pyfs_testpath), 'newname'))
    pytest.raises(DirectoryNotEmptyError, legacy_pyfs.delete)


def test_pyfs_save(legacy_pyfs, pyfs_testpath, get_md5):
    """Test basic save operation."""
    data = b'somedata'
    legacy_pyfs.save(BytesIO(data))

    assert exists(pyfs_testpath)
    assert open(pyfs_testpath, 'rb').read() == data


def test_pyfs_save_failcleanup(legacy_pyfs, pyfs_testpath, get_md5):
    """Test basic save operation."""
    data = b'somedata'

    def fail_callback(total, size):
        assert exists(pyfs_testpath)
        raise Exception('Something bad happened')

    pytest.raises(
        Exception,
        legacy_pyfs.save,
        BytesIO(data), chunk_size=4, progress_callback=fail_callback
    )
    assert not exists(pyfs_testpath)
    assert not exists(dirname(pyfs_testpath))


def test_pyfs_save_callback(legacy_pyfs):
    """Test progress callback."""
    data = b'somedata'

    counter = dict(size=0)

    def callback(total, size):
        counter['size'] = size

    uri, size, checksum = legacy_pyfs.save(
        BytesIO(data), progress_callback=callback)

    assert counter['size'] == len(data)


def test_pyfs_save_limits(legacy_pyfs):
    """Test progress callback."""
    data = b'somedata'
    uri, size, checksum = legacy_pyfs.save(BytesIO(data), size=len(data))
    assert size == len(data)

    uri, size, checksum = legacy_pyfs.save(BytesIO(data), size_limit=len(data))
    assert size == len(data)

    # Size doesn't match
    pytest.raises(
        UnexpectedFileSizeError, legacy_pyfs.save, BytesIO(data), size=len(data) - 1)
    pytest.raises(
        UnexpectedFileSizeError, legacy_pyfs.save, BytesIO(data), size=len(data) + 1)

    # Exceeds size limits
    pytest.raises(
        FileSizeError, legacy_pyfs.save, BytesIO(data),
        size_limit=FileSizeLimit(len(data) - 1, 'bla'))


def test_pyfs_update(legacy_pyfs, pyfs_testpath, get_md5):
    """Test update of file."""
    legacy_pyfs.initialize(size=100)
    legacy_pyfs.update(BytesIO(b'cd'), seek=2, size=2)
    legacy_pyfs.update(BytesIO(b'ab'), seek=0, size=2)

    with open(pyfs_testpath) as fp:
        content = fp.read()
    assert content[0:4] == 'abcd'
    assert len(content) == 100

    # Assert return parameters from update.
    size, checksum = legacy_pyfs.update(BytesIO(b'ef'), seek=4, size=2)
    assert size == 2
    assert get_md5(b'ef') == checksum


def test_pyfs_update_fail(legacy_pyfs, pyfs_testpath, get_md5):
    """Test update of file."""
    def fail_callback(total, size):
        assert exists(pyfs_testpath)
        raise Exception('Something bad happened')

    legacy_pyfs.initialize(size=100)
    legacy_pyfs.update(BytesIO(b'ab'), seek=0, size=2)
    pytest.raises(
        Exception,
        legacy_pyfs.update,
        BytesIO(b'cdef'),
        seek=2,
        size=4,
        chunk_size=2,
        progress_callback=fail_callback,
    )

    # Partial file can be written to disk!
    with open(pyfs_testpath) as fp:
        content = fp.read()
    assert content[0:4] == 'abcd'
    assert content[4:6] != 'ef'


def test_pyfs_checksum(get_md5):
    """Test fixity."""
    # Compute checksum of license file/
    with open('LICENSE', 'rb') as fp:
        data = fp.read()
        checksum = get_md5(data)

    counter = dict(size=0)

    def callback(total, size):
        counter['size'] = size

    # Now do it with storage interface
    s = PyFSFileStorage('LICENSE', size=getsize('LICENSE'))
    assert checksum == s.checksum(chunk_size=2, progress_callback=callback)
    assert counter['size'] == getsize('LICENSE')

    # No size provided, means progress callback isn't called
    counter['size'] = 0
    s = PyFSFileStorage('LICENSE')
    assert checksum == s.checksum(chunk_size=2, progress_callback=callback)
    assert counter['size'] == 0


def test_pyfs_checksum_fail():
    """Test fixity problems."""
    # Raise an error during checksum calculation
    def callback(total, size):
        raise OSError(errno.EPERM, "Permission")

    s = PyFSFileStorage('LICENSE', size=getsize('LICENSE'))

    pytest.raises(StorageError, s.checksum, progress_callback=callback)


def test_pyfs_send_file(app, legacy_pyfs):
    """Test send file."""
    data = b'sendthis'
    uri, size, checksum = legacy_pyfs.save(BytesIO(data))

    with app.test_request_context():
        res = legacy_pyfs.send_file(
            'myfilename.txt', mimetype='text/plain', checksum=checksum)
        assert res.status_code == 200
        h = res.headers
        assert h['Content-Type'] == 'text/plain; charset=utf-8'
        assert h['Content-Length'] == str(size)
        assert h['Content-MD5'] == checksum[4:]
        assert h['ETag'] == '"{0}"'.format(checksum)

        # Content-Type: application/octet-stream
        # ETag: "b234ee4d69f5fce4486a80fdaf4a4263"
        # Last-Modified: Sat, 23 Jan 2016 06:21:04 GMT
        # Cache-Control: max-age=43200, public
        # Expires: Sat, 23 Jan 2016 19:21:04 GMT
        # Date: Sat, 23 Jan 2016 07:21:04 GMT

        res = legacy_pyfs.send_file(
            'myfilename.txt', mimetype='text/plain', checksum='crc32:test')
        assert res.status_code == 200
        assert 'Content-MD5' not in dict(res.headers)

        # Test for absence of Content-Disposition header to make sure that
        # it's not present when as_attachment=False
        res = legacy_pyfs.send_file('myfilename.txt', mimetype='text/plain',
                             checksum=checksum, as_attachment=False)
        assert res.status_code == 200
        assert 'attachment' not in res.headers['Content-Disposition']


def test_pyfs_send_file_for_download(app, legacy_pyfs):
    """Test send file."""
    data = b'sendthis'
    uri, size, checksum = legacy_pyfs.save(BytesIO(data))

    with app.test_request_context():
        # Test for presence of Content-Disposition header to make sure that
        # it's present when as_attachment=True
        res = legacy_pyfs.send_file('myfilename.txt', mimetype='text/plain',
                             checksum=checksum, as_attachment=True)
        assert res.status_code == 200
        assert (res.headers['Content-Disposition'] ==
                'attachment; filename=myfilename.txt')


def test_pyfs_send_file_xss_prevention(app, legacy_pyfs):
    """Test send file."""
    data = b'<html><body><script>alert("xss");</script></body></html>'
    uri, size, checksum = legacy_pyfs.save(BytesIO(data))

    with app.test_request_context():
        res = legacy_pyfs.send_file(
            'myfilename.html', mimetype='text/html', checksum=checksum)
        assert res.status_code == 200
        h = res.headers
        assert h['Content-Type'] == 'text/plain; charset=utf-8'
        assert h['Content-Length'] == str(size)
        assert h['Content-MD5'] == checksum[4:]
        assert h['ETag'] == '"{0}"'.format(checksum)
        # XSS prevention
        assert h['Content-Security-Policy'] == 'default-src \'none\';'
        assert h['X-Content-Type-Options'] == 'nosniff'
        assert h['X-Download-Options'] == 'noopen'
        assert h['X-Permitted-Cross-Domain-Policies'] == 'none'
        assert h['X-Frame-Options'] == 'deny'
        assert h['X-XSS-Protection'] == '1; mode=block'
        assert h['Content-Disposition'] == 'inline'

        # Image
        h = legacy_pyfs.send_file('image.png', mimetype='image/png').headers
        assert h['Content-Type'] == 'image/png'
        assert h['Content-Disposition'] == 'inline'

        # README text file
        h = legacy_pyfs.send_file('README').headers
        assert h['Content-Type'] == 'text/plain; charset=utf-8'
        assert h['Content-Disposition'] == 'inline'

        # Zip
        h = legacy_pyfs.send_file('archive.zip').headers
        assert h['Content-Type'] == 'application/octet-stream'
        assert h['Content-Disposition'] == 'attachment; filename=archive.zip'

        # PDF
        h = legacy_pyfs.send_file('doc.pdf').headers
        assert h['Content-Type'] == 'application/octet-stream'
        assert h['Content-Disposition'] == 'attachment; filename=doc.pdf'


def test_pyfs_send_file_fail(app, legacy_pyfs):
    """Test send file."""
    legacy_pyfs.save(BytesIO(b'content'))

    with patch('invenio_files_rest.storage.legacy.send_stream') as send_stream:
        send_stream.side_effect = OSError(errno.EPERM, "Permission problem")
        with app.test_request_context():
            pytest.raises(StorageError, legacy_pyfs.send_file, 'test.txt')


def test_pyfs_copy(legacy_pyfs, dummy_location):
    """Test send file."""
    s = PyFSFileStorage(join(dummy_location.uri, 'anotherpath/data'))
    s.save(BytesIO(b'otherdata'))

    legacy_pyfs.copy(s)
    fp = legacy_pyfs.open()
    assert fp.read() == b'otherdata'


def test_non_unicode_filename(app, legacy_pyfs):
    """Test sending the non-unicode filename in the header."""
    data = b'HelloWorld'
    uri, size, checksum = legacy_pyfs.save(BytesIO(data))

    with app.test_request_context():
        res = legacy_pyfs.send_file(
            u'żółć.dat', mimetype='application/octet-stream',
            checksum=checksum)
        assert res.status_code == 200
        assert set(res.headers['Content-Disposition'].split('; ')) == \
            set(["attachment", "filename=zoc.dat",
                 "filename*=UTF-8''%C5%BC%C3%B3%C5%82%C4%87.dat"])

    with app.test_request_context():
        res = legacy_pyfs.send_file(
            'żółć.txt', mimetype='text/plain', checksum=checksum)
        assert res.status_code == 200
        assert res.headers['Content-Disposition'] == 'inline'
