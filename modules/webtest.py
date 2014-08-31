import module
from flask import Response


@module.app.route('/')
def index():
    return Response('I am webtest')