# -*- coding: utf-8 -*-
#
# Copyright 2008 Alec Thomas <alec@swapoff.org>
# All rights reserved.
#

"""Command-line glue for Flam.

Provides a convenient way to start and configure your application. The
bootstrap function provides several useful features:

  - Provides the --config=<file> option, allowing the application to specify
    the configuration file to load options from.
  - Provides --debug=<n> for setting the debug level early on.
  - Provides --help and optionally --version via optparse.
  - All config.Options are mapped as command-line arguments.
"""


import os
import sys
import traceback
from optparse import OptionParser, Option
import flam.config


__all__ = ['parse_args']
__author__ = 'Alec Thomas <alec@swapoff.org>'


class Error(Exception):
    """Base bootstrap exception."""


def _extract_bootstrap_args(parser, args):
    """Extract arguments used to bootstrap the application object."""
    output = []
    option_names = []

    for option in parser.option_list:
        option_names.extend([(n[2:], option.nargs) for n in option._long_opts
                             if n[2:] not in ['help', 'version']])

    for i, arg in enumerate(args):
        value = None
        for name, nargs in option_names:
            if arg.startswith('--%s=' % name):
                output.append(arg)
            elif arg == '--' + name:
                output.append(arg)
                if nargs:
                    try:
                        output.append(args[i + 1])
                    except IndexError:
                        pass

    return output


def _to_optparse_option(config, config_option):
    """Transform a flam.config.Option object to an optparse.Option object."""

    def default_converter(option, opt_str, value, parser):
        config.set(config_option.name, value, transient=True)
        value = config_option.cast(value)
        setattr(parser.values, option.dest, value)

    def boolean_converter(option, opt_str, value, parser):
        config.set(config_option.name, not default, transient=True)
        setattr(parser.values, config_option.name, not default)

    default = config_option.accessor(
        config, config_option.name, config_option.default,
        )

    type_name = config_option.__class__.__name__.lower()
    if type_name.endswith('option'):
        type_name = type_name[:-6]
    metavar = config_option.metavar

    args = dict(
        help=config_option.__doc__ + ' (%default)', action='callback', default=default,
        metavar=(metavar or type_name).upper(), dest=config_option.name,
        )

    if type_name == 'bool':
        args['callback'] = boolean_converter
    else:
        args['type'] = 'string'
        args['callback'] = default_converter
    return Option('--' + config_option.name, **args)


def parse_args(argv=None, config=None, name=None, version=None):
    """Bootstrap a main function with command line and configuration options.

    :param argv: sys.argv (or equivalent)
    :param config: flam.config.Configuration object or filename.
    :param name: Name of the application.
    :param version: Version number of the application.
    """
    argv = argv or sys.argv
    name = name or os.path.basename(argv[0]).replace('.py', '')

    # Extract bootstrap arguments from commandline
    parser = OptionParser(prog=name, conflict_handler='resolve',
                          version=version)
    default_config = None
    if config is None and name is not None:
        default_config = name + '.conf'
    elif isinstance(config, basestring):
        default_config = config
    parser.add_option('--config', default=default_config,
                      help='configuration file for %s' % name,
                      metavar='file')
    parser.add_option('--debug', default=None, type='int',
                      help='Set debug level.')
    #parser.add_option('--logging', default=None, type='string')

    args = _extract_bootstrap_args(parser, argv[1:])
    options, args = parser.parse_args(args)

    if config is None:
        config = options.config
    config = flam.config.Configuration(config)
    flam.config.set_global_config(config)

    for name, option in sorted(flam.config.Option.registry.iteritems()):
        optparse_option = _to_optparse_option(config, option)
        parser.add_option(optparse_option)

    options, args = parser.parse_args(argv[1:])
    for key, value in options.__dict__.iteritems():
        if value is not None:
            config.set(key, value, transient=True)
    return config, args
