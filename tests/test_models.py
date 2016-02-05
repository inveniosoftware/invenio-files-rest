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

"""Module test views."""

from __future__ import absolute_import, print_function

from os.path import getsize

import pytest

from invenio_files_rest.errors import FileInstanceAlreadySetError
from invenio_files_rest.models import Bucket, FileInstance, Location, Object


def test_location(app, db):
    """Test location model."""
    with db.session.begin_nested():
        l1 = Location(name='test1', uri='file:///tmp', default=False)
        l2 = Location(name='test2', uri='file:///tmp', default=True)
        l3 = Location(name='test3', uri='file:///tmp', default=True)
        db.session.add(l1)
        db.session.add(l2)
        db.session.add(l3)

    assert Location.get_by_name('test1').name == 'test1'
    assert Location.get_by_name('test2').name == 'test2'
    assert Location.get_by_name('test3').name == 'test3'

    assert Location.get_default().name == 'test2'
    assert len(Location.all()) == 3

    assert str(Location.get_by_name('test1')) == 'test1'


def test_location_validation(app, db):
    """Test validation of location name."""
    pytest.raises(ValueError, Location, name='UPPER', uri='file://', )
    pytest.raises(ValueError, Location, name='1ab', uri='file://', )
    pytest.raises(ValueError, Location, name='a'*21, uri='file://', )


def test_bucket_create(app, db):
    """Test bucket creation."""
    with db.session.begin_nested():
        l1 = Location(name='test1', uri='file:///tmp/1', default=False)
        l2 = Location(name='test2', uri='file:///tmp/2', default=True)
        db.session.add(l1)
        db.session.add(l2)

    assert Location.query.count() == 2

    # Simple create
    with db.session.begin_nested():
        b = Bucket.create()
        assert b.id
        assert b.default_location == Location.get_default().id
        assert b.location == Location.get_default()
        assert b.default_storage_class == \
            app.config['FILES_REST_DEFAULT_STORAGE_CLASS']
        assert b.size == 0
        assert b.quota_size is None
        assert b.deleted is False
        db.session.add(b)

    # __repr__ test
    assert str(b) == str(b.id)

    # Retrieve one
    assert Bucket.get(b.id).id == b.id

    # Create with location_name and storage class
    with db.session.begin_nested():
        b = Bucket.create(location_name='test1', storage_class='A')
        assert b.default_location == Location.get_by_name('test1').id
        assert b.default_storage_class == 'A'
        db.session.add(b)

    # Retreieve one
    assert Bucket.all().count() == 2

    # Invalid storage class.
    pytest.raises(ValueError, Bucket.create, storage_class='X')


def test_bucket_retrieval(app, db, dummy_location):
    """Test bucket get/create."""
    with db.session.begin_nested():
        b1 = Bucket.create()
        Bucket.create()

    assert Bucket.all().count() == 2

    with db.session.begin_nested():
        b1.deleted = True

    assert Bucket.all().count() == 1


def test_object_create(app, db, dummy_location):
    """Test object creation."""
    with db.session.begin_nested():
        b = Bucket.create()
        obj1 = Object.create(b, "test")
        assert obj1.bucket_id == b.id
        assert obj1.key == 'test'
        assert obj1.version_id
        assert obj1.file_id is None
        assert obj1.is_head is True
        assert obj1.bucket == b

        # Set fake location.
        obj1.set_location("file:///tmp/obj1", 1, "checksum")

        obj2 = Object.create(b, "test")
        assert obj2.bucket_id == b.id
        assert obj2.key == 'test'
        assert obj2.version_id != obj1.version_id
        assert obj2.file_id is None
        assert obj2.is_head is True
        assert obj2.bucket == b

        # Set fake location
        obj2.set_location("file:///tmp/obj2", 2, "checksum")

        # Obj 3 has no location, and thus considered deleted.
        Object.create(b, "deleted_obj")

    # Sanity check
    assert Object.query.count() == 3

    # Assert that obj2 is the head version
    obj = Object.get(b.id, "test", version_id=obj1.version_id)
    assert obj.version_id == obj1.version_id
    assert obj.is_head is False
    obj = Object.get(b.id, "test", version_id=obj2.version_id)
    assert obj.version_id == obj2.version_id
    assert obj.is_head is True
    obj = Object.get(b.id, "test")
    assert obj.version_id == obj2.version_id
    assert obj.is_head is True

    # Assert that obj3 is not retrievable.
    assert Object.get(b.id, "deleted_obj") is None
    assert Object.get(b.id, "deleted_obj", with_deleted=True) is not None


