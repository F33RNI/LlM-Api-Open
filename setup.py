"""
Copyright (c) 2024 Fern Lane

This file is part of LlM-Api-Open (LMAO) project.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import pathlib
from pathlib import Path

from setuptools import find_packages, setup

# Include other files
data_files = ["LICENSE", "README.md"]
data_files += [str(file) for file in pathlib.Path(os.path.join("src", "lmao", "chatgpt")).glob("*.py")]
data_files += [str(file) for file in pathlib.Path(os.path.join("src", "lmao", "chatgpt")).glob("*.js")]

# Parse version from _version.py file
with open(os.path.join("src", "lmao", "_version.py"), "r", encoding="utf-8") as file:
    version = file.read().strip().split("__version__")[-1].split('"')[1]

setup(
    name="llm-api-open",
    version=version,
    license="MIT License",
    author="Fern Lane",
    description="Unofficial open APIs for popular LLMs with self-hosted redirect capability",
    packages=find_packages("src"),
    package_dir={"": "src"},
    data_files=[("", data_files)],
    include_package_data=True,
    url="https://github.com/F33RNI/LlM-Api-Open",
    project_urls={"Bug Report": "https://github.com/F33RNI/LlM-Api-Open/issues/new"},
    entry_points={
        "console_scripts": ["lmao = lmao.main:main"],
    },
    install_requires=[
        "selenium>=4.18.1",
        "undetected-chromedriver>=3.5.5",
        "beautifulsoup4>=4.12.3",
        "markdownify>=0.11.6",
        "Flask>=3.0.2",
    ],
    long_description=Path.open(Path("README.md"), encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    py_modules=["llm-api-open"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Framework :: Flask",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: JavaScript",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
