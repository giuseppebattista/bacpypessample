import os
from distutils.core import setup

#
#   read
#

def read(fname):
    """Utility function to read the contents of the README.txt file."""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

#
#   __main__
#

setup(name='BACpypes',
    version='0.10',
    description='BACnet Python Library',
    author='Joel Bender',
    author_email='joel@carrickbender.com',
    url='http://bacpypes.sourceforge.net/',
    packages=['bacpypes'],
    long_description=open('README.txt').read(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
        "Topic :: Utilities",
        ],
    )

