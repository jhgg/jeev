import os
import jeev
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="jeev",
    version=jeev.version.split('-')[0] + 'b0',
    author="Jacob Heinz",
    author_email="me@jh.gg",
    description="A simple chat bot, at your service.",
    license="MIT",
    keywords="chat slack bot irc jeev",
    url="https://github.com/jhgg/jeev",
    packages=find_packages(exclude=['modules']),
    install_requires=[
        'certifi==14.5.14',
        'coloredlogs==1.0.1',
        'cssselect==0.9.1',
        'Flask==0.10.1',
        'geopy==1.1.3',
        'gevent==1.0.2',
        'greenlet==0.4.7',
        'humanfriendly==1.27',
        'itsdangerous==0.24',
        'Jinja2==2.7.3',
        'lxml==3.3.6',
        'MarkupSafe==0.23',
        'pytz==2014.4',
        'requests==2.7.0',
        'six==1.9.0',
        'slackclient==0.15',
        'websocket-client==0.32.0',
        'Werkzeug==0.9.6',
        'wheel==0.38.1',
    ],
    include_package_data=True,
    zip_safe=False,
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