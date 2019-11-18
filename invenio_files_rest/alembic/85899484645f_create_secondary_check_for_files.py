# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Create secondary check columns for files_files tables."""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '85899484645f'
down_revision = 'f741aa746a7d'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database."""
    op.add_column(
        'files_files',
        sa.Column('last_secondary_check_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'files_files',
        sa.Column(
            'last_secondary_check',
            sa.Boolean(name='last_secondary_check'),
            nullable='true'
        )
    )
    op.execute("UPDATE files_files SET last_secondary_check = true")
    op.alter_column(
        'files_files',
        'last_secondary_check',
        existing_type=sa.Boolean(name='last_secondary_check'),
        nullable='false'
    )


def downgrade():
    """Downgrade database."""
    op.drop_column(
        'files_files',
        'last_secondary_check_at',
        existing_type=sa.DateTime(),
        nullable='true')
    op.drop_column(
        'files_files',
        'last_secondary_check',
        existing_type=sa.Boolean(name='last_secondary_check'),
        nullable='false'
    )
