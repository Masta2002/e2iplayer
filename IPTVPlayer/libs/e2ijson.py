# -*- coding: utf-8 -*-
#
# Thin wrapper around the stdlib json module. The extra loads() keyword
# arguments are kept for call-site compatibility; they are no-ops now that
# the optional e2icjson C accelerator has been dropped.

import json


def loads(inputString, noneReplacement=None, baseTypesAsString=False, utf8=True):
    return json.loads(inputString)


def dumps(inputString, *args, **kwargs):
    return json.dumps(inputString, *args, **kwargs)
