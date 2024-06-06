#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

requirements = [
    "rosco==2.9.0",
    "openfast_toolbox==3.5.1",
    "floris==3.6.0",
    "flasc==1.5.1",
]

test_requirements = [ ]

setup(
    author="Bart M. Doekemeijer",
    author_email='bart.doekemeijer@shell.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="ZeroMQ-based WFC interface demonstration in FAST.Farm",
    install_requires=requirements,
    long_description="This repository contains a FAST.Farm simulation in which the turbines are controlled from a Python-based wind farm control script. The interface between FAST.Farm and Python is facilitated by the ZeroMQ functionality available in ROSCO.",
    include_package_data=True,
    keywords='wfc_zmq_interface_demo',
    name='wfc_zmq_interface_demo',
    packages=find_packages(include=[]),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/tbd...',
    version='0.1.0',
    zip_safe=False,
)
