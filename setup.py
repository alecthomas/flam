import fileinput
import os
import sys
import textwrap

from distutils.command.build_py import build_py as _build_py
from distutils import log
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


class build_py(_build_py):
    """Update auto import map in flam/__init__.py before building."""

    def run(self):
        log.info('updating auto import map in flam/__init__.py')
        module_map = self._find_modules()
        self._update_auto_imports(module_map)
        _build_py.run(self)

    def _find_modules(self):
        module_map = {}
        symbols = set()
        for dir, dirs, files in os.walk('flam'):
            modules = [os.path.join(dir, file).replace('.py', '').replace('/', '.')
                       for file in files
                       if not file.startswith('_')
                       and file.endswith('.py')
                       and 'test' not in file]
            for name in modules:
                module = __import__(name, {}, {}, ['.'])
                duplicates = symbols.intersection(module.__all__)
                if duplicates:
                    log.warn('warning: Duplicate symbols "%s" found in %s.'
                             % (', '.join(duplicates), name))
                symbols.update(module.__all__)
                module_map[name] = module.__all__
        return module_map

    def _update_auto_imports(self, module_map):
        inside = 0

        # Prioritise symbols from flam.core over all others.
        core = module_map.pop('flam.core')

        for line in fileinput.input('flam/__init__.py', inplace=1):
            if '# BEGIN IMPORTS' in line:
                inside = 1
            elif '# END IMPORTS' in line:
                inside = 0
            elif inside == 1:
                inside += 1

            if inside != 2:
                sys.stdout.write(line)
            if inside == 1:
                print '    %r: %r,' % ('flam.core', core)
                for name, symbols in module_map.items():
                    symbols = list(set(symbols) - set(core))
                    print '    %r: %r,' % (name, symbols)


setup(
    name='flam',
    url='http://swapoff.org/flam',
    download_url='http://swapoff.org/flam',
    version='0.0.4',
    description='A minimalist Python application framework.',
    license='BSD',
    platforms=['any'],
    packages=['flam', 'flam.web'],
    author='Alec Thomas',
    author_email='alec@swapoff.org',
    cmdclass={'build_py': build_py},
    test_suite = 'nose.collector',
    install_requires = [
        'setuptools >= 0.6b1',
        'Genshi >= 0.5',
        'simplejson >= 2.0.0',
        'Werkzeug >= 0.4',
    ],
    )
