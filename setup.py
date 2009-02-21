import fileinput
import os
import sys
import textwrap

from distutils.command.build_py import build_py as _build_py
from distutils import log
from distutils.core import setup


class build_py(_build_py):
    """Update auto import map in flam/__init__.py before building."""

    def run(self):
        log.info('updating auto import map in flam/__init__.py')
        module_map = self.find_modules()
        self.update_auto_imports(module_map)
        _build_py.run(self)

    def find_modules(self):
        module_map = {}
        for dir, dirs, files in os.walk('flam'):
            modules = [os.path.join(dir, file).replace('.py', '').replace('/', '.')
                       for file in files if not file.startswith('_') and file.endswith('.py')]
            for name in modules:
                module = __import__(name, {}, {}, ['.'])
                module_map[name] = module.__all__
        return module_map

    def update_auto_imports(self, module_map):
        inside = 0

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
                for name, symbols in module_map.items():
                    print '    %r: %r,' % (name, symbols)


setup(
    name='flam',
    url='http://swapoff.org/flam',
    download_url='http://swapoff.org/flam',
    version='0.0.1',
    description='A minimalist Python application framework.',
    license='BSD',
    platforms=['any'],
    packages=['flam'],
    author='Alec Thomas',
    author_email='alec@swapoff.org',
    cmdclass={'build_py': build_py},
    )
