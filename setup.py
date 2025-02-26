#!/usr/bin/env python

"""A setuptools based setup module.
See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / 'README.md').read_text(encoding='utf-8')

# Arguments marked as "Required" below must be included for upload to PyPI.
# Fields marked as "Optional" may be commented out.

setup(name='plusplus',
      version='0.3',
      description='plusplus202',
      author='Jonathan Campbell',
      author_email='jonathan@campbelljc.com',
      url='https://www.github.com/campbelljc/plusplus/',
      packages=['plusplus'],
     )