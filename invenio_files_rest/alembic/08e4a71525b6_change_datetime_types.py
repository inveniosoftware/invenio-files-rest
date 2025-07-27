#
# This file is part of Invenio.
# Copyright (C) 2023-2025 CERN.
# Copyright (C) 2026 Graz University of Technology.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Alter datetime columns to utc aware datetime columns."""

from invenio_db.utils import (
    update_table_columns_column_type_to_datetime,
    update_table_columns_column_type_to_utc_datetime,
)

# revision identifiers, used by Alembic.
revision = "08e4a71525b6"
down_revision = "e172c837b036"
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    for table_name in [
        "files_location",
        "files_bucket",
        "files_files",
        "files_object",
        "files_multipartobject",
        "files_multipartobject_part",
    ]:
        update_table_columns_column_type_to_utc_datetime(table_name, "created")
        update_table_columns_column_type_to_utc_datetime(table_name, "updated")
    update_table_columns_column_type_to_utc_datetime("files_files", "last_check_at")


def downgrade():
    """Downgrade database."""
    for table_name in [
        "files_location",
        "files_bucket",
        "files_files",
        "files_object",
        "files_multipartobject",
        "files_multipartobject_part",
    ]:
        update_table_columns_column_type_to_datetime(table_name, "created")
        update_table_columns_column_type_to_datetime(table_name, "updated")
    update_table_columns_column_type_to_datetime("files_files", "last_check_at")