def test_object_multibucket(app, db, dummy_location):
    """Test object creation."""
    with db.session.begin_nested():
        b1 = Bucket.create()
        b2 = Bucket.create()
        obj1 = Object.create(b1, "test")
        obj1.set_location("file:///tmp/obj1", 1, "checksum")
        obj2 = Object.create(b2, "test")
        obj2.set_location("file:///tmp/obj2", 2, "checksum")

    # Sanity check
    assert Object.query.count() == 2

    # Assert no versions are created
    obj = Object.get(b1.id, "test")
    assert obj.is_head is True
    assert obj.version_id == obj1.version_id
    obj = Object.get(b2.id, "test")
    assert obj.is_head is True
    assert obj.version_id == obj2.version_id


def test_object_get_by_bucket(app, db, dummy_location):
    """Test object creation."""
    with db.session.begin_nested():
        b1 = Bucket.create()
        b2 = Bucket.create()
        obj1_first = Object.create(b1, "test")
        obj1_first.set_location("b1test1", 1, "achecksum")
        Object.create(b1, "test")
        obj1_latest = Object.create(b1, "test")
        obj1_latest.set_location("b1test3", 1, "achecksum")
        Object.create(b1, "another").set_location("b1another1", 1, "achecksum")
        Object.create(b2, "test").set_location("b2test1", 1, "achecksum")

    # Sanity check
    assert Object.query.count() == 5
    assert Object.get(b1.id, "test")
    assert Object.get(b1.id, "another")
    assert Object.get(b2.id, "test")

    # Retrieve objects for a bucket with/without versions
    assert Object.get_by_bucket(b1.id).count() == 2
    assert Object.get_by_bucket(b1.id, versions=True).count() == 3
    assert Object.get_by_bucket(b2.id).count() == 1
    assert Object.get_by_bucket(b2.id, versions=True).count() == 1

    # Assert order of returned objects (alphabetical)
    objs = Object.get_by_bucket(b1.id).all()
    assert objs[0].key == "another"
    assert objs[1].key == "test"

    # Assert order of returned objects verions (creation date ascending)
    objs = Object.get_by_bucket(b1.id, versions=True).all()
    assert objs[0].key == "another"
    assert objs[1].key == "test"
    assert objs[1].version_id == obj1_latest.version_id
    assert objs[2].key == "test"
    assert objs[2].version_id == obj1_first.version_id


def test_object_delete(app, db, dummy_location):
    """Test object creation."""
    with db.session.begin_nested():
        b1 = Bucket.create()
        Object.create(b1, "test").set_location("b1test1", 1, "achecksum")
        Object.create(b1, "test").set_location("b1test2", 1, "achecksum")
        Object.delete(b1.id, "test")

    assert Object.query.count() == 3
    assert Object.get(b1.id, "test") is None
    assert Object.get_by_bucket(b1.id).count() == 0

    obj = Object.get(b1.id, "test", with_deleted=True)
    assert obj.is_deleted
    assert obj.file_id is None

    with db.session.begin_nested():
        Object.create(b1, "test").set_location("b1test4", 1, "achecksum")

    assert Object.query.count() == 4
    assert Object.get(b1.id, "test") is not None
    assert Object.get_by_bucket(b1.id).count() == 1


def test_object_set_contents(app, db, dummy_location):
    """Test object set contents."""
    with db.session.begin_nested():
        b1 = Bucket.create()
        obj = Object.create(b1, "LICENSE")
        assert obj.file_id is None
        assert FileInstance.query.count() == 0

        # Save a file.
        with open('LICENSE', 'rb') as fp:
            obj.set_contents(fp)

    # Assert size, location and checksum
    assert obj.file_id is not None
    assert obj.file.uri is not None
    assert obj.file.size == getsize('LICENSE')
    assert obj.file.checksum is not None
    assert b1.size == obj.file.size

    # Try to overwrite
    with db.session.begin_nested():
        with open('LICENSE', 'rb') as fp:
            pytest.raises(FileInstanceAlreadySetError, obj.set_contents, fp)

    # Save a new version with different content
    with db.session.begin_nested():
        obj2 = Object.create(b1, "LICENSE")
        with open('README.rst', 'rb') as fp:
            obj2.set_contents(fp)

    assert obj2.file_id is not None and obj2.file_id != obj.file_id
    assert obj2.file.size == getsize('README.rst')
    assert obj2.file.uri != obj.file.uri
    assert Bucket.get(b1.id).size == obj.file.size + obj2.file.size


def test_object_set_location(app, db, dummy_location):
    """Test object set contents."""
    with db.session.begin_nested():
        b1 = Bucket.create()
        obj = Object.create(b1, "LICENSE")
        assert obj.file_id is None
        assert FileInstance.query.count() == 0
        obj.set_location("b1test1", 1, "achecksum")
        assert FileInstance.query.count() == 1
        pytest.raises(
            FileInstanceAlreadySetError,
            obj.set_location, "b1test1", 1, "achecksum")
