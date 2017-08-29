#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
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

"""Revision message."""

import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '8ae99b034410'
down_revision = 'f741aa746a7d'
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    # table ObjectVersion: modify primary_key
    if op.get_context().dialect.name == 'mysql':
        Fk = 'fk_files_object_bucket_id_files_bucket'
        op.execute(
            'ALTER TABLE files_object '
            'DROP FOREIGN KEY {0}, DROP PRIMARY KEY, '
            'ADD PRIMARY KEY(version_id), '
            'ADD FOREIGN KEY(bucket_id) '
            'REFERENCES files_bucket(id)'.format(Fk))
    else:
        op.drop_constraint('pk_files_object', 'files_object', type_='primary')
        op.create_primary_key(
            'pk_files_object', 'files_object', ['version_id'])
    op.create_unique_constraint(
        'uq_files_object_bucket_id', 'files_object',
        ['bucket_id', 'version_id', 'key'])
    # table ObjectVersionTag: create
    op.create_table(
        'files_objecttags',
        sa.Column(
            'version_id',
            sqlalchemy_utils.types.uuid.UUIDType(),
            nullable=False),
        sa.Column(
            'key',
            sa.Text().with_variant(mysql.VARCHAR(255), 'mysql'),
            nullable=False
        ),
        sa.Column(
            'value',
            sa.Text().with_variant(mysql.VARCHAR(255), 'mysql'),
            nullable=False
        ),
        sa.PrimaryKeyConstraint('version_id', 'key'),
        sa.ForeignKeyConstraint(
            ['version_id'],
            [u'files_object.version_id'],
            ondelete='CASCADE'),
    )


def downgrade():
    """Downgrade database."""
    # table ObjectVersionTag
    op.drop_table('files_objecttags')
    # table ObjectVersion: modify primary_key
    if op.get_context().dialect.name == 'mysql':
        Fk = 'fk_files_object_bucket_id_files_bucket'
        op.execute(
            'ALTER TABLE files_object '
            'DROP INDEX uq_files_object_bucket_id, '
            #  'DROP FOREIGN KEY {0}, '
            'DROP PRIMARY KEY, '
            'ADD PRIMARY KEY(`bucket_id`, `key`, `version_id`)'
            .format(Fk))
    else:
        op.drop_constraint(
            'pk_files_object', 'files_object', type_='primary')
        op.create_primary_key('pk_files_object', 'files_object',
                              ['bucket_id', 'key', 'version_id'])
