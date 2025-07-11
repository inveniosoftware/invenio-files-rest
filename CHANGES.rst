..
    This file is part of Invenio.
    Copyright (C) 2015-2024 CERN.
    Copyright (C) 2024 Graz University of Technology.

    Invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.



Changes
=======

Version v3.2.0 (released 2025-06-06)

- fix: always send Accept-Ranges header if ranges are enabled
    * The current Werkzeug version only sends the `Accept-Ranges`
      header when a `Range` header is provided by the caller. As
      a result, the caller cannot determine range support
      beforehand. This change ensures the header is always sent
      when ranges are enabled.
- fix: pass werkzeug exceptions, such as RequestedRangeNotSatisfiable
    * Werkzeug performs Range header validation and raises an
      exception (HTTP 416) when it is invalid. We pass the exception
      to caller instead of raising generic HTTP 500 (StorageError)

Version v3.1.0 (released 2025-06-05)

- Adds range request support for accessing files (#321)
    * Adds range request support for accessing files, delegated to werkzeug
- fix(deps): Use sqlalchemy 2.0 compatible query syntax
- fix: skip non-readable files on checksum verification
    * FileInstance can be marked as non-readable.
      Currently, even those instances are verified,
      which might raise an exception. This commit fixes
      that by adding readable=True to the default filter
      and changing the way the total size is computed
      to use this filter
- fix: setuptools require underscores instead of dashes

Version 3.0.0 (release 2024-12-09)

- filename: replace encoding/decoding
- fix: alembic assert error
- fix: max content type
- fix: werkzeug changed raise handling for tests
- fix: docs reference target not found
- fix: filename is marked as byte
- tests: apply changes for sqlalchemy>=2.0
- setup: bump invenio dependencies

Version 2.2.4 (release 2024-12-04)

- workflows: add translation flag for publishing

Version 2.2.3 (release 2024-11-28)

- setup: pin dependencies

Version 2.2.2 (release 2024-11-05)

- fix: LegacyAPIWarning of sqlalchemy
- global: move to db.session.query syntax
- fix: compatibility with werkzeug >= 3.0.0

Version 2.2.1 (release 2024-09-19)

- fix: downloading for some weird filenames
- i18n: push translations

Version 2.2.0 (release 2024-01-18)

- Bump for skipping yanked v2.1.0 release

Version 2.1.0 (release 2024-01-18)

- models: add copy_from method to ObjectVersion

Version 2.0.3 (release 2023-12-14)

- files: avoid creating directories while opening files for reading

Version 2.0.2 (release 2023-11-01)

- pyfs: fix computing parent folder path on delete action

Version 2.0.1 (release 2023-10-02)

- models: handle bucket quota update on delete
- models: update bucket size on object version delete
- storage: pyfs handle file upload interruption

Version 2.0.0 (release 2023-08-15)

- models: `Bucket.sync` method now returns a tuple of (bucket, list_of_changes) instead
  of bucket. That is a breaking change if you were consuming the return value.

Version 1.5.0 (release 2023-03-02)

- remove deprecated flask-babelex dependency and imports
- install invenio-i18n

Version 1.4.0 (release 2023-01-24)

- tasks: add orphan cleaning celery task

Version 1.3.3 (release 2022-04-06)

- Fix Flask v2.1 issues.
- Refactor dependencies to respect Invenio dependency strategy and remove
  pin on Flask-Login.

Version 1.3.2 (release 2022-02-14)

- Fix deprecation warnings from marshmallow.

Version 1.3.1 (release 2022-01-31)

- Fix a race-condition by enforcing integrity constraint on is head. An issue
  was detected that could produce two head versions of the same object. This
  fix adds a partial index in PostgreSQL to ensure that the race condition
  throws an integrity error when trying to commit. Partial indexes is only
  available on PostgreSQL.

- Fix for the sync method and signals signature.

Version 1.3.0 (released 2021-10-18)

- Bumped minimum PyFilesystem dependency to v2. Note that, setuptools v58+ have
  dropped support for use2to3, thus PyFilesystem v0.5.5 no longer installs on
  Python 3 when using setuptools v58 or greater.

Version 1.2.0 (released 2020-05-14)

- Adds optional file streaming using a reverse proxy (e.g. NGINX).

Version 1.1.1 (released 2020-02-24)

- Makes cli `location` command backwards compatible.

Version 1.1.0 (released 2020-01-19)

- Moves *location* from command to group
- Allows listing locations via de CLI
- Allows setting a location as *default*
- Get by name on the `Location` object returns None when not found instead of raising an exception
- Other bug fixes

Version 1.0.6 (released 2019-11-22)

- Bump version and add to installation requirements invenio-celery
- Add documentation of module usage
- Remove storage_class parameter from Bucket create when POST to Location resource

Version 1.0.5 (released 2019-11-21)

- Add signals for deletion and upload of files

Version 1.0.4 (released 2019-11-20)

- Fix `StorageError` type returned

Version 1.0.3 (released 2019-11-15)

- Increase invenio-rest version to support Marshmallow 2 and 3 migration

Version 1.0.2 (released 2019-11-14)

- Adds optional serializer_mapping and view_name in `json_serializer` method

Version 1.0.1 (released 2019-08-01)

- Adds support for marshmallow 2 and 3.

Version 1.0.0 (released 2019-07-22)

- Initial public release.
