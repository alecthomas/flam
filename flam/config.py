# -*- coding: utf-8 -*-
#
# Copyright (C) 2003-2005 Edgewall Software
# Copyright (C) 2003-2004 Jonas Borgström <jonas@edgewall.com>
# Copyright (C) 2004-2005 Christopher Lenz <cmlenz@gmx.de>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.org/wiki/TracLicense.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://trac.edgewall.org/log/.
#
# Author: Jonas Borgström <jonas@edgewall.com>
#     Christopher Lenz <cmlenz@gmx.de>
import os

from flam import features
from flam.util import to_list, to_boolean, URI


__all__ = """
Configuration
Option
BoolOption
IntOption
FloatOption
ListOption
URIOption
FeatureOption
OrderedFeaturesOption
set_global_config
""".split()


_config = None

def set_global_config(config):
    """Set default global config."""
    global _config
    _config = config


class Configuration(dict):
    """Abstraction layer for a basic key/value configuration file format."""

    def __init__(self, filename=None):
        super(Configuration, self).__init__()
        self.filename = filename
        if filename and os.path.exists(filename):
            self.load(filename)

    def load(self, filename):
        for line in open(filename):
            line = line.split('#', 1)[0].strip()
            if not line:
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            self[key] = value

    # Public API
    def options(self):
        return sorted(self.items())

    def update(self, data, transient=False):
        """Bulk update configuration options from a dictionary."""
        super(Configuration, self).update(data)
        if not transient and self.filename:
            # TODO Reflect this back to the configuration file
            raise NotImplementedError

    def get(self, name, default=None):
        if name in self:
            value = super(Configuration, self).get(name, default)
        else:
            option = Option.registry.get(name)
            if option is not None:
                value = option.default
                if value is None:
                    value = default
            else:
                value = default
        return value

    def set(self, name, value, transient=False):
        """set a configuration option.

        Args:
            transient: Value is for the lifetime of this session only.
        """
        self[name] = value
        if not transient and self.filename:
            # TODO Reflect this back to the configuration file
            raise NotImplementedError

    def get_bool(self, name, default=None):
        return to_boolean(self.get(name, default))

    def get_int(self, name, default=None):
        return int(self.get(name, default))

    def get_float(self, name, default=None):
        return float(self.get(name, default))

    def get_list(self, name, default=None, sep=',', keep_empty=False):
        return to_list(self.get(name, default), sep, keep_empty)


class Option(object):
    """"A convenience property for accessing configuration entries.
    
    Options are also mapped to commandline flags via the ape.commandline module.
    """

    registry = {}

    def __init__(self, name, default=None, help='', metavar=None):
        """Create a new Option.

        Args:
            name: Name of the option.
            default: Default value.
            help: Documentation string.
            metavar: Name of variable to display in help.
        """
        self.name = name
        if default is not None:
            self.default = self.cast(default)
        else:
            self.default = default
        self.__doc__ = help
        self.metavar = metavar
        self.registry[name] = self

    def __get__(self, instance, owner):
        if instance is None:
            return self
        config = getattr(instance, '_config', _config)
        if config is not None:
            return self.accessor(config, self.name, self.default)
        else:
            return self.default

    def __set__(self, instance, value):
        config = getattr(instance, '_config', config)
        config.set(self.name, unicode(value))

    def accessor(self, config, name, default):
        return self.cast(config.get(name, default))

    def cast(self, value):
        return str(value)


class BoolOption(Option):
    def cast(self, value):
        return to_boolean(value)


class IntOption(Option):
    def cast(self, value):
        return int(value)


class FloatOption(Option):
    def cast(self, value):
        return float(value)


class ListOption(Option):
    def __init__(self, name, default=None, help='', metavar=None, sep=',',
                 keep_empty=False):
        self.sep = sep
        self.keep_empty = keep_empty
        Option.__init__(self, name, default, help, metavar)

    def cast(self, value):
        return to_list(value, self.sep, self.keep_empty)


class URIOption(Option):
    def cast(self, value):
        return URI(value)


class FeatureOption(Option):
    def __init__(self, name, feature, default=None, help='', metavar=None):
        Option.__init__(self, name, default, help, metavar)
        self.feature = feature

    def __get__(self, instance, owner):
        if instance is None:
            return self
        value = Option.__get__(self, instance, owner)

        for impl in features.require(self.feature):
            if impl.__class__.__name__ == value:
                return impl
        raise AttributeError('Cannot find an implementation of the "%s" '
                             'interface named "%s". Please update the option '
                             '%s.' % (self.feature.__class__.__name__, value,
                                      self.name))


class OrderedFeaturesOption(ListOption):
    """A comma separated, ordered, list of components implementing `interface`.
    Can be empty.

    If `include_missing` is true (the default) all components implementing the
    interface are returned, with those specified by the option ordered first."""

    def __init__(self, name, feature, default=None,
                 help='', metavar=None, include_missing=True):
        ListOption.__init__(self, name, default, help, metavar)
        self.feature = feature
        self.include_missing = include_missing

    def __get__(self, instance, owner):
        if instance is None:
            return self
        order = ListOption.__get__(self, instance, owner)
        components = []
        for impl in features.require(self.feature):
            if self.include_missing or impl.__class__.__name__ in order:
                components.append(impl)

        def compare(x, y):
            x, y = x.__class__.__name__, y.__class__.__name__
            if x not in order:
                return int(y in order)
            if y not in order:
                return -int(x in order)
            return cmp(order.index(x), order.index(y))
        components.sort(compare)
        return components
