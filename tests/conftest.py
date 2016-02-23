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
import tempfile

import pytest
from flask import Flask
from flask_cli import FlaskCLI
from invenio_db import db as db_
from invenio_db import InvenioDB
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_files_rest import InvenioFilesREST
from invenio_files_rest.models import Location
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
    )
    FlaskCLI(app_)
    InvenioDB(app_)
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
def dummy_location(request, db):
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
