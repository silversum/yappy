#!/usr/bin/env python

from importlib.machinery import SourceFileLoader

from setuptools import setup


NAME = "yappy"

PYTHON_VERSION = "~=3.9.0"

REQUIRES = [
    "pydantic~=1.8.2",
    "click~=8.0.3",
]


_version_loader = SourceFileLoader("__version__", f"{NAME}/__version__.py")
VERSION = str(_version_loader.load_module().__version__)


DESCRIPTION = (
    "Yet another way to turn your pydantic model into console application."
)

LONG_DESCRIPTION = open("README.md").read()


setup(
    name=NAME,
    version=VERSION,
    author="Artem Zakhov",
    author_email="solutio.sciurus@gmail.com",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/silversum/yappy",

    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Typing :: Typed",
    ],

    python_requires=PYTHON_VERSION,
    install_requires=REQUIRES,

    packages=[NAME],
    include_package_data=True,
    # make package compatible with PEP 561:
    # https://mypy.readthedocs.io/en/latest/installed_packages.html#creating-pep-561-compatible-packages
    package_data={NAME: ["py.typed"]},
    zip_safe=False,
)
