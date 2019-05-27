# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


r"""REST API for Files.

Invenio-Files-REST provides configurable REST APIs for uploading, serving,
downloading and deleting files. It works as a standalone module or in
combination with `Invenio-Records <https://invenio-records.readthedocs.io>`_
through the
`Invenio-Records-Files <https://invenio-records-files.readthedocs.io>`_
integration.

The module can be configured with different storage backends, and provides
features such as:

- A robust REST API.
- Configurable storage backends with the ability to build your very own.
- Highly customizable access-control.
- Secure file handling.
- Integrity checking mechanism.
- Support for large file uploads and multipart upload.
- Signals for system events.

The REST API follows best practices and supports, e.g.:

- Content negotiation and links headers.
- Cache control via ETags and Last-Modified headers.
- Optimistic concurrency control via ETags.
- Rate-limiting, Cross-Origin Resource Sharing, and various security headers.


Initialization
--------------

First, let's create a Flask application:

>>> from flask import Flask
>>> app = Flask('myapp')

And add some configuration, mainly for storage:

>>> app.config['BROKER_URL'] = 'redis://'
>>> app.config['CELERY_RESULT_BACKEND'] = 'redis://'
>>> app.config['DATADIR'] = 'data'
>>> app.config['FILES_REST_MULTIPART_CHUNKSIZE_MIN'] = 4
>>> app.config['REST_ENABLE_CORS'] = True
>>> app.config['SECRET_KEY'] = 'CHANGEME'
>>> app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
>>> app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

>>> allow_all = lambda *args, **kwargs: \
... type('Allow', (), {'can': lambda self: True})()
>>> app.config['FILES_REST_PERMISSION_FACTORY'] = allow_all

Now let's initialize all required Invenio extensions:

>>> import shutil
>>> from os import makedirs
>>> from os.path import dirname, exists
>>> from pprint import pprint
>>> import json

>>> from flask_babelex import Babel
>>> from flask_menu import Menu
>>> from invenio_db import InvenioDB, db
>>> from invenio_rest import InvenioREST
>>> from invenio_admin import InvenioAdmin
>>> from invenio_accounts import InvenioAccounts
>>> from invenio_access import InvenioAccess
>>> from invenio_accounts.views import blueprint as accounts_blueprint
>>> from invenio_celery import InvenioCelery
>>> from invenio_files_rest import InvenioFilesREST
>>> from invenio_files_rest.views import blueprint
>>> from invenio_files_rest.models import Location

>>> ext_babel = Babel(app)
>>> ext_menu = Menu(app)
>>> ext_db = InvenioDB(app)
>>> ext_rest = InvenioREST(app)
>>> ext_admin = InvenioAdmin(app)
>>> ext_accounts = InvenioAccounts(app)
>>> ext_access = InvenioAccess(app)

Finally, let's initialize InvenioFilesREST, register the blueprints
and push a Flask application context:

>>> ext_rest = InvenioFilesREST(app)

>>> app.register_blueprint(accounts_blueprint)
>>> app.register_blueprint(blueprint)

>>> app.app_context().push()

Let's create the database and tables, using an in-memory SQLite database:

>>> db.create_all()

To start storing file, let's create a location in a temporary directory:

>>> srcroot = dirname(dirname('app.py'))
>>> d = app.config['DATADIR']
>>> if exists(d): shutil.rmtree(d)
>>> makedirs(d)
>>> loc = Location(name='local', uri=d, default=True)
>>> db.session.add(loc)
>>> db.session.commit()

Now let's create a bucket:

>>> res = app.test_client().post('/files')

And see the response containing the id of the bucket:

>>> json_response = json.loads(res.get_data().decode("utf-8"))


REST API
--------

This part of the documentation will show you how to get started in using the
REST API of Invenio-Files-REST.

The REST API allows you to create buckets and perform CRUD operations on files.
You can use query parameters in order to perform these operations.

.. note::
    The REST APIs endpoint is registered by the Invenio API instance. This
    means that the endpoint is reachable with the path ``/api/files/``.


Available methods and endpoints
-------------------------------

The following is a brief overview of the methods the REST API provides.

By default, the URL prefix for the REST API is under /files.


Bucket Endpoints
----------------

Create
^^^^^^

**Description**
    Creates a bucket in the default location.

**Parameters**

.. code-block:: console

    No parameters.

**Request**

.. code-block:: console

    POST /files

**Response**

.. code-block:: json

    {
        "max_file_size": null,
        "updated": "2019-05-24T08:59:40.356202+00:00",
        "locked": false,
        "links": {
            "self": "http://localhost:5000/files/
                     436ac279-d85f-4500-8217-295804c14794",
            "uploads": "http://localhost:5000/files/
                        436ac279-d85f-4500-8217-295804c14794?uploads",
            "versions": "http://localhost:5000/files/
                         436ac279-d85f-4500-8217-295804c14794?versions"
        },
        "created": "2019-05-24T08:59:40.356195+00:00",
        "quota_size": null,
        "id": "436ac279-d85f-4500-8217-295804c14794",
        "size": 0
    }


Check existance
^^^^^^^^^^^^^^^

**Description**
    Checks if a bucket exists.

**Parameters**

.. code-block:: console

    No parameters.

**Request**

.. code-block:: console

    HEAD /files/<bucket_id>

**Response**

.. code-block:: console

    Status: 200 OK

**Errors**

.. code-block:: console

    Status: 404 NOT FOUND


List files
^^^^^^^^^^

**Description**
    Returns list of all of the files in the specified bucket.

**Parameters**

.. code-block:: console

    No parameters

**Request**

.. code-block:: console

    GET /files/<bucket_id>

**Response**

Example with no files in the bucket:

.. code-block:: json

    {
        "max_file_size": null,
        "updated": "2019-05-24T08:59:40.356202+00:00",
        "locked": false,
        "links": {
            "self": "http://localhost:5000/files/
                     436ac279-d85f-4500-8217-295804c14794",
            "uploads": "http://localhost:5000/files/
                        436ac279-d85f-4500-8217-295804c14794?uploads",
            "versions": "http://localhost:5000/files/
                         436ac279-d85f-4500-8217-295804c14794?versions"
        },
        "created": "2019-05-24T08:59:40.356195+00:00",
        "quota_size": null,
        "id": "436ac279-d85f-4500-8217-295804c14794",
        "contents": [],
        "size": 0
    }

Example with one file in the bucket:

.. code-block:: json

    {
        "max_file_size": null,
        "updated": "2019-05-24T09:20:36.361338+00:00",
        "locked": false,
        "links": {
            "self": "http://localhost:5000/files/
                     436ac279-d85f-4500-8217-295804c14794",
            "uploads": "http://localhost:5000/files/
                        436ac279-d85f-4500-8217-295804c14794?uploads",
            "versions": "http://localhost:5000/files/
                         436ac279-d85f-4500-8217-295804c14794?versions"
        },
        "created": "2019-05-24T08:59:40.356195+00:00",
        "quota_size": null,
        "id": "436ac279-d85f-4500-8217-295804c14794",
        "contents": [
            {
                "mimetype": "text/plain",
                "updated": "2019-05-24T09:20:36.344541+00:00",
                "links": {
                    "self": "http://localhost:5000/files/
                             436ac279-d85f-4500-8217-295804c14794/example.txt",
                    "version": "http://localhost:5000/files/
                                436ac279-d85f-4500-8217-295804c14794/example.txt?
                                versionId=39075b38-b354-4ce9-bd36-2425495e6a7a",
                    "uploads": "http://localhost:5000/files/
                                436ac279-d85f-4500-8217-295804c14794/example.txt?
                                uploads"
                },
                "is_head": true,
                "tags": {},
                "checksum": "md5:2cad20c19a8eb9bb11a9f76527aec9bc",
                "created": "2019-05-24T09:20:36.341621+00:00",
                "version_id": "39075b38-b354-4ce9-bd36-2425495e6a7a",
                "delete_marker": false,
                "key": "example.txt",
                "size": 12
            }
        ],
        "size": 12
    }

**Errors**

.. code-block:: json

    {
       "message":"Bucket does not exist.",
       "status":404
    }


Working with files:
-------------------

Upload files
^^^^^^^^^^^^

**Description**
    Uploads a file.

**Parameters**

.. code-block:: console

    binary: <file>

**Request**

.. code-block:: console

    PUT /files/<bucket_id>/<file_name>

**Response**

.. code-block:: json

    {
        "mimetype": "text/plain",
        "updated": "2019-05-24T09:20:36.344541+00:00",
        "links": {
            "self": "http://localhost:5000/files/
                     436ac279-d85f-4500-8217-295804c14794/example.txt",
            "version": "http://localhost:5000/files/
                        436ac279-d85f-4500-8217-295804c14794/example.txt?
                        versionId=39075b38-b354-4ce9-bd36-2425495e6a7a",
            "uploads": "http://localhost:5000/files/
                       436ac279-d85f-4500-8217-295804c14794/example.txt?uploads"
        },
        "is_head": true,
        "tags": {},
        "checksum": "md5:2cad20c19a8eb9bb11a9f76527aec9bc",
        "created": "2019-05-24T09:20:36.341621+00:00",
        "version_id": "39075b38-b354-4ce9-bd36-2425495e6a7a",
        "delete_marker": false,
        "key": "example.txt",
        "size": 12
    }


List file versions
^^^^^^^^^^^^^^^^^^

**Description**
    Returns a list of all versions of all files in the bucket.

**Parameters**

.. code-block:: console

    No parameters.

**Request**

.. code-block:: console

    GET /files/<bucket_id>?versions

**Response**

Example with two files (one with two versions):

.. code-block:: json

    {
        "max_file_size": null,
        "updated": "2019-05-24T10:08:34.174650+00:00",
        "locked": false,
        "links": {
            "self": "http://localhost:5000/files/
                     436ac279-d85f-4500-8217-295804c14794",
            "uploads": "http://localhost:5000/files/
                        436ac279-d85f-4500-8217-295804c14794?uploads",
            "versions": "http://localhost:5000/files/4
                         36ac279-d85f-4500-8217-295804c14794?versions"
        },
        "created": "2019-05-24T08:59:40.356195+00:00",
        "quota_size": null,
        "id": "436ac279-d85f-4500-8217-295804c14794",
        "contents": [
            {
                "mimetype": "text/plain",
                "updated": "2019-05-24T09:58:11.907546+00:00",
                "links": {
                    "self": "http://localhost:5000/files/
                             436ac279-d85f-4500-8217-295804c14794/example.txt",
                    "version": "http://localhost:5000/files/
                               436ac279-d85f-4500-8217-295804c14794/example.txt?
                               versionId=8d17d5ff-65c8-4339-ae83-4d4527f34fe7",
                    "uploads": "http://localhost:5000/files/
                               436ac279-d85f-4500-8217-295804c14794/example.txt?
                               uploads"
                },
                "is_head": true,
                "tags": {},
                "checksum": "md5:e7e63425ce6f05c796d05adb6b5f94be",
                "created": "2019-05-24T09:58:11.904366+00:00",
                "version_id": "8d17d5ff-65c8-4339-ae83-4d4527f34fe7",
                "delete_marker": false,
                "key": "example.txt",
                "size": 15
            },
            {
                "mimetype": "text/plain",
                "updated": "2019-05-24T09:58:11.903395+00:00",
                "links": {
                    "self": "http://localhost:5000/files/
                            436ac279-d85f-4500-8217-295804c14794/example.txt?
                            versionId=39075b38-b354-4ce9-bd36-2425495e6a7a",
                    "version": "http://localhost:5000/files/
                               436ac279-d85f-4500-8217-295804c14794/example.txt?
                               versionId=39075b38-b354-4ce9-bd36-2425495e6a7a"
                },
                "is_head": false,
                "tags": {},
                "checksum": "md5:2cad20c19a8eb9bb11a9f76527aec9bc",
                "created": "2019-05-24T09:20:36.341621+00:00",
                "version_id": "39075b38-b354-4ce9-bd36-2425495e6a7a",
                "delete_marker": false,
                "key": "example.txt",
                "size": 12
            },
            {
                "mimetype": "text/plain",
                "updated": "2019-05-24T10:08:34.172575+00:00",
                "links": {
                    "self": "http://localhost:5000/files/
                             436ac279-d85f-4500-8217-295804c14794/foo.txt",
                    "version": "http://localhost:5000/files/
                                436ac279-d85f-4500-8217-295804c14794/foo.txt?
                                versionId=ca1b9724-cc29-428c-a5d4-b06e1694eb14",
                    "uploads": "http://localhost:5000/files/
                                436ac279-d85f-4500-8217-295804c14794/foo.txt?
                                uploads"
                },
                "is_head": true,
                "tags": {},
                "checksum": "md5:ff702f10bebfa2f1508deb475ded2d65",
                "created": "2019-05-24T10:08:34.170827+00:00",
                "version_id": "ca1b9724-cc29-428c-a5d4-b06e1694eb14",
                "delete_marker": false,
                "key": "foo.txt",
                "size": 7
            }
        ],
        "size": 34
    }


Download file
^^^^^^^^^^^^^

**Description**
    Downloads a file.

**Parameters**

.. code-block:: console

    No parameters

**Request**

.. code-block:: console

    GET /files/<bucket_id>/<file_name>

**Response**

.. code-block:: console

    File contents

**Errors**

.. code-block:: json

    {
        "message": "Object does not exists.",
        "status": 404
    }


Delete file version
^^^^^^^^^^^^^^^^^^^

**Description**
    Permanently erases the object version.

**Parameters**

.. code-block:: console

    No parameters

**Request**

.. code-block:: console

    DELETE /files/<bucket_id>/<file_name>?versionId=<version_id>

**Response**

.. code-block:: console

    Status: 204 NO CONTENT

**Errors**

.. code-block:: json

    {
       "message":"Object does not exists.",
       "status":404
    }


Delete file
^^^^^^^^^^^

**Description**
    Marks whole file as deleted.

**Parameters**

.. code-block:: console

    No parameters

**Request**

.. code-block:: console

    DELETE /files/<bucket_id>/<file_name>

**Response**

.. code-block:: console

    Status: 204 NO CONTENT

**Errors**

.. code-block:: json

    {
       "message":"Object does not exists.",
       "status":404
    }


Working with multipart files:
-----------------------------

Initiate multipart upload
^^^^^^^^^^^^^^^^^^^^^^^^^

**Description**
    Initiates a multipart upload.

**Parameters**

.. code-block:: console

    No parameters

**Request**

.. code-block:: console

    POST /files/<bucket_id>/<file_name>?
         uploads&size=<total_size>&partSize=<part_size>

**Response**

.. code-block:: json

    {
        "updated": "2019-05-24T10:30:02.969221+00:00",
        "links": {
            "self": "http://localhost:5000/files/
                     436ac279-d85f-4500-8217-295804c14794/bar.txt?
                     uploadId=650dd4cb-4f7a-4671-a1e4-fd1dfd1d926c",
            "object": "http://localhost:5000/files/
                       436ac279-d85f-4500-8217-295804c14794/bar.txt",
            "bucket": "http://localhost:5000/files/
                       436ac279-d85f-4500-8217-295804c14794"
        },
        "last_part_size": 5242880,
        "created": "2019-05-24T10:30:02.969216+00:00",
        "bucket": "436ac279-d85f-4500-8217-295804c14794",
        "completed": false,
        "part_size": 6291456,
        "key": "bar.txt",
        "last_part_number": 1,
        "id": "650dd4cb-4f7a-4671-a1e4-fd1dfd1d926c",
        "size": 11534336
    }

**Errors**

.. code-block:: json

    {
        "message": "The request was well-formed but was unable to be followed
                    due to semantic errors.",
        "status": 422
    }


    {
        "status": 400,
        "message": "Invalid part size."
    }


    {
        "status": 400,
        "message": "Invalid file size."
    }


    {
        "message": "Bucket does not exist.",
        "status": 404
    }


Add to multipart upload
^^^^^^^^^^^^^^^^^^^^^^^

**Description**
    Uploads a part of an in-progress multipart upload.

**Parameters**

.. code-block:: console

    binary: <file>

**Request**

.. code-block:: console

    PUT /files/<bucket_id>/<file_name>?uploadId=<id_number>&part=<part_number>

**Response**

.. code-block:: json

    {
        "updated": "2019-05-24T10:37:36.734901+00:00",
        "created": "2019-05-24T10:37:36.708936+00:00",
        "checksum": "md5:bd3c485ea77f37d3cb04501ea6000e63",
        "part_number": 0,
        "end_byte": 6291456,
        "start_byte": 0
    }

**Errors**

.. code-block:: json

    {
        "status": 400,
        "message": null
    }

    {
        "status": 400,
        "message": "No upload part detected in request."
    }


List in-progress multipart uploads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Description**
    Returns a list of all in-progress multipart uploads.

**Parameters**

.. code-block:: console

    No parameters

**Request**

.. code-block:: console

    GET /files/<bucket_id>?uploads

**Response**

.. code-block:: json

    [
        {
            "updated": "2019-05-24T10:30:02.969221+00:00",
            "links": {
                "self": "http://localhost:5000/files/
                         436ac279-d85f-4500-8217-295804c14794/bar.txt?
                         uploadId=650dd4cb-4f7a-4671-a1e4-fd1dfd1d926c",
                "object": "http://localhost:5000/files/
                           436ac279-d85f-4500-8217-295804c14794/bar.txt",
                "bucket": "http://localhost:5000/files/
                           436ac279-d85f-4500-8217-295804c14794"
            },
            "last_part_size": 5242880,
            "created": "2019-05-24T10:30:02.969216+00:00",
            "bucket": "436ac279-d85f-4500-8217-295804c14794",
            "completed": false,
            "part_size": 6291456,
            "key": "bar.txt",
            "last_part_number": 1,
            "id": "650dd4cb-4f7a-4671-a1e4-fd1dfd1d926c",
            "size": 11534336
        }
    ]

**Errors**

.. code-block:: json

    {
        "message": "Bucket does not exist.",
        "status": 404
    }


List uploaded parts
^^^^^^^^^^^^^^^^^^^

**Description**
    Returns a list of all the uploaded parts of a multipart upload.

**Parameters**

.. code-block:: console

    No parameters

**Request**

.. code-block:: console

    GET /files/<bucket_id>/<file_name>?uploadId=<id_number>

**Response**

.. code-block:: json

    {
        "updated": "2019-05-24T10:37:36.707887+00:00",
        "last_part_size": 5242880,
        "links": {
            "self": "http://localhost:5000/files/
                     436ac279-d85f-4500-8217-295804c14794/bar.txt?
                    uploadId=650dd4cb-4f7a-4671-a1e4-fd1dfd1d926c",
            "object": "http://localhost:5000/files/
                       436ac279-d85f-4500-8217-295804c14794/bar.txt",
            "bucket": "http://localhost:5000/files/
                       436ac279-d85f-4500-8217-295804c14794"
        },
        "created": "2019-05-24T10:30:02.969216+00:00",
        "part_size": 6291456,
        "completed": false,
        "bucket": "436ac279-d85f-4500-8217-295804c14794",
        "parts": [
            {
                "updated": "2019-05-24T10:37:36.734901+00:00",
                "created": "2019-05-24T10:37:36.708936+00:00",
                "checksum": "md5:bd3c485ea77f37d3cb04501ea6000e63",
                "part_number": 0,
                "end_byte": 6291456,
                "start_byte": 0
            }
        ],
        "key": "bar.txt",
        "last_part_number": 1,
        "id": "650dd4cb-4f7a-4671-a1e4-fd1dfd1d926c",
        "size": 11534336
    }

**Errors**

.. code-block:: json

    {
        "message": "The request was well-formed but was unable to be followed
                    due to semantic errors.",
        "status": 422
    }

    {
        "message": "uploadId does not exists.",
        "status": 404
    }

    {
        "message": "Bucket does not exist.",
        "status": 404
    }


Complete multipart upload
^^^^^^^^^^^^^^^^^^^^^^^^^

**Description**
    Finalizes the multipart upload, merging all parts into one.

**Parameters**

.. code-block:: console

    No parameters

**Request**

.. code-block:: console

    POST /files/<bucket_id>/<file_name>?uploadId=<id_number>

**Response**

.. code-block:: console

    Status 200 OK

**Errors**

.. code-block:: json

    {
        "status": 400,
        "message": "Not all parts have been uploaded."
    }


Abort multipart upload
^^^^^^^^^^^^^^^^^^^^^^

**Description**
    Aborts a multipart upload.

**Parameters**

.. code-block:: console

    No parameters

**Request**

.. code-block:: console

    DELETE /files/<bucket_id>/<file_name>?uploadId=<upload_id>

**Response**

.. code-block:: console

    Status: 204 NO CONTENT

**Errors**

.. code-block:: json

    {
        "message": "uploadId does not exists.",
        "status": 404
    }


Storage Backends
----------------

In order to get started let's setup and configure a storage backend.
Storage will serve as an interface for the actual file access.

In the configuration of the application, the variable
:py:data:`invenio_files_rest.config.FILES_REST_STORAGE_FACTORY`
defines the path of the factory that will be used to create a storage instance.

Invenio-Files-REST comes with a default storage implementation
`PyFilesystem <https://www.pyfilesystem.org/>`_ to save files locally.

The module provides an abstract layer for storage implementation that allows
to swap storages easily.
For example the storage backend can be a cloud service, such as
`Invenio-S3 <https://invenio-s3.readthedocs.io/>`_ which offers integration
with any S3 REST API compatible object storage.


Build your own Storage Backend
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Advanced topic on how to implement and connect your own storage Backend for
Invenio-Files-REST.

In order to use a different storage backend, it is required to subclass the
:py:data:`invenio_files_rest.storage.FileStorage` class, and provide
implementations for some of its methods.

Mandatory methods to implement:

* :code:`initialize`
* :code:`open`
* :code:`save`
* :code:`update`
* :code:`delete`

Optional methods to implement:

* :code:`send_file`
* :code:`checksum`
* :code:`copy`
* :code:`_init_hash`
* :code:`_compute_checksum`
* :code:`_write_stream`


Create Buckets
--------------

In order to upload, modify or delete files, a bucket needs to be created first.
A bucket can be created by a :code:`POST` request to the endpoint
:code:`/files`. The response will contain the unique ID of the bucket.
A bucket can have one or more tags which store extra metadata for that bucket.
Each tag is uniquely identified by a key.

First let's create a bucket:

.. code-block:: console

   $ curl -X POST http://localhost:5000/files

.. code-block:: json

    {
        "max_file_size": null,
        "updated": "2019-05-16T13:07:21.595398+00:00",
        "locked": false,
        "links": {
            "self": "http://localhost:5000/files/
                     cb8d0fa7-2349-484b-89cb-16573d57f09e",
            "uploads": "http://localhost:5000/files/
                        cb8d0fa7-2349-484b-89cb-16573d57f09e?uploads",
            "versions": "http://localhost:5000/files/
                         cb8d0fa7-2349-484b-89cb-16573d57f09e?versions"
        },
        "created": "2019-05-16T13:07:21.595391+00:00",
        "quota_size": null,
        "id": "cb8d0fa7-2349-484b-89cb-16573d57f09e",
        "size": 0
    }


Upload Files
------------

The REST API allows you to upload, download and modify single files.
A file is uniquely identified within a bucket by its :code:`key` (filename).
Each file can have multiple versions.

Let's upload a file called :code:`my_file.txt` inside the bucket that was just
created. A file can be added to a bucket (uploaded) by a :code:`PUT` request,
which will create a new :code:`ObjectVersion`. The same will happen
when uplading a file with the same :code:`key` (filename).


Upload a file:

.. code-block:: console

   $ B=cb8d0fa7-2349-484b-89cb-16573d57f09e

   $ curl -i -X PUT --data-binary @my_file.txt \
     "http://localhost:5000/files/$B/my_file.txt"

.. code-block:: json

    {
        "mimetype": "text/plain",
        "updated": "2019-05-16T13:10:22.621533+00:00",
        "links": {
            "self": "http://localhost:5000/files/
                     cb8d0fa7-2349-484b-89cb-16573d57f09e/my_file.txt",

            "version": "http://localhost:5000/files/
                        cb8d0fa7-2349-484b-89cb-16573d57f09e/my_file.txt?
                        versionId=7f62676d-0b8e-4d77-9687-8465dc506ca8",
            "uploads": "http://localhost:5000/files/
                        cb8d0fa7-2349-484b-89cb-16573d57f09e/
                        my_file.txt?uploads"
        },
        "is_head": true,
        "tags": {},
        "checksum": "md5:d7d02c7125bdcdd857eb70cb5f19aecc",
        "created": "2019-05-16T13:10:22.617714+00:00",
        "version_id": "7f62676d-0b8e-4d77-9687-8465dc506ca8",
        "delete_marker": false,
        "key": "my_file.txt",
        "size": 14
    }


JS Uploaders
^^^^^^^^^^^^

Some JavaScript uploaders do not allow to customize the name of the request
parameters.
You can create an upload factory according to the specifications of your
JavaScript uploader and update the relevant configuration as follows:

1. Assing your factories to the :code:`config` variables:
:py:data:`invenio_files_rest.config.FILES_REST_MULTIPART_PART_FACTORIES` and
:py:data:`invenio_files_rest.config.FILES_REST_UPLOAD_FACTORIES`

2. Use the :code:`@use_kwargs` decorator to map your JS upoader's parameters
as in the example below, whereby the request paramater :code:`_totalSize`
is mapped to :code:`content-length`:

.. code-block:: python

    @use_kwargs({
        'content_length': fields.Int(
            load_from='_totalSize',
            location='form',
            required=True,
        ),
        'content_type': fields.Str(
            load_from='Content-Type',
            location='headers',
            required=True,
        ),
        'uploaded_file': fields.Raw(
            load_from='file',
            location='files',
            required=True,
        ),
    })

Invenio-Files-REST comes with an implementation for
`ng-file-upload <https://github.com/danialfarid/ng-file-upload>`_ AngularJs
uploader.

For more details see
:py:func:`invenio_files_rest.views.ngfileupload_uploadfactory`.

Multipart Upload
^^^^^^^^^^^^^^^^

In some cases, a file may be too large for a single upload. You might want to
speed up the upload process by uploading multiple parts in parallel. In these
cases, you have to use multipart uploads.

This requires you to split the file you want to upload, in equal chunks except
from the last one which has to be smaller or equal to the chunks size.

Then each chunck can be uploaded in parallel. Once all parts have been
uploaded, the multipart upload completes, and the parts are automatically
merged into one single file.

When uploading a multipart file, if one of the chunks fails, it will be
discarded, and you can resubmit only the failed chunk to conclude your upload.

As an example, let's create an 11MB file which will then be split into 2
chunks using the linux :code:`split` command:

.. code-block:: console

   dd if=/dev/urandom of=my_file.txt bs=1048576 count=11

   split -b6291456 my_file.txt segment_

A multipart upload can be initialised with a :code:`POST` request, sending
the name of the file after merge, the chunk size and the total size.

Then each part upload can be uploaded with a :code:`PUT` request.

Create a new bucket:

.. code-block:: console

   $ curl -X POST http://localhost:5000/files

The ID is contained in the response:

.. code-block:: json

    {
       "max_file_size":null,
       "updated":"2019-05-17T06:52:52.897378+00:00",
       "locked":false,
       "links":{
          "self":"http://localhost:5000/files/
                  c896d17b-0e7d-44b3-beba-7e43b0b1a7a4",
          "uploads":"http://localhost:5000/files/
                     c896d17b-0e7d-44b3-beba-7e43b0b1a7a4?uploads",
          "versions":"http://localhost:5000/files/
                      c896d17b-0e7d-44b3-beba-7e43b0b1a7a4?versions"
       },
       "created":"2019-05-17T06:52:52.897373+00:00",
       "quota_size":null,
       "id":"c896d17b-0e7d-44b3-beba-7e43b0b1a7a4",
       "size":0
    }

Multipart upload initialisation:

.. code-block:: console

   $ B=c896d17b-0e7d-44b3-beba-7e43b0b1a7a4

   $ curl -i -X POST \
     "http://localhost:5000/files/$B/my_file.txt?
      uploads&size=11534336&partSize=6291456"

The response will contain the upload :code:`id` that is needed for the
requests for the parts uploads:

.. code-block:: json

    {
       "updated":"2019-05-17T07:07:22.219002+00:00",
       "links":{
          "self":"http://localhost:5000/files/
                  c896d17b-0e7d-44b3-beba-7e43b0b1a7a4/my_file.txt?
                  uploadId=a85b1cbd-4080-4c81-a95c-b4df5d1b615f",

          "object":"http://localhost:5000/files/
                    c896d17b-0e7d-44b3-beba-7e43b0b1a7a4/my_file.txt",

          "bucket":"http://localhost:5000/files/
                    c896d17b-0e7d-44b3-beba-7e43b0b1a7a4"
       },
       "last_part_size":5242880,
       "created":"2019-05-17T07:07:22.218998+00:00",
       "bucket":"c896d17b-0e7d-44b3-beba-7e43b0b1a7a4",
       "completed":false,
       "part_size":6291456,
       "key":"my_file.txt",
       "last_part_number":1,
       "id":"a85b1cbd-4080-4c81-a95c-b4df5d1b615f",
       "size":11534336
    }

Continue uploading parts, by using a PUT request and specifying the upload
:code:`id` of the bucket:

.. code-block:: console

   $ U=a85b1cbd-4080-4c81-a95c-b4df5d1b615f

   $ curl -i -X PUT --data-binary @segment_aa \
     "http://localhost:5000/files/$B/my_file.txt?uploadId=$U&partNumber=0"

    {
       "updated":"2019-05-17T07:08:27.069504+00:00",
       "created":"2019-05-17T07:08:27.048028+00:00",
       "checksum":"md5:876ae993a752f38b1850668be7e3fe9a",
       "part_number":0,
       "end_byte":6291456,
       "start_byte":0
    }

   $ curl -i -X PUT --data-binary @segment_ab \
     "http://localhost:5000/files/$B/my_file.txt?uploadId=$U&partNumber=1"

Complete a multipart upload, by submitting a :code:`POST` request, with the
upload id.

.. code-block:: console

   $ curl -i -X POST \
     "http://localhost:5000/files/$B/my_file.txt?uploadId=$U"

Abort a multipart upload (deletes all uploaded parts); it will return a 204
code if it succeeds:

.. code-block:: console

   $ curl -i -X DELETE "http://localhost:5000/files/$B/my_file.txt?uploadId=$U"


Large Files
^^^^^^^^^^^
The maximum file size for upload is defined by :code:`MAX_CONTENT_LENGTH`
header. In addition your webserver i.e. Nginx will apply a limitation on the
body size of the request.

1. You can modify the maximum allowed file size by changing the
:code:`MAX_CONTENT_LENGTH` configuration variable. Flask
will reject any incoming requests with a greater content length by returning a
:code:`413 (Request Entity Too Large)`. For security if it is not set and
the request does not specify a :code:`CONTENT_LENGTH` header, no data will be
read. The example below configues :code:`MAX_CONTENT_LENGTH` to :code:`25MB`.

>>> app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024

.. note::

    Special note on the :code:`get_data()` method: Calling this loads the full
    request data into memory. This is only safe to do if the
    :code:`MAX_CONTENT_LENGTH` is set.

2. In case of using Nginx, the request body size is limitd by the configuration
variable :code:`client_max_body_size`. For files with size greater than that,
it will return :code:`413 (Request Entity Too Large)`. The following example
configures Nginx to accept up to :code:`25MB`.

.. code-block:: console

    http {
        ...
        client_max_body_size 25M;
    }


Retrieve Files
--------------

Once the bucket is created and a file is uploaded, it is possible
to retrieve it with a :code:`GET` request.

By default, the latest version will be retrieved. To retrieve a specific
version of the file, the :code:`versionId` query parameter can be used, as in
the example below:

Download the latest version of the file:

.. code-block:: console

   $ curl -i http://localhost:5000/files/$B/my_file.txt

Download a specific version of the file:

.. code-block:: console

   $ curl -i http://localhost:5000/files/$B/my_file.txt?versionId=<version_id>

.. note::
    By default, the file is returned with the header
    :code:`'Content-Disposition': 'inline'`, so that the browser will try to
    preview it. In case you want to trigger a download of the file, use the
    :code:`download` query parameter, which will change the
    :code:`'Content-Disposition'` header to :code:`'attachment'`

.. code-block:: console

   $ curl -i http://localhost:5000/files/$B/my_file.txt?download


Security
^^^^^^^^

It is very easy to be exposed to Cross-Site Scripting (XSS) attacks if you
serve user uploaded files. Here are some recommendations:

1. Serve user uploaded files from a separate domain (not a subdomain). This
way a malicious file can only attack other user uploaded files.

2. Prevent the browser from rendering and executing HTML files by setting
:code:`trusted=False` in the :code:`send_file()` method of your
:code:`FileStorage` implementation.

3. Force the browser to download the file as an attachment
:code:`as_attachment=True` by adding the :code:`download` keyword in the query
parameters.


Delete Files
------------

If you want to delete a file there are two options:

1. You can mark the file as deleted. This will create a new
:code:`ObjectVersion` without content (creates a delete marker and makes the
file inaccessible):

.. code-block:: console

   $ curl -i -X DELETE http://localhost:5000/files/$B/my_file.txt


2. Permanently delete a specific object version, by specifying
the version id. This will completely remove the :code:`ObjectVersion`:

.. code-block:: console

   $ curl -i -X DELETE \
       http://localhost:5000/files/$B/my_file.txt?versionId=<version_id>


.. :note::
    :code:`ObjectVersion` that are marked as deleted can be retrieved only by
    providing an explicit :code:`versionId` as query parameter.


The file instance on disk cannot be removed through REST API. You can use
the provided task via CLI
:py:func:`invenio_files_rest.tasks.remove_file_data`.


Access control
--------------

Invenio-Files-REST depends on `Invenio-Access
<https://invenio-access.readthedocs.io>`_ module, to control the files access.

It comes with a default permission factory implementation which can be found
at :py:data:`invenio_files_rest.permissions.permission_factory` and can be
customized further, by providing your custom implementation in the relevant
config variable
:py:data:`invenio_files_rest.config.FILES_REST_PERMISSION_FACTORY`.

The module also comes with a list of predefined actions for the most common
operations:

    - location-update
    - bucket-read
    - bucket-read-versions
    - bucket-update
    - bucket-listmultiparts
    - object-read
    - object-read-version
    - object-delete
    - object-delete-version
    - multipart-read
    - multipart-delete


For example, to verify that the contents of a bucket can be read, you should
add the decorator with :code:`bucket-read` action which takes the bucket as the
argument.

.. code-block:: python

    @need_permissions(
        lambda self, bucket, versions: bucket,
        'bucket-read',
    )
    def foo():
        print("Function foo can read the content of the bucket")


By default when try perform an action and the permission check fails, the
returned http status code will be :code:`404` instead of :code:`401` or
:code:`403` to hide the existence or non, of objects.

See :mod:`invenio_files_rest.permissions` for extensive documentation.


Integrity
---------

Invenio-Files-REST stores file checksums and regularly revalidates them, in
order to verify the data integrity of all data at rest, as well as to detect
corruption of data in transit.

For the computation of the checksum you can provide the desired algorithm,
otherwise :code:`MD5` will be used.

When uploading a file a checksum is computed on the fly and stored in the
database.

For all existing files there is a predefined task :code:`verify_checksum`
which can be configured to run periodically (default is every 30 days) and
iterates all files in your storage and validates their checksum.

When removing a file from disk, the operation is a combination of two steps,
first delete the :code:`FileInstance` from the database, and if it succeeds
will try to delete the File from disk. This leaves the possibility of having
a file on disk dangling in case the database removal works, and the disk file
removal doesn't work.


Signals
-------

Invenio-Files-REST supports signals that can be used to react to events.

Events are sent in case of:

* file downloaded

Let's request to download a file, and capture the signal:

.. code-block:: python

    from invenio_files_rest.signals import file_downloaded

    def after_file_downloaded(send, *args, *kwargs):
        print('Signal file_downloaded emitted')

    listener = file_downloaded.connect(after_file_downloaded)
    # Request to dowload a file for the event to trigger

You can read more about the `Flask Signals
<http://flask.pocoo.org/docs/1.0/signals/>`_.


Data Migration
--------------

:code:`Locations` are used to represent different storage systems and possibly
different geographical locations. :code:`Buckets` but also
:code:`ObjectVersions` are assigned a Location. This approach provides extra
flexibility when there's a need to migrate the data.

When a bucket is created, a Location needs to be provided, otherwise the
default one is used.

.. note::
    Before updating our records to point to the new :code:`Location`, the
    actual files need to be copied in the new storage with the new location.
    Then a bulk update needs to be performed on the FileInstance objects
    to point to the new bucket.

Invenio-Files-REST provides a celery task
:py:func:`invenio_files_rest.tasks.migrate_file` to migrate existing files
from current location to a new location. A new location might be in remote
system on a different bucket, even on a different storage backend. This task
can be used to migrate all files or a subset of files in case of location
change. Given a :code:`file_id` and the name of the new location (which should
have been already created), it will:

    1. create a new empty :code:`FileInstance` in the destination location
    2. copy the file content in the newly created :code:`FileInstance`
    3. re-link all ObjectVersions pointing to the previous :code:`FileInstance`
       to the new one, and optionally with :code:`post_fixity_check` argument,
       re-compute the file checksum

In case process does not complete successfully, destination
:code:`FileInstance` is removed completely and the process has to be repeated.

See :doc:`api` for an extensive API documentation.
"""

from __future__ import absolute_import, print_function

from .ext import InvenioFilesREST
from .proxies import current_files_rest
from .version import __version__

__all__ = ('__version__', 'current_files_rest', 'InvenioFilesREST', )
