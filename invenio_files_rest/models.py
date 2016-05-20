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

"""Models for Invenio-Files-REST.

The entities of this module consists of:

 * **Buckets** - Identified by UUIDs, and contains objects.
 * **Buckets tags** - Identified uniquely with a bucket by a key. Used to store
   extra metadata for a bucket.
 * **Objects** - Identified uniquely within a bucket by string keys. Each
   object can have multiple object versions (note: Objects do not have their
   own database table).
 * **Object versions** - Identified by UUIDs and belongs to one specific object
   in one bucket. Each object version has zero or one file instance. If the
   object version has no file instance, it is considered a *delete marker*.
 * **File instance** - Identified by UUIDs. Represents a physical file on disk.
   The location of the file is specified via a URI. A file instance can have
   many object versions.
 * **Locations** - A bucket belongs to a specific location. Locations can be
   used to represent e.g. different storage systems and/or geographical
   locations.

The actual file access is handled by a storage interface. Also, objects do not
have their own model, but are represented via the :py:data:`ObjectVersion`
model.
"""

from __future__ import absolute_import, print_function

import re
import uuid
from datetime import datetime

import six
from flask import current_app
from invenio_db import db
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import validates
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy_utils.types import UUIDType

from .errors import FileInstanceAlreadySetError, InvalidOperationError

slug_pattern = re.compile('^[a-z][a-z0-9-]+$')


class Timestamp(object):
    """Timestamp model mix-in with fractional seconds support.

    SQLAlchemy-Utils timestamp model, does not have support for fractional
    seconds.
    """

    created = db.Column(
        db.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'),
        default=datetime.utcnow,
        nullable=False
    )
    """Creation timestamp."""

    updated = db.Column(
        db.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql'),
        default=datetime.utcnow,
        nullable=False
    )
    """Modification timestamp."""


@db.event.listens_for(Timestamp, 'before_update', propagate=True)
def timestamp_before_update(mapper, connection, target):
    """Listener for updating updated field."""
    target.updated = datetime.utcnow()


class Location(db.Model, Timestamp):
    """Model defining base locations."""

    __tablename__ = 'files_location'

    id = db.Column(db.Integer, primary_key=True)
    """Internal identifier for locations.

    The internal identifier is used only used as foreign key for buckets in
    order to decrease storage requirements per row for buckets.
    """

    name = db.Column(db.String(20), unique=True, nullable=False)
    """External identifier of the location."""

    uri = db.Column(db.String(255), nullable=False)
    """URI of the location."""

    default = db.Column(db.Boolean, nullable=False, default=False)
    """True if the location is the default location.

    At least one location should be the default location.
    """

    @validates('name')
    def validate_name(self, key, name):
        """Validate name."""
        if not slug_pattern.match(name) or len(name) > 20:
            raise ValueError(
                'Invalid location name (lower-case alphanumeric + danshes).')
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
        try:
            return cls.query.filter_by(default=True).one_or_none()
        except MultipleResultsFound:
            return None

    @classmethod
    def all(cls):
        """Return query that fetches all locations."""
        return Location.query.all()

    def __repr__(self):
        """Return representation of location."""
        return self.name


