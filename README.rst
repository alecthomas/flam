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

Register new flags with :func:`flam.flag` (this is an alias for
optparse.OptionParser.add_option()).

The underlying optparse.OptionParser object is exposed as :data:`flam.flag_parser`.

Call :func:`flam.parse_args` to parse command-line arguments. Defaults to
parsing sys.argv[1:].

:data:`flam.flags` is an optparse.Values() object that will contain the parsed
flag values.

The --flags=FILE flag can be used to load flag values from a file consisting of
"key = value" lines. Both empty lines and those beginning with # are ignored.
