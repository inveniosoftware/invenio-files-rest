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

"""Models for Invenio-Files-REST."""

from __future__ import absolute_import, print_function

import re
import uuid

import six
from flask import current_app
from invenio_db import db
from sqlalchemy.orm import validates
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import UUIDType

from .errors import FileInstanceAlreadySetError

slug_pattern = re.compile("^[a-z][a-z0-9-]+$")


class Location(db.Model, Timestamp):
    """Model defining base locations."""

    __tablename__ = 'files_location'

    id = db.Column(db.Integer, primary_key=True)
    """Id of location."""

    name = db.Column(db.String(20), unique=True, nullable=False)
    """Name of the location."""

    uri = db.Column(db.String(255), nullable=False)
    """URI of the location."""

    default = db.Column(db.Boolean, nullable=False, default=False)
    """True if the location is the default location."""

    @validates('name')
    def validate_name(self, key, name):
        """Validate name."""
        if not slug_pattern.match(name) or len(name) > 20:
            raise ValueError(
                "Invalid location name (lower-case alphanumeric + danshes).")
        return name

    @classmethod
    def get_by_name(cls, name):
        """Fetch a specific location object."""
        return cls.query.filter_by(
            name=name,
        ).one()

    @classmethod
    def get_default(cls):
        """Fetch the default location object."""
        return cls.query.filter_by(default=True).first()

    @classmethod
    def all(cls):
        """Return query that fetches all locations."""
        return Location.query.all()

    def __repr__(self):
        """Return representation of location."""
        return self.name


class Bucket(db.Model, Timestamp):
    """Model for storing buckets."""

    __tablename__ = 'files_bucket'

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    """Bucket identifier."""

    default_location = db.Column(
        db.Integer,
        db.ForeignKey(Location.id, ondelete='RESTRICT'),
        nullable=False)

    default_storage_class = db.Column(
        db.String(1), nullable=False,
        default=lambda: current_app.config['FILES_REST_DEFAULT_STORAGE_CLASS'])

    size = db.Column(db.BigInteger, default=0, nullable=False)

    quota_size = db.Column(db.BigInteger, nullable=True)

    locked = db.Column(db.Boolean, default=False, nullable=False)

    deleted = db.Column(db.Boolean, default=False, nullable=False)

    location = db.relationship(Location, backref='buckets')
    """Location associated with this bucket."""

    def __repr__(self):
        """Return representation of location."""
        return str(self.id)

    @validates('default_storage_class')
    def validate_storage_class(self, key, default_storage_class):
        """Validate name."""
        if default_storage_class not in \
           current_app.config['FILES_REST_STORAGE_CLASS_LIST']:
            raise ValueError('Invalid storage class.')
        return default_storage_class

    def snapshot(self, lock=True):
        """Create a snapshot of latest objects in bucket."""
        if self.deleted:
            raise ValueError("Cannot make snapshot of a deleted bucket.")
        Bucket(
            default_location=self.default_location,
            default_storage_class=self.default_storage_class,
            quota_size=self.quota_size,
        )

    @classmethod
    def create(cls, location=None, storage_class=None):
        """Create a bucket."""
        with db.session.begin_nested():
            if location is None:
                location = Location.get_default()
            elif isinstance(Location, six.string_types):
                location = Location.get_by_name(location)

            obj = cls(
                location=location,
                default_storage_class=storage_class or current_app.config[
                    'FILES_REST_DEFAULT_STORAGE_CLASS'])
            db.session.add(obj)
        return obj

    @classmethod
    def get(cls, bucket_id):
        """Return a specific bucket object."""
        return cls.query.filter_by(
            id=bucket_id,
            deleted=False
        ).first()

    @classmethod
    def all(cls):
        """Return all buckets."""
        return cls.query.filter_by(
            deleted=False
        )