class Bucket(db.Model, Timestamp):
    """Model for storing buckets.

    A bucket is a container of objects. Buckets have a default location and
    storage class. Individual objects in the bucket can however have different
    locations and storage classes.

    A bucket can be marked as deleted. A bucket can also be marked as locked
    to prevent operations on the bucket.

    Each bucket can also define a quota. The size of a bucket is the size
    of all objects in the bucket (including all versions).
    """

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
    """Default location."""

    default_storage_class = db.Column(
        db.String(1), nullable=False,
        default=lambda: current_app.config['FILES_REST_DEFAULT_STORAGE_CLASS'])
    """Default storage class."""

    size = db.Column(db.BigInteger, default=0, nullable=False)
    """Size of bucket.

    This is a computed property which can rebuilt any time from the objects
    inside the bucket.
    """

    quota_size = db.Column(db.BigInteger, nullable=True)
    """Quota size of bucket. Used only by the file_size_limiter.

    Note, don't use this attribute directly. It MAY be used to store
    the actual quota size for this bucket. Change the file_size_limiter if
    you want to filter accepted files based on their size.
    """

    locked = db.Column(db.Boolean, default=False, nullable=False)
    """Is bucket locked?"""

    deleted = db.Column(db.Boolean, default=False, nullable=False)
    """Is bucket deleted?"""

    location = db.relationship(Location, backref='buckets')
    """Location associated with this bucket."""

    def __repr__(self):
        """Return representation of location."""
        return str(self.id)

    @validates('default_storage_class')
    def validate_storage_class(self, key, default_storage_class):
        """Validate storage class."""
        if default_storage_class not in \
           current_app.config['FILES_REST_STORAGE_CLASS_LIST']:
            raise ValueError('Invalid storage class.')
        return default_storage_class

    def snapshot(self, lock=False):
        """Create a snapshot of latest objects in bucket.

        :param lock: Create the new bucket in a locked state.
        :returns: Newly created bucket with the snapshot.
        """
        if self.deleted:
            raise InvalidOperationError(
                'Cannot make snapshot of a deleted bucket.')
        with db.session.begin_nested():
            b = Bucket(
                default_location=self.default_location,
                default_storage_class=self.default_storage_class,
                quota_size=self.quota_size,
                locked=True if lock else self.locked,
            )
            db.session.add(b)

        for o in ObjectVersion.get_by_bucket(self):
            o.copy(bucket=b)

        return b

    def get_tags(self):
        """Get tags for bucket as dictionary."""
        return {t.key: t.value for t in self.tags}

    @classmethod
    def create(cls, location=None, storage_class=None):
        """Create a bucket.

        :param location: Location of bucket (instance or name).
            Default: Default location.
        :param storage_class: Storage class of bucket.
            Default: Default storage class.
        :returns: Created bucket.
        """
        with db.session.begin_nested():
            if location is None:
                location = Location.get_default()
            elif isinstance(location, six.string_types):
                location = Location.get_by_name(location)

            obj = cls(
                location=location,
                default_storage_class=storage_class or current_app.config[
                    'FILES_REST_DEFAULT_STORAGE_CLASS'])
            db.session.add(obj)
        return obj

    @classmethod
    def get(cls, bucket_id):
        """Get bucket object (excluding deleted).

        :param bucket_id: Bucket identifier.
        :returns: Bucket instance.
        """
        return cls.query.filter_by(
            id=bucket_id,
            deleted=False
        ).one_or_none()

    @classmethod
    def all(cls):
        """Return query of all buckets (excluding deleted)."""
        return cls.query.filter_by(
            deleted=False
        )


class BucketTag(db.Model):
    """Model for storing tags associated to buckets.

    This is useful to store extra information for a bucket.
    """

    __tablename__ = 'files_buckettags'

    bucket_id = db.Column(
        UUIDType,
        db.ForeignKey(Bucket.id, ondelete='CASCADE'),
        default=uuid.uuid4,
        primary_key=True, )

    key = db.Column(db.String(255), primary_key=True)
    """Tag key."""

    value = db.Column(db.Text, nullable=False)
    """Tag value."""

    bucket = db.relationship(Bucket, backref='tags')
    """Relationship to buckets."""

    @classmethod
    def get(cls, bucket, key):
        """Get tag object."""
        return cls.query.filter_by(
            bucket_id=bucket.id if isinstance(bucket, Bucket) else bucket,
            key=key,
        ).one_or_none()

    @classmethod
    def create(cls, bucket, key, value):
        """Create a new tag for bucket."""
        with db.session.begin_nested():
            obj = cls(
                bucket_id=bucket.id if isinstance(bucket, Bucket) else bucket,
                key=key,
                value=value
            )
            db.session.add(obj)
        return obj

    @classmethod
    def create_or_update(cls, bucket, key, value):
        """Create a new tag for bucket."""
        obj = cls.get(bucket, key)
        if obj:
            obj.value = value
        else:
            cls.create(bucket, key, value)

    @classmethod
    def get_value(cls, bucket, key):
        """Get tag value."""
        obj = cls.get(bucket, key)
        return obj.value if obj else None

    @classmethod
    def delete(cls, bucket, key):
        """Delete a tag."""
        with db.session.begin_nested():
            cls.query.filter_by(
                bucket_id=bucket.id if isinstance(bucket, Bucket) else bucket,
                key=key,
            ).delete()


