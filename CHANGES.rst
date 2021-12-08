..
    This file is part of Invenio.
    Copyright (C) 2015-2019 CERN.

    Invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.



Changes
=======

Version 1.0.7 (released 2021-12-08)

- Backport fix in `models.Bucket.sync` method
- Backport fix in signals send

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
