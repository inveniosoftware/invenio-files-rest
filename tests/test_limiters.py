# SPDX-FileCopyrightText: 2015-2019 CERN.
# SPDX-License-Identifier: MIT

"""Test limiters."""

import pytest

from invenio_files_rest.limiters import FileSizeLimit


def test_file_size_limit_comparisons():
    """Test FileSizeLimit comparison operators."""
    bigger = FileSizeLimit(100, "big limit")
    smaller = FileSizeLimit(50, "small limit")

    assert bigger > smaller
    assert smaller < bigger
    assert bigger == bigger
    assert bigger == 100
    assert bigger > 50
    assert bigger < 150

    with pytest.raises(NotImplementedError):
        bigger > 90.25
    with pytest.raises(NotImplementedError):
        bigger < 90.25
    with pytest.raises(NotImplementedError):
        bigger == 90.25
