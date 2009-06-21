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

    >>> def main(args):
    ...   print flags.flags
    ...   print args
    >>> run(main, ['hello', 'world'])
    {}
    ['hello', 'world']

    Now provide a version and call --help:

    >>> try:
    ...   run(main, args=['--help'], usage='test [options]', version='0.1')
    ... except SystemExit:
    ...   pass
    Usage: test [options]
    <BLANKLINE>
    Options:
      -h, --help  show this help message and exit
      --config    load flags from FILE
      --version   show program's version number and exit

    :param args: Command-line arguments. Will default to sys.argv[1:].
    :param usage: A usage string, displayed when --help is passed. If not
                  provided, the docstring from main will be used.
    :param version: The version of the application. If provided, adds a
                    --version flag.
    """
    if version:
        flags.parser.set_version(version)
    if usage:
        flags.parser.set_usage(usage)
    else:
        flags.parser.set_usage(inspect.getdoc(main))
    options, args = flags.parser.parse_args(args)
    flags.flags.__dict__.update(options.__dict__)
    main(args)
