# Copyright 2021 The streetview-greenery authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# based on https://github.com/pypa/sampleproject - MIT License

import re
from setuptools import setup, find_packages
from os import path
from io import open


def get_long_description():
    """Get project description based on README"""
    here = path.abspath(path.dirname(__file__))

    # Get the long description from the README file
    with open(path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()

    # remove emoji
    long_description = re.sub(r"\:[a-z_]+\:", "", long_description)

    return long_description


setup(
    name='greenstreet',
    version="1.0.0",
    description='Streetview Greenery',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/qubixes/streetview-greenery',
    author='Raoul Schram',
    author_email='',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='greenery streetview machine learning',
    packages=find_packages(exclude=['docs', 'scripts']),
    python_requires='~=3.6',
    install_requires=[
        'Pillow',
        'numpy',
        'scipy',
        'tqdm',
        'gdal',
        'folium',
        'pybase64',
        'matplotlib',
        'tensorflow',
        'requests',
        'matplotlib',
        'pykrige',
        'setuptools',
    ],
#     extras_require={},
    entry_points={
        'console_scripts': [
            'greenstreet = greenstreet.__main__:main',
        ],
    },
    project_urls={
        'Source': 'https://github.com/UtrechtUniversity/streetview-greenery',
    },
)
