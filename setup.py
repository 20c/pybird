#!/usr/bin/env python

import ez_setup
ez_setup.use_setuptools()
from setuptools import setup

setup(name='pybird',
      version='1.0',
      description='BIRD interface handler for Python',
      author='Erik Romijn',
      author_email='eromijn@solidlinks.nl',
      test_suite='nose.collector',
      tests_require=['nose>=0.11'],
      license="BSD",
      py_modules=["pybird"],
     )