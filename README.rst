=============================
negative_inline_editor
=============================

.. image:: https://badge.fury.io/py/negative-inline-editor.png
    :target: http://badge.fury.io/py/negative-inline-editor

.. image:: https://travis-ci.org/negative-space/negative-inline-editor.png?branch=master
    :target: https://travis-ci.org/negative-space/negative-inline-editor

On-site editing for Django

Features
--------

* Nicely looking panel for inline editing
* Edit single model fields on-site
* Edit list with drag-and-drop and add/delete support
* Medium-like content-editing integrated
* negative-i18n integration


Installation
---------------

pip install negative-inline-editor

Add 'negative_inline_editor' to installed apps and add middleware:


    INSTALLED_APPS += [
        'negative_inline_editor'
    ]

    MIDDLEWARE += [
        'negative_inline_editor.middleware.EditableMiddleware'
    ]


Configuration
------------------

Add to the settings application that are allowed to edit through fronted (by super-user only).

NEGATIVE_INLINE_MODELS = [
    'negative_i18n',
    'my_app',
]


Usage
---------------

Single field editing

{% editable page->title %}