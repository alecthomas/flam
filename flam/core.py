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


__all__ = ['Error', 'log']


class Error(Exception):
    """Base Flam exception."""


formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    '%Y-%m-%d %H:%M:%S',
    )
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(formatter)

log = logging.getLogger('flam')
log.setLevel(logging.INFO)
log.addHandler(console)
