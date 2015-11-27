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
from invenio_db import db
from sqlalchemy_utils.types import UUIDType
from sqlalchemy_utils.models import Timestamp


class Location(db.Model, Timestamp):
    """Model for defining base locations."""

    __tablename__ = 'files_location'

    id = db.Column(db.Integer, primary_key=True, auto_increment=True)
    """Id of location."""

    location = db.Column(db.String(), nullable=False)
    """Define a location."""


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

    locked = db.Column(db.Bool, default=False, nullable=False)


class Object(db.Model, Timestamp):
    """Model for storing objects."""

    __tablename__ = 'files_object'

    bucket_id = db.Column(
        UUIDType,
        db.ForeignKey(Bucket.id),
        primary_key=True, )

    key = db.Column(
        db.String(255),
        primary_key=True, )

    version_id = id = db.Column(
        UUIDType,
        primary_key=True,
        default=uuid.uuid4, )

    deleted = db.Column(db.Bool, default=False, nullable=False)

    location = db.Column(db.String(255), nullable=False)

    storage_class = db.Column(db.String(255), nullable=False)

    size = db.Column(db.BigInteger, default=0, nullable=False)

    checksum = db.Column(db.String(255), nullable=False)


__all__ = (
    'Location',
    'Bucket',
    'Object',
)
