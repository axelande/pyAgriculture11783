from setuptools import setup, find_packages
from Cython.Build import cythonize

# Read requirements
with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name="pyAgriculture11783",
    version="0.2.0",
    packages=find_packages(),
    package_data={'schemas': ['schemas']},
    install_requires=required,
    ext_modules=cythonize('pyAgriculture/cython_agri.pyx'),
)