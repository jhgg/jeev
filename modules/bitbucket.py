import module
from flask import request, Response

@module.app.route('/webhook', methods=['POST'])
def bitbucket_webhook():
    pass