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
    s = FileStorage()
    pytest.raises(NotImplementedError, s.open)
    pytest.raises(NotImplementedError, s.initialize)
    pytest.raises(NotImplementedError, s.delete)
    pytest.raises(NotImplementedError, s.save, None)
    pytest.raises(NotImplementedError, s.update, None)
    pytest.raises(NotImplementedError, s.checksum)


def test_pyfs_initialize(pyfs, pyfs_testpath):
    """Test init of files."""
    # Create file object.
    assert not exists(pyfs_testpath)
    uri, size, checksum = pyfs.initialize(size=100)

    assert size == 100
    assert checksum is None
    assert os.stat(pyfs_testpath).st_size == size

    uri, size, checksum = pyfs.initialize()
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


def test_pyfs_delete_fail(pyfs, pyfs_testpath):
    """Test init of files."""
    pyfs.save(BytesIO(b'somedata'))
    os.rename(pyfs_testpath, join(dirname(pyfs_testpath), 'newname'))
    pytest.raises(DirectoryNotEmptyError, pyfs.delete)


def test_pyfs_save(pyfs, pyfs_testpath, get_md5):
    """Test basic save operation."""
    data = b'somedata'
    uri, size, checksum = pyfs.save(BytesIO(data))

    assert uri == pyfs_testpath
    assert size == len(data)
    assert checksum == get_md5(data)
    assert exists(pyfs_testpath)
    assert open(pyfs_testpath, 'rb').read() == data


def test_pyfs_save_failcleanup(pyfs, pyfs_testpath, get_md5):
    """Test basic save operation."""
    data = b'somedata'

    def fail_callback(total, size):
        assert exists(pyfs_testpath)
        raise Exception('Something bad happened')

    pytest.raises(
        Exception,
        pyfs.save,
        BytesIO(data), chunk_size=4, progress_callback=fail_callback
    )
    assert not exists(pyfs_testpath)
    assert not exists(dirname(pyfs_testpath))


def test_pyfs_save_callback(pyfs):
    """Test progress callback."""
    data = b'somedata'

    counter = dict(size=0)

    def callback(total, size):
        counter['size'] = size

    uri, size, checksum = pyfs.save(
        BytesIO(data), progress_callback=callback)

    assert counter['size'] == len(data)


def test_pyfs_save_limits(pyfs):
    """Test progress callback."""
    data = b'somedata'
    uri, size, checksum = pyfs.save(BytesIO(data), size=len(data))
    assert size == len(data)

    uri, size, checksum = pyfs.save(BytesIO(data), size_limit=len(data))
    assert size == len(data)

    # Size doesn't match
    pytest.raises(
        UnexpectedFileSizeError, pyfs.save, BytesIO(data), size=len(data) - 1)
    pytest.raises(
        UnexpectedFileSizeError, pyfs.save, BytesIO(data), size=len(data) + 1)

    # Exceeds size limits
    pytest.raises(
        FileSizeError, pyfs.save, BytesIO(data),
        size_limit=FileSizeLimit(len(data) - 1, 'bla'))


def test_pyfs_update(pyfs, pyfs_testpath, get_md5):
    """Test update of file."""
    pyfs.initialize(size=100)
    pyfs.update(BytesIO(b'cd'), seek=2, size=2)
    pyfs.update(BytesIO(b'ab'), seek=0, size=2)

    with open(pyfs_testpath) as fp:
        content = fp.read()
    assert content[0:4] == 'abcd'
    assert len(content) == 100

    # Assert return parameters from update.
    size, checksum = pyfs.update(BytesIO(b'ef'), seek=4, size=2)
    assert size == 2
    assert get_md5(b'ef') == checksum


def test_pyfs_update_fail(pyfs, pyfs_testpath, get_md5):
    """Test update of file."""
    def fail_callback(total, size):
        assert exists(pyfs_testpath)
        raise Exception('Something bad happened')

    pyfs.initialize(size=100)
    pyfs.update(BytesIO(b'ab'), seek=0, size=2)
    pytest.raises(
        Exception,
        pyfs.update,
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


def test_pyfs_send_file(app, pyfs):
    """Test send file."""
    data = b'sendthis'
    uri, size, checksum = pyfs.save(BytesIO(data))

    with app.test_request_context():
        res = pyfs.send_file(
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

        res = pyfs.send_file(
            'myfilename.txt', mimetype='text/plain', checksum='crc32:test')
        assert 'Content-MD5' not in dict(res.headers)


def test_pyfs_send_file_xss_prevention(app, pyfs):
    """Test send file."""
    data = b'<html><body><script>alert("xss");</script></body></html>'
    uri, size, checksum = pyfs.save(BytesIO(data))

    with app.test_request_context():
        res = pyfs.send_file(
            'myfilename.html', mimetype='text/plain', checksum=checksum)
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

        # Content-Type: application/octet-stream
        # ETag: "b234ee4d69f5fce4486a80fdaf4a4263"
        # Last-Modified: Sat, 23 Jan 2016 06:21:04 GMT
        # Cache-Control: max-age=43200, public
        # Expires: Sat, 23 Jan 2016 19:21:04 GMT
        # Date: Sat, 23 Jan 2016 07:21:04 GMT
        # Content-Security-Policy: default-src 'none';
        # X-Content-Type-Options: nosniff
        # X-Download-Options: noopen
        # X-Permitted-Cross-Domain-Policies: none
        # X-Frame-Options: deny
        # X-XSS-Protection: 1; mode=block


def test_pyfs_send_file_fail(app, pyfs):
    """Test send file."""
    pyfs.save(BytesIO(b'content'))

    with patch('invenio_files_rest.storage.base.send_stream') as send_stream:
        send_stream.side_effect = OSError(errno.EPERM, "Permission problem")
        with app.test_request_context():
            pytest.raises(StorageError, pyfs.send_file, 'test.txt')


def test_pyfs_copy(pyfs, dummy_location):
    """Test send file."""
    s = PyFSFileStorage(join(dummy_location.uri, 'anotherpath/data'))
    s.save(BytesIO(b'otherdata'))

    pyfs.copy(s)
    fp = pyfs.open()
    assert fp.read() == b'otherdata'


def test_non_unicode_filename(app, pyfs):
    """Test sending the non-unicode filename in the header."""
    data = b'HelloWorld'
    uri, size, checksum = pyfs.save(BytesIO(data))

    with app.test_request_context():
        res = pyfs.send_file(
            u'żółć.dat', mimetype='application/octet-stream',
            checksum=checksum)
        assert res.status_code == 200
        assert set(res.headers['Content-Disposition'].split('; ')) == \
            set(["attachment", "filename=zoc.dat",
                 "filename*=UTF-8''%C5%BC%C3%B3%C5%82%C4%87.dat"])

    with app.test_request_context():
        res = pyfs.send_file(
            'żółć.txt', mimetype='text/plain', checksum=checksum)
        assert res.status_code == 200
        assert res.headers['Content-Disposition'] == 'inline'
