import setuptools
import os.path
import sys
from distutils.core import setup
from Cython.Build import cythonize

setup(ext_modules=cythonize('cython_agri.pyx'))
# Parse the requirements-txt file and use for install_requires in pip
with open('requirements.txt') as f:
    required = f.read().splitlines()



setuptools.setup(
    name="pyAgriculture11783",
    version="0.1.0",
    packages=setuptools.find_packages(),
    package_data={'schemas':['schemas']},
    install_requires = required
    
)
