# encoding: utf-8
#
# Copyright (C) 2008-2009 Alec Thomas <alec@swapoff.org
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

from __future__ import absolute_import

import logging

from flam import flags
from flam.app import on_application_init
from flam.signal import Signal


__all__ = ['log', 'on_log_level_change']


on_log_level_change = Signal()


def _set_log_level(option, opt_str, value, parser):
    """Flag callback for setting the log level."""
    level = getattr(logging, value.upper(), 'WARN')
    on_log_level_change(level)

flags.flag('--log-level', type=str, action='callback', callback=_set_log_level,
           help='set log level to debug, info, warning, error or fatal [%default]',
           metavar='LEVEL', default='warning')


@on_log_level_change.connect
def _set_logger_level(level):
    """Set the log level of the default logger."""
    log.setLevel(level)


@on_application_init.connect
def _initialise_log_level():
    """Update any loggers."""
    on_log_level_change(logging.FATAL)


formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    '%Y-%m-%d %H:%M:%S',
    )
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(formatter)

log = logging.getLogger('flam')
log.setLevel(logging.FATAL)
log.addHandler(console)
