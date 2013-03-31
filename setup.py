# -*- coding: utf-8 -*-

"""
shipit
~~~~~~

A curses interface to GitHub.
"""

from setuptools import setup, find_packages

from shipit import NAME, DESCRIPTION, VERSION

REQUIREMENTS = [
    "github3.py==0.5.2",
    "urwid==1.1.1",
    "x256==0.0.2",
]

setup(name=NAME,
      version=VERSION,
      author="Alejandro Gómez",
      author_email="alejandro@dialelo.com",
      url="https://github.com/alejandrogomez/shipit",
      description=DESCRIPTION,
      packages=find_packages(exclude=["tests"]),
      entry_points={
          "console_scripts": ["shipit = shipit.cli:main"]
      },
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Environment :: Console :: Curses",
          "Intended Audience :: End Users/Desktop",
          "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
          "Natural Language :: English",
          "Operating System :: POSIX :: Linux",
          "Operating System :: MacOS",
          "Programming Language :: Python :: 3",
      ],
      install_requires=REQUIREMENTS,)
