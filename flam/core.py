# encoding: utf-8
#
# Copyright (C) 2008-2009 Alec Thomas <alec@swapoff.org
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

import logging

from flam import flags


__all__ = ['Error', 'log']


class Error(Exception):
    """Base Flam exception."""


def _set_log_level(option, opt_str, value, parser):
    level = getattr(logging, value.upper(), 'WARN')
    log.setLevel(level)

flags.add('--log-level', type=str, action='callback', callback=_set_log_level,
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
log.setLevel(logging.WARN)
log.addHandler(console)