class FileInstance(db.Model, Timestamp):
    """Model for storing files.

    A file instance represents a file on disk. A file instance may be linked
    from many objects, while an object can have one and only one file instance.

    A file instance also records the storage class, size and checksum of the
    file on disk.

    Additionally, a file instance can be read only in case the storage layer
    is not capable of writing to the file (e.g. can typically be used to
    link to files on externally controlled storage).
    """

    __tablename__ = 'files_files'

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    """Identifier of file."""

    uri = db.Column(db.Text().with_variant(mysql.VARCHAR(255), 'mysql'),
                    unique=True, nullable=True)
    """Location of file."""

    storage_class = db.Column(db.String(1), nullable=True)
    """Storage class of file."""

    size = db.Column(db.BigInteger, default=0, nullable=True)
    """Size of file."""

    checksum = db.Column(db.String(255), nullable=True)
    """String representing the checksum of the object."""

    readable = db.Column(db.Boolean, default=True, nullable=False)
    """Defines if the file is read only."""

    writable = db.Column(db.Boolean, default=True, nullable=False)
    """Defines if file is writable.

    This property is used to create a file instance prior to having the actual
    file at the given URI. This is useful when e.g. copying a file instance.
    """

    last_check_at = db.Column(db.DateTime, nullable=True)
    """Timestamp of last fixity check."""

    last_check = db.Column(db.Boolean, default=True, nullable=False)
    """Result of last fixity check."""

    @validates('uri')
    def validate_uri(self, key, uri):
        """Validate uri."""
        if len(uri) > current_app.config['FILES_REST_FILE_URI_MAX_LEN']:
            raise ValueError(
                'FileInstance URI too long ({0}).'.format(len(uri)))
        return uri

    @classmethod
    def get(cls, file_id):
        """Get a file instance."""
        return cls.query.filter_by(id=file_id).one_or_none()

    @classmethod
    def get_by_uri(cls, uri):
        """Get a file instance by URI."""
        assert uri is not None
        return cls.query.filter_by(uri=uri).one_or_none()

    @classmethod
    def create(cls):
        """Create a file instance.

        Note, object is only added to the database session.
        """
        obj = cls(
            id=uuid.uuid4(),
            writable=True,
            readable=False,
            size=0,
        )
        db.session.add(obj)
        return obj

    def storage(self, **kwargs):
        """Get storage interface for object.

        Uses the applications storage factory to create a storage interface
        that can be used for this particular file instance.

        :returns: Storage interface.
        """
        return current_app.extensions['invenio-files-rest'].storage_factory(
            fileinstance=self, **kwargs)

    def verify_checksum(self, progress_callback=None, **kwargs):
        """Verify checksum of file instance."""
        real_checksum = self.storage(**kwargs).compute_checksum(
            progress_callback=progress_callback)
        with db.session.begin_nested():
            self.last_check = (self.checksum == real_checksum)
            self.last_check_at = datetime.utcnow()
        return self.last_check

    def set_contents(self, stream, chunk_size=None,
                     progress_callback=None, **kwargs):
        """Save contents of stream to this file.

        :param obj: ObjectVersion instance from where this file is accessed
            from.
        :param stream: File-like stream.
        """
        if not self.writable:
            raise ValueError('File instance is not writable.')
        self.set_uri(
            *self.storage(**kwargs).save(
                stream, chunk_size=chunk_size,
                progress_callback=progress_callback))

    def copy_contents(self, fileinstance, progress_callback=None, **kwargs):
        """Copy this file instance into another file instance."""
        if not fileinstance.readable:
            raise ValueError('Source file instance is not readable.')
        if not self.writable:
            raise ValueError('File instance is not writable.')
        if not self.size == 0:
            raise ValueError('File instance has data.')

        self.set_uri(
            *self.storage(**kwargs).copy(
                fileinstance, progress_callback=progress_callback))

    def send_file(self, mimetype=None, **kwargs):
        """Send file to client."""
        if not self.readable:
            raise ValueError('File instance is not readable.')
        return self.storage(**kwargs).send_file(mimetype=mimetype)

    def set_uri(self, uri, size, checksum, readable=True, writable=False,
                storage_class=None):
        """Set a location of a file."""
        self.uri = uri
        self.size = size
        self.checksum = checksum
        self.writable = writable
        self.readable = readable
        self.storage_class = \
            current_app.config['FILES_REST_DEFAULT_STORAGE_CLASS'] \
            if storage_class is None else \
            storage_class
        return self