class FileInstance(db.Model, Timestamp):
    """Model for storing objects."""

    __tablename__ = 'files_files'

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )

    uri = db.Column(db.String(255), unique=True, nullable=True)
    """Location of file."""

    storage_class = db.Column(db.String(1), nullable=True)
    """Storage class of object."""

    size = db.Column(db.BigInteger, default=0, nullable=True)
    """Size of object."""

    checksum = db.Column(db.String(255), nullable=True)
    """String representing the checksum of the object."""

    read_only = db.Column(db.Boolean, default=False, nullable=False)
    """Defines if the file is read only."""

    def storage(self, obj):
        """Get storage for object."""
        return current_app.extensions['invenio-files-rest'].storage_factory(
            obj=obj, fileinstance=self)

    def set_contents(self, obj, stream, size=None, chunk_size=None):
        """Save contents of stream to this file."""
        if self.read_only:
            raise ValueError("FileInstance is read-only.")
        self.set_uri(*self.storage(obj).save(
            stream, size=size, chunk_size=chunk_size), read_only=True)

    def send_file(self, obj):
        """Send file to client."""
        return self.storage(obj).send_file()

    def set_uri(self, uri, size, checksum, read_only=True,
                storage_class=None):
        """Set a location of a file."""
        self.uri = uri
        self.size = size
        self.checksum = checksum
        self.read_only = read_only
        if storage_class is not None:
            self.storage_class = storage_class
        else:
            self.storage_class = \
                current_app.config['FILES_REST_DEFAULT_STORAGE_CLASS']


class Object(db.Model, Timestamp):
    """Model for storing objects."""

    __tablename__ = 'files_object'

    bucket_id = db.Column(
        UUIDType,
        db.ForeignKey(Bucket.id, ondelete='RESTRICT'),
        default=uuid.uuid4,
        primary_key=True, )

    key = db.Column(
        db.String(255),
        primary_key=True, )

    version_id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4, )

    file_id = db.Column(
        UUIDType,
        db.ForeignKey(FileInstance.id, ondelete='RESTRICT'), nullable=True)
    """Location of object.

    A null value in this column defines that the object has been deleted.
    """

    is_head = db.Column(db.Boolean, nullable=False, default=True)
    """Defines if object is the latest version."""

    # Relationships definitions
    bucket = db.relationship(Bucket, backref='objects')
    """Relationship to buckets."""

    file = db.relationship(FileInstance, backref='objects')
    """Relationship to file instance."""

    def __repr__(self):
        """Return representation of location."""
        return "{0}:{1}?versionId={2}".format(
            self.bucket_id, self.key, self.version_id)

    @property
    def is_deleted(self):
        """Determine if object is a delete marker."""
        return self.file_id is None

    def set_contents(self, stream, size=None, chunk_size=None):
        """Save contents of stream to object."""
        if self.file_id is not None:
            raise FileInstanceAlreadySetError()

        self.file = FileInstance()
        db.session.add(self.file)
        self.file.set_contents(
            self, stream, size=size, chunk_size=chunk_size)

        self.bucket.size += self.file.size

    def set_location(self, uri, size, checksum, storage_class=None):
        """Set only URI location of for object."""
        if self.file_id is not None:
            raise FileInstanceAlreadySetError()

        self.file = FileInstance()
        self.file.set_uri(uri, size, checksum, storage_class=storage_class)
        db.session.add(self.file)

        self.bucket.size += size

    def send_file(self):
        """Send file to client."""
        return self.file.send_file(self)

    @classmethod
    def create(cls, bucket, key, stream=None, **kwargs):
        """Create a new object in a bucket."""
        with db.session.begin_nested():
            latest_obj = cls.get(bucket.id, key)
            if latest_obj is not None:
                latest_obj.is_head = False
                db.session.add(latest_obj)

            # By default objects are created in a deleted state (i.e.
            # file_id is null).
            obj = cls(
                bucket=bucket,
                key=key,
                version_id=uuid.uuid4(),
                is_head=True,
            )
            db.session.add(obj)
        if stream:
            obj.set_contents(stream, **kwargs)
        return obj

    @classmethod
    def get(cls, bucket_id, key, version_id=None, with_deleted=False):
        """Fetch a specific object."""
        args = [
            cls.bucket_id == bucket_id,
            cls.key == key,
        ]

        if version_id:
            args.append(cls.version_id == version_id)
        else:
            args.append(cls.is_head == True)  # noqa
        if not with_deleted:
            args.append(cls.file_id != None)  # noqa

        return cls.query.filter(*args).one_or_none()

    @classmethod
    def delete(cls, bucket_id, key):
        """Delete an object.

        :returns: True if the object file exists.
        """
        if cls.get(bucket_id, key):
            return cls.create(Bucket.get(bucket_id), key)
        return None

    @classmethod
    def get_by_bucket(cls, bucket_id, versions=False):
        """Return query that fetches all the objects in a bucket."""
        args = [
            cls.bucket_id == bucket_id,
            cls.file_id != None,  # noqa
        ]

        if not versions:
            args.append(cls.is_head == True)  # noqa

        return cls.query.filter(*args).order_by(cls.key, cls.created.desc())


__all__ = (
    'Location',
    'Bucket',
    'Object',
    'FileInstance',
)
