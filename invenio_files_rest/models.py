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

"""Models for Invenio-Files-REST."""

from __future__ import absolute_import, print_function

import uuid

from flask import url_for
from invenio_db import db
from sqlalchemy import desc
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import UUIDType


class Location(db.Model, Timestamp):

    """Model defining base locations."""

    __tablename__ = 'files_location'

    id = db.Column(db.Integer, primary_key=True)
    """Id of location."""

    uri = db.Column(db.String(), nullable=False)
    """URI of the location."""

    active = db.Column(db.Boolean, nullable=False, default=False)
    """True if the location is available to be used."""

    @classmethod
    def get(cls, loc_id):
        """Fetch a specific location object."""
        return cls.query.filter_by(
            id=loc_id,
            active=True
        ).first()

    @classmethod
    def all(cls, active=True):
        """Return query that fetches all locations."""
        return Location.query.filter_by(
            active=active
        )


class Bucket(db.Model, Timestamp):

    """Model for storing buckets."""

    __tablename__ = 'files_bucket'

    id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4,
    )
    """Bucket identifier."""

    default_location = db.Column(db.Integer, db.ForeignKey(Location.id))

    default_storage_class = db.Column(db.String(1), nullable=False)

    size = db.Column(db.BigInteger, default=0, nullable=False)

    locked = db.Column(db.Boolean, default=False, nullable=False)

    deleted = db.Column(db.Boolean, default=False, nullable=False)

    location = db.relationship(
        'Location',
        backref='files_bucket',
        primaryjoin="Location.id == Bucket.default_location"
    )
    """Location associated with this bucket."""

    def serialize(self):
        """Serialize bucket to dict."""
        return {
            'url': url_for(
                'invenio_files_rest.bucket_api',
                bucket_id=self.id,
                _external=True),
            'id': str(self.id),
            'size': self.size
        }

    @classmethod
    def get(cls, bucket_id):
        """Return a specific bucket object."""
        return cls.query.filter_by(
            id=bucket_id,
            deleted=False
        ).first()

    @classmethod
    def all(cls, limit=1000):
        """Return all buckets."""
        return cls.query.filter_by(
            deleted=False
        ).limit(1000)

    @classmethod
    def delete(cls, bucket_id):
        """Delete bucket.

        :returns: True if the bucket exists and gets deleted.
        """
        bucket = cls.get(bucket_id)
        if bucket:
            bucket.deleted = True
            for obj in Object.get_by_bucket(bucket_id, versions=True).all():
                obj.deleted = True
            return True
        return False


class Object(db.Model, Timestamp):

    """Model for storing objects."""

    __tablename__ = 'files_object'

    bucket_id = db.Column(
        UUIDType,
        db.ForeignKey(Bucket.id),
        primary_key=True, )

    filename = db.Column(
        db.String(255),
        primary_key=True, )

    version_id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4, )

    deleted = db.Column(db.Boolean, default=False, nullable=False)

    location = db.Column(db.String(255), nullable=False)

    storage_class = db.Column(db.String(255), nullable=False)

    size = db.Column(db.BigInteger, default=0, nullable=False)

    checksum = db.Column(db.String(255), nullable=True)

    bucket = db.relationship(
        'Bucket',
        backref='files_object',
        primaryjoin="Bucket.id == Object.bucket_id"
    )

    def serialize(self):
        """Serialize object to dict."""
        return {
            'url': url_for(
                'invenio_files_rest.object_api',
                bucket_id=self.bucket_id,
                filename=self.filename,
                _external=True),
            'version_id': str(self.version_id),
            'size': self.size,
            'checksum': self.checksum,
            'updated': self.updated.isoformat()
        }

    @classmethod
    def get(cls, bucket_id, filename, version_id=None):
        """Fetch a specific file."""
        if version_id:
            return cls.query.filter_by(
                bucket_id=str(bucket_id),
                filename=filename,
                version_id=version_id,
                deleted=False
            ).first()
        else:
            return cls.query.filter_by(
                bucket_id=str(bucket_id),
                filename=filename,
                deleted=False
            ).order_by(desc(Object.updated)).first()

    @classmethod
    def delete(cls, bucket_id, filename):
        """Delete all the versions of a file object in a bucket.

        :returns: True if the object file exists.
        """
        objs = cls.query.filter_by(
            bucket_id=bucket_id,
            filename=filename,
            deleted=False
        ).all()
        if objs:
            for obj in objs:
                obj.deleted = True
            return True
        return False

    @classmethod
    def get_by_bucket(cls, bucket_id, versions=False):
        """Return query that fetches all the objects in a bucket."""
        if versions:
            return cls.query.filter_by(
                bucket_id=bucket_id,
                deleted=False
            )
        else:
            table_object = db.aliased(Object)
            return cls.query.filter(
                cls.bucket_id == bucket_id,
                ~cls.deleted,
                cls.updated == db.session.query(
                    db.func.max(table_object.updated)).filter(
                        ~table_object.deleted,
                        table_object.filename == cls.filename).limit(1)
            )


__all__ = (
    'Location',
    'Bucket',
    'Object',
)
