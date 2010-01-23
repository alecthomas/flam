try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name='flam',
    url='http://swapoff.org/flam',
    download_url='http://swapoff.org/flam',
    version='0.1',
    description='A minimalist Python application framework.',
    license='BSD',
    platforms=['any'],
    py_modules=['flam'],
    author='Alec Thomas',
    author_email='alec@swapoff.org',
    test_suite = 'nose.collector',
    test_requires = [
        'nose',
        'Mock >= 0.5.0',
    ],
    install_requires = [
        'setuptools >= 0.6b1',
    ],
    )
