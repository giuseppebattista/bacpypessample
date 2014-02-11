#!/bin/bash

# python setup.py bdist_egg upload
sudo python -c "import setuptools; execfile('setup.py')" bdist_egg upload
