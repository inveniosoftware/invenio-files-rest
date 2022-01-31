# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Files download/upload REST API similar to S3 for Invenio."""

import os
from setuptools import find_packages, setup

readme = open('README.rst').read()
history = open('CHANGES.rst').read()

tests_require = [
    'Flask-BabelEx>=0.9.4',
    'Flask-Menu>=0.5.0',
    'invenio-access>=1.2.0',
    'invenio-accounts>=1.4.0',
    'invenio-admin>=1.2.0',
    'mock>=1.3.0',
    'pytest-invenio>=1.4.2'
]

extras_require = {
    'docs': [
        'Sphinx>=4.2.0',
        'sphinxcontrib-httpdomain>=1.4.0',
    ],
    'postgresql': [
        'invenio-db[postgresql,versioning]>=1.0.9',
    ],
    'mysql': [
        'invenio-db[mysql,versioning]>=1.0.9',
    ],
    'sqlite': [
        'invenio-db[versioning]>=1.0.9',
    ],
    'tests': tests_require,
}


extras_require['all'] = []
for name, reqs in extras_require.items():
    if name in ('postgresql', 'mysql', 'sqlite'):
        continue
    extras_require['all'].extend(reqs)


install_requires = [
    'click-default-group>=1.2.2,<2.0.0',
    'Flask-Login>=0.3.2,<0.5.0',
    'Flask-WTF>=0.15.1',
    'fs>=2.0.10,<3.0',
    'invenio-accounts>=1.4.8',
    'invenio-base>=1.2.5',
    'invenio-celery>=1.2.3',
    'invenio-rest[cors]>=1.2.4',
    'WTForms>=2.0',
]

setup_requires = [
    'Babel>=2.8',
]

packages = find_packages()

# Get the version string. Cannot be done with import!
g = {}
with open(os.path.join('invenio_files_rest', 'version.py'), 'rt') as fp:
    exec(fp.read(), g)
    version = g['__version__']

setup(
    name='invenio-files-rest',
    version=version,
    description=__doc__,
    long_description=readme + '\n\n' + history,
    keywords='invenio files REST',
    license='MIT',
    author='CERN',
    author_email='info@inveniosoftware.org',
    url='https://github.com/inveniosoftware/invenio-files-rest',
    packages=packages,
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    entry_points={
        'invenio_access.actions': [
            # Location related permissions
            'location_update_all'
            ' = invenio_files_rest.permissions:location_update_all',
            # Bucket related permissions.
            'bucket_read_all'
            ' = invenio_files_rest.permissions:bucket_read_all',
            'bucket_read_versions_all'
            ' = invenio_files_rest.permissions:bucket_read_versions_all',
            'bucket_update_all'
            ' = invenio_files_rest.permissions:bucket_update_all',
            'bucket_listmultiparts_all'
            ' = invenio_files_rest.permissions:bucket_listmultiparts_all',
            # Object related permissions.
            'object_read_all'
            ' = invenio_files_rest.permissions:object_read_all',
            'object_read_version_all'
            ' = invenio_files_rest.permissions:object_read_version_all',
            'object_delete_all'
            ' = invenio_files_rest.permissions:object_delete_all',
            'object_delete_version_all'
            ' = invenio_files_rest.permissions:object_delete_version_all',
            # Multipart related permissions.
            'multipart_read_all'
            ' = invenio_files_rest.permissions:multipart_read_all',
            'multipart_delete_all'
            ' = invenio_files_rest.permissions:multipart_delete_all',
        ],
        'invenio_admin.views': [
            'location_adminview = invenio_files_rest.admin:location_adminview',
            'bucket_adminview = invenio_files_rest.admin:bucket_adminview',
            'object_adminview = invenio_files_rest.admin:object_adminview',
            'fileinstance_adminview'
            ' = invenio_files_rest.admin:fileinstance_adminview',
            'multipartobject_adminview'
            ' = invenio_files_rest.admin:multipartobject_adminview',
        ],
        'invenio_base.api_apps': [
            'invenio_files_rest = invenio_files_rest:InvenioFilesREST',
        ],
        'invenio_base.api_blueprints': [
            'invenio_files_rest = invenio_files_rest.views:blueprint',
        ],
        'invenio_base.apps': [
            'invenio_files_rest = invenio_files_rest:InvenioFilesREST',
        ],
        'invenio_celery.tasks': [
            'invenio_files_rest = invenio_files_rest.tasks',
        ],
        'invenio_db.alembic': [
            'invenio_files_rest = invenio_files_rest:alembic',
        ],
        'invenio_db.models': [
            'invenio_files_rest = invenio_files_rest.models',
        ],
    },
    extras_require=extras_require,
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'Development Status :: 5 - Production/Stable',
    ],
)