class ObjectVersion(db.Model, Timestamp):
    """Model for storing versions of objects.

    A bucket stores one or more objects identified by a key. Each object is
    versioned where each version is represented by an ``ObjectVersion``.

    An object version can either be 1) a *normal version* which is linked to
    a file instance, or 2) a *delete marker*, which is *not* linked to a file
    instance.

    An normal object version is linked to a physical file on disk via a file
    instance. This allows for multiple object versions to point to the same
    file on disk, to optimize storage efficiency (e.g. useful for snapshotting
    an entire bucket without duplicating the files).

    A delete marker object version represents that the object at hand was
    deleted.

    The latest version of an object is marked using the ``is_head`` property.
    If the latest object version is a delete marker the object will not be
    shown in the bucket.
    """

    __tablename__ = 'files_object'

    bucket_id = db.Column(
        UUIDType,
        db.ForeignKey(Bucket.id, ondelete='RESTRICT'),
        default=uuid.uuid4,
        primary_key=True, )
    """Bucket identifier."""

    key = db.Column(
        db.Text().with_variant(mysql.VARCHAR(255), 'mysql'),
        primary_key=True, )
    """Key identifying the object."""

    version_id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4, )
    """Identifier for the specific version of an object."""

    file_id = db.Column(
        UUIDType,
        db.ForeignKey(FileInstance.id, ondelete='RESTRICT'), nullable=True)
    """File instance for this object version.

    A null value in this column defines that the object has been deleted.
    """

    mimetype = db.Column(
        db.String(255),
        index=True,
        nullable=True, )
    """MIME type of the object."""

    is_head = db.Column(db.Boolean, nullable=False, default=True)
    """Defines if object is the latest version."""

    # Relationships definitions
    bucket = db.relationship(Bucket, backref='objects')
    """Relationship to buckets."""

    file = db.relationship(FileInstance, backref='objects')
    """Relationship to file instance."""

    @validates('key')
    def validate_key(self, key, key_):
        """Validate key."""
        if len(key_) > current_app.config['FILES_REST_OBJECT_KEY_MAX_LEN']:
            raise ValueError(
                'ObjectVersion key too long ({0}).'.format(len(key_)))
        return key_

    def __repr__(self):
        """Return representation of location."""
        return '{0}:{2}:{1}'.format(
            self.bucket_id, self.key, self.version_id)

    @property
    def is_deleted(self):
        """Determine if object version is a delete marker."""
        return self.file_id is None

    def set_contents(self, stream, size=None, chunk_size=None,
                     progress_callback=None):
        """Save contents of stream to file instance.

        If a file instance has already been set, this methods raises an
        ``FileInstanceAlreadySetError`` exception.

        :param stream: File-like stream.
        :param size: Size of stream if known.
        :param chunk_size: Desired chunk size to read stream in. It is up to
            the storage interface if it respects this value.
        """
        if self.file_id is not None:
            raise FileInstanceAlreadySetError()

        self.file = FileInstance.create()
        self.file.set_contents(
            stream, size=size, chunk_size=chunk_size,
            progress_callback=progress_callback, objectversion=self)

        self.bucket.size += self.file.size

        return self

    def set_location(self, uri, size, checksum, storage_class=None):
        """Set only URI location of for object.

        Useful to link files on externally controlled storage. If a file
        instance has already been set, this methods raises an
        ``FileInstanceAlreadySetError`` exception.

        :param uri: Full URI to object (which can be interpreted by the storage
            interface).
        :param size: Size of file.
        :param checksum: Checksum of file.
        :param storage_class: Storage class where file is stored ()
        """
        if self.file_id is not None:
            raise FileInstanceAlreadySetError()

        self.file = FileInstance()
        self.file.set_uri(
            uri, size, checksum, storage_class=storage_class
        )
        db.session.add(self.file)

        self.bucket.size += size

        return self

    def set_file(self, fileinstance):
        """Set a file instance."""
        if self.file_id is not None:
            raise FileInstanceAlreadySetError()

        self.file = fileinstance
        self.bucket.size += self.file.size

        return self

    def restore(self):
        """Restore version of an object.

        Raises an exception if the object is not the latest version.
        """
        if self.is_head:
            raise InvalidOperationError('Cannot restore latest version.')
        return self.copy()

    def copy(self, bucket=None, key=None):
        """Copy an object version to a given bucket + object key.

        The copy operation is handled completely at the metadata level. The
        actual data on disk is not copied. Instead, the two object versions
        will point to the same physical file (via the same FileInstance).

        .. warning::

           If the destination object exists, it will be replaced by  the new
           object version which will become the latest version.

        :param bucket: The bucket (instance or id) to copy the object to.
            Default: current bucket.
        :param key: Key name of destination object.
            Default: current object key.
        :returns: The copied object version.
        """
        if self.is_deleted:
            raise InvalidOperationError('Cannot copy a delete marker.')

        # Get bucket
        if bucket is None:
            bucket = self.bucket
        else:
            bucket = bucket if isinstance(bucket, Bucket) else Bucket.get(
                bucket)

        obj = ObjectVersion.create(
            bucket, key or self.key, _file_id=self.file_id)
        return obj

    @classmethod
    def create(cls, bucket, key, _file_id=None, stream=None, mimetype=None,
               **kwargs):
        """Create a new object in a bucket.

        The created object is by default created as a delete marker. You must
        use ``set_contents()`` or ``set_location()`` in order to change this.

        :param bucket: The bucket (instance or id) to create the object in.
        :param key: Key of object.
        :param _file_id: For internal use.
        :param stream: File-like stream object. Used to set content of object
            immediately after being created.
        :param mimetype: MIME type of the file object if it is known.
        :param kwargs: Keyword arguments passed to ``Object.set_contents()``.
        """
        bucket = bucket if isinstance(bucket, Bucket) else Bucket.get(bucket)

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
                mimetype=mimetype,
            )
            if _file_id:
                obj.file_id = _file_id
            db.session.add(obj)
        if stream:
            obj.set_contents(stream, **kwargs)
        return obj

    @classmethod
    def get(cls, bucket, key, version_id=None):
        """Fetch a specific object.

        By default the latest object version is returned, if
        ``version_id`` is not set.

        :param bucket: The bucket (instance or id) to get the object from.
        :param key: Key of object.
        :param version_id: Specific version of an object.
        """
        bucket_id = bucket.id if isinstance(bucket, Bucket) else bucket

        args = [
            cls.bucket_id == bucket_id,
            cls.key == key,
        ]

        if version_id:
            args.append(cls.version_id == version_id)
        else:
            args.append(cls.is_head.is_(True))
            args.append(cls.file_id.isnot(None))

        return cls.query.filter(*args).one_or_none()

    @classmethod
    def get_versions(cls, bucket, key):
        """Fetch all versions of a specific object.

        :param bucket: The bucket (instance or id) to get the object from.
        :param key: Key of object.
        """
        bucket_id = bucket.id if isinstance(bucket, Bucket) else bucket

        args = [
            cls.bucket_id == bucket_id,
            cls.key == key,
        ]

        return cls.query.filter(*args).order_by(cls.key, cls.created.desc())

    @classmethod
    def delete(cls, bucket, key):
        """Delete an object.

        Technically works by creating a new version which works as a delete
        marker.

        :param bucket: The bucket (instance or id) to delete the object from.
        :param key: Key of object.
        :returns: Created delete marker object if key exists else ``None``.
        """
        bucket_id = bucket.id if isinstance(bucket, Bucket) else bucket

        if cls.get(bucket_id, key):
            return cls.create(Bucket.get(bucket_id), key)

    @classmethod
    def get_by_bucket(cls, bucket, versions=False):
        """Return query that fetches all the objects in a bucket."""
        bucket_id = bucket.id if isinstance(bucket, Bucket) else bucket

        args = [
            cls.bucket_id == bucket_id,
        ]

        if not versions:
            args.append(cls.file_id.isnot(None))
            args.append(cls.is_head.is_(True))

        return cls.query.filter(*args).order_by(cls.key, cls.created.desc())

    @classmethod
    def relink_all(cls, old_file, new_file):
        """Relink all object versions (for a given file) to a new file.

        .. warning::

           Use this method with great care.
        """
        assert old_file.checksum == new_file.checksum
        assert old_file.id
        assert new_file.id

        with db.session.begin_nested():
            ObjectVersion.query.filter_by(file_id=str(old_file.id)).update({
                ObjectVersion.file_id: str(new_file.id)})


__all__ = (
    'Bucket',
    'FileInstance',
    'Location',
    'ObjectVersion',
)
