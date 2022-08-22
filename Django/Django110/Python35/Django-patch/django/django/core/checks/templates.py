# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy

from django.conf import settings
from django.utils import six

from . import Error, Tags, register

E001 = Error(
    "You have 'APP_DIRS': True in your TEMPLATES but also specify 'loaders' "
    "in OPTIONS. Either remove APP_DIRS or remove the 'loaders' option.",
    id='templates.E001',
)
E002 = Error(
    "'string_if_invalid' in TEMPLATES OPTIONS must be a string but got: {} ({}).",
    id="templates.E002",
)


@register(Tags.templates)
def check_setting_app_dirs_loaders(app_configs, **kwargs):
    passed_check = True
    for conf in settings.TEMPLATES:
        if not conf.get('APP_DIRS'):
            continue
        if 'loaders' in conf.get('OPTIONS', {}):
            passed_check = False
    return [] if passed_check else [E001]


@register(Tags.templates)
def check_string_if_invalid_is_string(app_configs, **kwargs):
    errors = []
    for conf in settings.TEMPLATES:
        string_if_invalid = conf.get('OPTIONS', {}).get('string_if_invalid', '')
        if not isinstance(string_if_invalid, six.string_types):
            error = copy.copy(E002)
            error.msg = error.msg.format(string_if_invalid, type(string_if_invalid).__name__)
            errors.append(error)
    return errors
