# SPDX-FileCopyrightText: 2015-2019 CERN.
# SPDX-License-Identifier: MIT

"""Models for Invenio-Files-REST."""

from blinker import Namespace

_signals = Namespace()

file_downloaded = _signals.signal("file-downloaded")
"""File downloaded signal.

Sent when a file is downloaded.
"""

file_uploaded = _signals.signal("file-uploaded")
"""File uploaded signal.

Sent when a file is uploaded.
"""

file_deleted = _signals.signal("file-deleted")
"""File deleted signal.

Sent when a file is deleted.
"""
