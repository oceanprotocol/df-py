#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

"""The setup script."""

#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

from setuptools import find_packages, setup

# Installed by pip install ocean-provider
# or pip install -e .
install_requirements = [
    "coverage",
    "ccxt==3.0.84",
    "eciespy",
    "web3",
    "py-solc-x",
    "enforce_typing",
    "mypy",
    "numpy",
    "pandas",
    "pylint",
    "pytest",
    "pytest-env",
    "requests",
    "scipy",
    "types-requests",
    "bumpversion",
    "black",
    "ocean-contracts",
]

# Required to run setup.py:
setup_requirements = ["pytest-runner"]

setup(
    author="oceanprotocol",
    author_email="devops@oceanprotocol.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.8",
    ],
    description="DF PY lib.",
    install_requires=install_requirements,
    license="Apache Software License 2.0",
    include_package_data=True,
    packages=find_packages(
        include=[
            "df_py",
            "build",
            "contracts",
            "data",
            "interfaces",
            "reports",
            "scripts",
        ]
    ),
    setup_requires=setup_requirements,
    test_suite="tests",
    url="https://github.com/oceanprotocol/provider-py",
    # fmt: off
    # bumpversion needs single quotes
    version='0.0.4',
    # fmt: on
    zip_safe=False,
)
