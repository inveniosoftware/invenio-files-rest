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


"""Pytest configuration."""

from __future__ import absolute_import, print_function

import os
import shutil
import tempfile
from hashlib import md5
from os.path import dirname, join

import pytest
from flask import Flask
from flask_babelex import Babel
from flask_cli import FlaskCLI
from flask_menu import Menu
from invenio_access import InvenioAccess
from invenio_access.models import ActionUsers
from invenio_accounts import InvenioAccounts
from invenio_accounts.testutils import create_test_user
from invenio_accounts.views import blueprint as accounts_blueprint
from invenio_db import db as db_
from invenio_db import InvenioDB
from six import BytesIO
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_files_rest import InvenioFilesREST
from invenio_files_rest.models import Bucket, Location, ObjectVersion
from invenio_files_rest.permissions import objects_create, \
    objects_delete_all, objects_read_all, objects_update_all
from invenio_files_rest.views import blueprint


@pytest.yield_fixture(scope='session', autouse=True)
def app(request):
    """Flask application fixture."""
    app_ = Flask('testapp')
    app_.config.update(
        TESTING=True,
        SQLALCHEMY_TRACK_MODIFICATIONS=True,
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI',
            'sqlite:///:memory:'),
        WTF_CSRF_ENABLED=False,
        SERVER_NAME='invenio.org',
        SECURITY_PASSWORD_SALT='TEST_SECURITY_PASSWORD_SALT',
        SECRET_KEY='TEST_SECRET_KEY',
    )
    FlaskCLI(app_)
    InvenioDB(app_)
    Babel(app_)
    Menu(app_)
    InvenioAccounts(app_)
    InvenioAccess(app_)
    app_.register_blueprint(accounts_blueprint)
    InvenioFilesREST(app_)
    app_.register_blueprint(blueprint)

    with app_.app_context():
        yield app_


@pytest.yield_fixture()
def db(app):
    """Setup database."""
    if not database_exists(str(db_.engine.url)):
        create_database(str(db_.engine.url))
    db_.create_all()
    yield db_
    db_.session.remove()
    db_.drop_all()


@pytest.yield_fixture()
def dummy_location(db):
    """File system location."""
    tmppath = tempfile.mkdtemp()

    loc = Location(
        name='testloc',
        uri="file://{0}".format(tmppath),
        default=True
    )
    db.session.add(loc)
    db.session.commit()

    yield loc

    shutil.rmtree(tmppath)


@pytest.yield_fixture()
def objects(dummy_location):
    """File system location."""
    srcroot = dirname(dirname(__file__))

    # Bucket 1
    b1 = Bucket.create(dummy_location)
    objects = []
    for f in ['README.rst', 'LICENSE']:
        with open(join(srcroot, f), 'rb') as fp:
            objects.append(ObjectVersion.create(b1, f, stream=fp))

    yield objects


@pytest.yield_fixture()
def test_data(dummy_location, db):
    """Create some test data."""
    # Create the bucket with a single file
    buc1 = Bucket.create()
    key1 = "key1"  # Object key
    stream1 = b'contents1'  # Contents of the data stream
    o1 = ObjectVersion.create(buc1, key1, stream=BytesIO(stream1))
    md5_1 = md5(BytesIO(stream1).read()).hexdigest()

    # Create the test users
    u1_data = dict(email='user1@invenio-software.org', password='pass1')
    u2_data = dict(email='user2@invenio-software.org', password='pass1')
    u1 = create_test_user(active=True, **u1_data)  # User with permissions
    u2 = create_test_user(active=True, **u2_data)  # User w/o permissions

    # Give permissions to user 'user1', but not to 'user2'
    perms = [objects_create, objects_read_all, objects_update_all,
             objects_delete_all]
    for perm in perms:
        au = ActionUsers(action=perm.value,
                         argument=str(buc1.id),
                         user=u1)
        db.session.add(au)
    db.session.commit()

    data = {'bucket': buc1,
            'files': (o1, ),  # List of files
            'files_streams': (stream1, ),  # List of files contents
            'files_md5': (md5_1, ),  # List of files md5
            'user1': u1,  # User object
            'user1_data': u1_data,  # User data (used for login)
            'user2': u2,
            'user2_data': u2_data, }

    yield data
