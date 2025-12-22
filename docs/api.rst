..
    This file is part of Invenio.
    Copyright (C) 2015-2019 CERN.

    Invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.



API Docs
========

.. automodule:: invenio_files_rest.ext
   :members:

Models
------

.. automodule:: invenio_files_rest.models
   :members:

Storage
-------

.. automodule:: invenio_files_rest.storage
   :members:

Signals
-------

.. automodule:: invenio_files_rest.signals
   :members:

File streaming
--------------

.. automodule:: invenio_files_rest.helpers
   :members:

Tasks
-----

.. automodule:: invenio_files_rest.tasks
   :members:
   :undoc-members:
    .. for `undoc-members`, see https://github.com/celery/celery/pull/5135

   .. autotask:: verify_checksum(file_id, pessimistic=False, chunk_size=None, throws=True, checksum_kwargs=None)
   .. autotask:: schedule_checksum_verification(frequency=None,batch_interval=None,max_count=None,max_size=None,files_query=None,checksum_kwargs=None)
   .. autotask:: migrate_file(src_id, location_name, post_fixity_check=False)
   .. autotask:: remove_file_data(file_id, silent=True, force=False)
   .. autotask:: merge_multipartobject(upload_id, version_id=None)
   .. autotask:: remove_expired_multipartobjects()
   .. autotask:: clear_orphaned_files(force_delete_check=lambda file_instance: False, limit=1000)
   .. 
      note: Sphinx in versions >=6.0.0 has issues with celery decorators and does not
      document the functions properly. Hence, the functions are documented manually
      below until Sphinx fixes the issue


Exceptions
----------

.. automodule:: invenio_files_rest.errors
   :members:

Limiters
--------

.. automodule:: invenio_files_rest.limiters
   :members:

Permissions
-----------

.. automodule:: invenio_files_rest.permissions
   :members:

Views
-----

.. automodule:: invenio_files_rest.views
   :members:

Form parser
-----------

.. automodule:: invenio_files_rest.formparser
   :members:
