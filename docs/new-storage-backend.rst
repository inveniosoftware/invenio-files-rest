..
    This file is part of Invenio.
    Copyright (C) 2020 Cottage Labs LLP

    Invenio is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.


Developing a new storage backend
================================

A storage backend should subclass ``invenio_files_rest.storage.StorageBackend`` and should minimally implement the
``open()``, ``delete()``, ``_initialize(size)``, ``get_save_stream()`` and ``update_stream(seek)`` methods. You should
register the backend with an entry point in your ``setup.py``:

.. code-block:: python

   setup(
       ...,
       entry_points={
           ...,
           'invenio_files_rest.storage': [
               'mybackend = mypackage.storage:MyStorageBackend',
           ],
           ...
       },
       ...
   )

Implementation
--------------

The base class handles reporting progress, file size limits and checksumming.

Here's an example implementation of a storage backend that stores files remotely over HTTP with no authentication.

.. code-block:: python

   import contextlib
   import httplib
   import urllib
   import urllib.parse

   from invenio_files_rest.storage import StorageBackend


   class StorageBackend(StorageBackend):
       def open(self):
           return contextlib.closing(
               urllib.urlopen('GET', self.uri)
           )

       def _initialize(self, size=0):
           # Allocate space for the file. You can use `self.uri` as a suggested location, or return
           # a new location as e.g. `{"uri": the_new_uri}`.
           urllib.urlopen('POST', self.uri, headers={'X-Expected-Size': str(size)})
           return {}

       @contextlib.contextmanager
       def get_save_stream(self):
           # This should be a context manager (i.e. something that can be used in a `with` statement)
           # which closes the file when exiting the context manager and performs any clear-up if
           # an error occurs.
           parsed_uri = urllib.parse.urlparse(self.uri)
           # Assume the URI is HTTP, not HTTPS, and doesn't have a port or querystring
           conn = httplib.HTTPConnection(parsed_uri.netloc)

           conn.putrequest('PUT', parsed_uri.path)
           conn.endheaders()

           # HTTPConnections have a `send` method, whereas a file-like object should have `write`
           conn.write = conn.send

           try:
               yield conn.send
               response = conn.getresponse()
               if not 200 <= response.status < 300:
                   raise IOError("HTTP error")
           finally:
               conn.close()


Checksumming
------------

The base class performs checksumming by default, using the ``checksum_hash_name`` class or instance attribute as
the hashlib hashing function to use. If your underlying storage system provides checksumming functionality you can set
this to ``None`` and override ``checksum()``:

.. code-block:: python

   class RemoteChecksumStorageBackend(StorageBackend):
       checksum_hash_name = None

       def checksum(self, chunk_size=None):
           checksum = urllib.urlopen(self.uri + '?checksum=sha256').read()
           return f'sha256:{checksum}'

