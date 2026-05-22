# SPDX-FileCopyrightText: 2015-2019 CERN.
# SPDX-FileCopyrightText: 2024 Graz University of Technology.
# SPDX-License-Identifier: MIT

"""Files download/upload REST API similar to S3 for Invenio."""

from io import BytesIO


def login_user(client, user):
    """Log in a specified user."""
    with client.session_transaction() as sess:
        sess["_user_id"] = user.id if user else None
        sess["_fresh"] = True


class BadBytesIO(BytesIO):
    """Class for closing the stream for further reading abruptly."""

    def __init__(self, *args, **kwargs):
        """Initialize."""
        self.called = False
        return super(BadBytesIO, self).__init__(*args, **kwargs)

    def readinto(self, b: bytearray = None):
        """Raise error."""
        if self.called:
            raise ValueError("readinto raise")

    def read(self, *args, **kwargs):
        """Fail on second read."""
        if self.called:
            self.close()
        self.called = True
        return super(BadBytesIO, self).read(*args, **kwargs)
