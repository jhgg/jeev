import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name = "Jeev",
    version = "0.1.0",
    author = "Jacob Heinz",
    author_email = "me@jh.gg",
    description = "A simple chat bot, at your service.",
    license = "MIT",
    keywords = "chat slack bot irc jeev",
    url = "https://github.com/jhgg/jeev",
    packages=find_packages(exclude=['modules']),
    install_requires=[
        'Flask>=0.10.1',
        'requests>=2.4.0',
        'gevent>=1.0.0'
    ],
    scripts=['bin/jeev'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Communications :: Chat",
        "Topic :: Utilities",
        "Framework :: Flask",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 2 :: Only",
        "License :: OSI Approved :: MIT License",
    ],
)