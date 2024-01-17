#
# This file is part of Invenio.
# Copyright (C) 2023 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Add indexes."""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e172c837b036"
down_revision = "a29271fd78f8"
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    metadata = sa.MetaData()
    table = sa.Table("files_object", metadata, autoload_with=op.get_bind())

    # We need to do this checks as this index was being wrongly dropped by another alembic recipe in another module
    if "ix_uq_partial_files_object_is_head" in [index.name for index in table.indexes]:
        op.drop_index("ix_uq_partial_files_object_is_head", table_name="files_object")

    op.create_index(
        "ix_files_multipartobject_bucket_id",
        "files_multipartobject",
        ["bucket_id"],
        unique=False,
    )
    op.create_index(
        "ix_files_objecttags_version_id",
        "files_objecttags",
        ["version_id"],
        unique=False,
    )
    op.create_index(
        "ix_files_object_bucket_id", "files_object", ["bucket_id"], unique=False
    )
    op.create_index(
        "ix_files_buckettags_bucket_id", "files_buckettags", ["bucket_id"], unique=False
    )


def downgrade():
    """Downgrade database."""
    op.create_index(
        "ix_uq_partial_files_object_is_head",
        "files_object",
        ["bucket_id", "key"],
        unique=False,
    )
    op.drop_index(
        "ix_files_multipartobject_bucket_id", table_name="files_multipartobject"
    )
    op.drop_index("ix_files_objecttags_version_id", table_name="files_objecttags")
    op.drop_index("ix_files_object_bucket_id", table_name="files_object")
    op.drop_index("ix_files_buckettags_bucket_id", table_name="files_buckettags")
