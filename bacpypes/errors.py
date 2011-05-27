#!/usr/bin/python

import exceptions

#
#   ConfigurationError
#

class ConfigurationError(exceptions.ValueError):

    def __init__(self, *args):
        self.args = args

#
#   EncodingError
#

class EncodingError(exceptions.ValueError):

    def __init__(self, *args):
        self.args = args

#
#   DecodingError
#

class DecodingError(exceptions.ValueError):

    def __init__(self, *args):
        self.args = args

