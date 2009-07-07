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


__all__ = ['log']



def _set_log_level(option, opt_str, value, parser):
    """Flag callback for setting the log level."""
    level = getattr(logging, value.upper(), 'WARN')
    log.setLevel(level)

flags.flag('--log-level', type=str, action='callback', callback=_set_log_level,
           help='set log level to debug, info, warning, error or fatal [%default]',
           metavar='LEVEL', default='warning')


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
