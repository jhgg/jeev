# Jeev

Jeev is a python alternative to Github's famous Hubot, using Python+Gevent instead of Node+CoffeeScript. 

# Motivation

I got tired of Hubot's callback spaghetti, and decided to write an alternative to work with my company's slack channel.
This project is a work in progress, and is roughly documented. 

# Installing Jeev

You will need Python 2.7, and setuptools. If you want, you can install Jeev in a virtual environment.

Install jeev (and his built in modules) with pip:

    $ pip install jeev jeev-modules

This will install jeev, and his dependencies. It will also give you the `jeev` command which can be used to create
an initial jeev configuration, and run the bot. Let's create an instance of jeev in the folder "myjeev":

    $ jeev init myjeev

If you want to use jeev with heroku, or just have your Jeev instance inside of a git repository, the newly created
directory has everything you need: the configuration file, a few sample modules, a .gitignore file (so that you can safely add
everything to git).

    $ cd myjeev
    $ git init
    $ git add .
    $ git commit -m "Jeev's initial commit."

Now you can run Jeev by simply calling:

    $ jeev run

This will start Jeev using the console adapter that will read messages from stdin, and print out Jeev's responses
to stdout.

    $ jeev run
    >>> Jeev Console Adapater
    >>> Switch channel using \c channel_name
    >>> Switch user using \u user_name
    >>> Jeev will respond to the user name Jeev
    [user@test] >


# License

The MIT License (MIT)

Copyright (c) 2014 Jacob Heinz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.