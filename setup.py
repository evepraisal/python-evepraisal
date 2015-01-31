import os

from setuptools import setup, find_packages


description = ("Tool to use in Eve Online for evaluating the value of items "
               "sourced from various places within the game and out.")

if os.path.exists('README.rst'):
    f = open('README.rst')
    try:
        long_description = f.read()
    finally:
        f.close()
else:
    long_description = description

setup(
    name='evepraisal',
    version='2.0',
    description=description,
    long_description=long_description,
    author='Kevin McDonald',
    author_email='k3vinmcdonald@gmail.com',
    packages=find_packages(exclude=["tests"]),
    license='MIT',
    install_requires=[
        'flask',
        'Flask-Cache',
        'Flask-Babel',
        'flask_openid',
        'flask-sqlalchemy',
        'sqlalchemy',
        'alembic',
        'pylibmc',
        'evepaste',
    ],
    zip_safe=False,
)
