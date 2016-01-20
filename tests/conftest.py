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


"""Pytest configuration."""

from __future__ import absolute_import, print_function

import os
import shutil

import pytest
from flask import Flask
from flask_cli import FlaskCLI
from invenio_db import db as db_
from invenio_db import InvenioDB

from invenio_files_rest import InvenioFilesREST
from invenio_files_rest.models import Location

TEST_FS = '/tmp/_test_invenio_files_rest'


@pytest.yield_fixture(scope='session', autouse=True)
def app(request):
    """Flask application fixture."""
    app_ = Flask('testapp')
    app_.config.update(
        TESTING=True
    )
    InvenioFilesREST(app_)

    app_.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'
    )
    FlaskCLI(app_)
    InvenioDB(app_)

    os.mkdir(TEST_FS)

    def fin():
        shutil.rmtree('/tmp/_test_invenio_files_rest')

    request.addfinalizer(fin)

    with app_.app_context():
        yield app_


@pytest.yield_fixture(scope='session')
def database(app):
    """Ensure that the database schema is created."""
    db_.create_all()
    yield db_
    db_.session.remove()


@pytest.yield_fixture
def db(database, monkeypatch):
    """Provide database access and ensure changes do not persist."""
    # Prevent database/session modifications
    monkeypatch.setattr(database.session, 'commit', database.session.flush)
    monkeypatch.setattr(database.session, 'remove', lambda: None)
    yield database
    database.session.rollback()
    database.session.remove()


@pytest.fixture
def dummy_location(db):
    loc = Location(
        uri="file://{}".format(TEST_FS),
        active=True
    )
    db.session.add(loc)
    db.session.commit()
    return loc
