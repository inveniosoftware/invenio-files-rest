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

import pytest
from flask import Flask
from flask_babelex import Babel
from flask_celeryext import FlaskCeleryExt
from flask_cli import FlaskCLI
from flask_menu import Menu
from invenio_access import InvenioAccess
from invenio_access.models import ActionUsers
from invenio_accounts import InvenioAccounts
from invenio_accounts.testutils import create_test_user
from invenio_accounts.views import blueprint as accounts_blueprint
from invenio_db import db as db_
from invenio_db import InvenioDB
from six import BytesIO, b
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_files_rest import InvenioFilesREST
from invenio_files_rest.models import Bucket, Location, ObjectVersion
from invenio_files_rest.permissions import objects_create, \
    objects_delete_all, objects_read_all, objects_update_all
from invenio_files_rest.views import blueprint


@pytest.fixture(scope='session', autouse=True)
def base_app():
    """Flask application fixture."""
    app_ = Flask('testapp')
    app_.config.update(
        # CELERY_ALWAYS_EAGER=True,
        # CELERY_RESULT_BACKEND="cache",
        # CELERY_CACHE_BACKEND="memory",
        # CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
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
    FlaskCeleryExt(app_)
    InvenioDB(app_)
    Babel(app_)
    Menu(app_)

    return app_


@pytest.yield_fixture(scope='session', autouse=True)
def app(base_app):
    """Flask application fixture."""
    InvenioAccounts(base_app)
    InvenioAccess(base_app)
    base_app.register_blueprint(accounts_blueprint)
    InvenioFilesREST(base_app)
    base_app.register_blueprint(blueprint)

    with base_app.app_context():
        yield base_app


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
        uri=tmppath,
        default=True
    )
    db.session.add(loc)
    db.session.commit()

    yield loc

    shutil.rmtree(tmppath)


@pytest.yield_fixture()
def extra_location(db):
    """File system location."""
    tmppath = tempfile.mkdtemp()

    loc = Location(
        name='extra',
        uri=tmppath,
        default=False
    )
    db.session.add(loc)
    db.session.commit()

    yield loc

    shutil.rmtree(tmppath)


@pytest.fixture()
def bucket(db, dummy_location):
    """File system location."""
    b1 = Bucket.create()
    db.session.commit()
    return b1


@pytest.yield_fixture()
def objects(db, bucket):
    """File system location."""
    data_bytes = b('license file')
    obj1 = ObjectVersion.create(
        bucket, 'LICENSE', stream=BytesIO(data_bytes),
        size=len(data_bytes)
    )
    data_bytes2 = b('readme file')
    obj2 = ObjectVersion.create(
        bucket, 'README.rst', stream=BytesIO(data_bytes2),
        size=len(data_bytes)
    )
    db.session.commit()

    yield [obj1, obj2]


@pytest.fixture()
def users_data(db):
    """User data fixture."""
    return [
        dict(email='user1@invenio-software.org', password='pass1'),
        dict(email='user2@invenio-software.org', password='pass1'),
    ]


@pytest.fixture()
def users(db, users_data):
    """Create test users."""
    return [
        create_test_user(active=True, **users_data[0]),
        create_test_user(active=True, **users_data[1]),
    ]


@pytest.yield_fixture()
def permissions(db, users, bucket):
    """Bucket permissions."""
    # Give permissions to user 'user1', but not to 'user2'
    perms = [objects_create, objects_read_all, objects_update_all,
             objects_delete_all]

    for perm in perms:
        au = ActionUsers(action=perm.value,
                         argument=str(bucket.id),
                         user=users[0])
        db.session.add(au)
    db.session.commit()

    yield None
