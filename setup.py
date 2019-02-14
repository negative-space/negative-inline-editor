#!/usr/bin/env python

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

readme = open('README.rst').read()
doclink = """
Documentation
-------------

The full documentation is at http://negative-inline-editor.rtfd.org."""
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name='negative-inline-editor',
    version='0.1.0',
    description='On-site editing for Django',
    long_description=readme + '\n\n' + doclink + '\n\n' + history,
    author='Alex Rudakov',
    author_email='ribozz@gmail.com',
    url='https://github.com/negative-space/negative-inline-editor',
    packages=[
        'negative_inline_editor',
    ],
    package_dir={'negative-inline-editor': 'negative-inline-editor'},
    include_package_data=True,
    install_requires=[
        'django-i18n',
        'django-threadlocals'
    ],
    license='MIT',
    zip_safe=False,
    keywords='negative-inline-editor',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],

    extras_require={
        'filer':  [
            "django-rest-framework",
            "easy-thumbnails",
            "django-filer",
        ]
    }
)
