try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name='flam',
    url='http://swapoff.org/flam',
    download_url='http://swapoff.org/flam',
    version='0.0.5',
    description='A minimalist Python application framework.',
    license='BSD',
    platforms=['any'],
    packages=['flam', 'flam.web'],
    author='Alec Thomas',
    author_email='alec@swapoff.org',
    test_suite = 'nose.collector',
    test_requires = [
        'Mock >= 0.5.0',
    ],
    install_requires = [
        'setuptools >= 0.6b1',
        'Genshi >= 0.5',
        'simplejson >= 2.0.0',
        'Werkzeug >= 0.4',
        'DirectoryQueue >= 1.4.2',
    ],
    )
