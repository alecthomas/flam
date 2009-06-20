# encoding: utf-8
#
# Copyright (C) 2009 Alec Thomas <alec@swapoff.org>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

"""Application bootstrap."""


import inspect

from flam import flags


__all__ = ['run']


def run(main, args=None, usage=None, version=None):
    """Initialise and run the application.

    This function parses and updates the global flags object, and passes
    any remaining arguments through to the main function.
    """
    if version:
        flags.parser.version = version
    if usage:
        flags.parser.set_usage(usage)
    else:
        flags.parser.set_usage(inspect.getdoc(main))
    options, args = flags.parser.parse_args(args)
    flags.flags.__dict__.update(options.__dict__)
    main(args)
