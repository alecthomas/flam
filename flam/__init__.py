# encoding: utf-8
#
# Copyright (C) 2008-2009 Alec Thomas <alec@swapoff.org
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

"""flam /flæm/ noun, verb, flammed, flam⋅ming. Informal. –noun 1. a deception
or trick. 2. a falsehood; lie. –verb (used with object), verb (used without
object) 3. to deceive; delude; cheat.

Flam - A minimalist Python application framework.
"""

__author__ = 'Alec Thomas <alec@swapoff.org>'

__all__ = ['Error']

# Try and determine the version of flam according to pkg_resources.
try:
    from pkg_resources import get_distribution, ResolutionError
    try:
        __version__ = get_distribution('flam').version
    except ResolutionError:
        __version__ = None # unknown
except ImportError:
    __version__ = None # unknown


class Error(Exception):
    """Base Flam exception."""
