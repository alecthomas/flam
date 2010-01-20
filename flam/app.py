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
from flam.signal import Signal


__all__ = ['init', 'run', 'on_application_init']


on_application_init = Signal()


def init(args=None, usage=None, version=None):
    """Initialise the application."""
    on_application_init()
    if version:
        flags.parser.set_version(version)
    if usage:
        flags.parser.set_usage(usage)
    return flags.parse_args(args)


def run(main, args=None, usage=None, version=None):
    """Initialise and run the application.

    This function parses and updates the global flags object, and passes
    any remaining arguments through to the main function.

    >>> def main(args):
    ...   print args
    >>> run(main, ['hello', 'world'])
    ['hello', 'world']

    :param main: Main function to call, with the signature main(args).
    :param args: Command-line arguments. Will default to sys.argv[1:].
    :param usage: A usage string, displayed when --help is passed. If not
                  provided, the docstring from main will be used.
    :param version: The version of the application. If provided, adds a
                    --version flag.
    """
    if usage is None:
        usage = inspect.getdoc(main)
    args = init(args, usage, version)
    main(args)
