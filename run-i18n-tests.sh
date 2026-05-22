#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2023 Graz University of Technology.
# SPDX-License-Identifier: MIT

# Usage:
#   ./run-i18n-tests.sh

python -m setup extract_messages --output-file /dev/null
