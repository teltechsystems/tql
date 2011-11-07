import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "tql",
    version = "0.0.1",
    author = "Teltech Systems",
    author_email = "development@teltechcorp.com",
    description = ("Provides SQL wrapper on top of Django models, similar to Facebook's FQL"),
    url = "https://github.com/teltechsystems/tql",
    packages=['tql'],
    long_description=read('README.markdown'),
)