A minimalist Python application framework
=========================================

Flam provides utility functions and classes used in 99% of applications. No
more. No less.

Currently it provides:

  - Flag management.
  - Application bootstrapping.
  - Callback "signal" objects.

Flag management
---------------

Register new flags with ``flam.define_flag()``. This is an alias for
``optparse.OptionParser.add_option()`` and thus accepts exactly the same arguments.

The underlying ``optparse.OptionParser`` object is exposed as ``flam.flag_parser``.

Call ``flam.parse_args()`` to parse command-line arguments. Defaults to
parsing sys.argv[1:].

``flam.flags`` is an optparse.Values() object that will contain the parsed
flag values.

The --flags=FILE flag can be used to load flag values from a file consisting of
"key = value" lines. Both empty lines and those beginning with # are ignored.
