import logging
from gevent.pywsgi import WSGIServer
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule

logger = logging.getLogger('jeev.web')


class Web(object):
    url_map = Map([
        Rule('/<module>/', endpoint='module', defaults={'rest': ''}),
        Rule('/<module>/<path:rest>', endpoint='module')
    ])

    def __init__(self, jeev):
        self.jeev = jeev
        self.opts = getattr(jeev.config, 'webOpts', {})
        self.server = WSGIServer((self.opts['listenHost'], self.opts['listenPort']), self.wsgi_app)

    def wsgi_app(self, environ, start_response):
        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
            handler = getattr(self, 'handle_%s' % endpoint)
            return handler(args, environ, start_response)

        except HTTPException, e:
            return e(environ, start_response)

    def handle_module(self, args, environ, start_response):
        module = self.jeev.modules.get_module(args['module'])

        if module and module.is_web:
            original_script_name = environ.get('SCRIPT_NAME', '')
            environ['SCRIPT_NAME'] = original_script_name + '/' + args['module']
            environ['PATH_INFO'] = args['rest']
            return module.app(environ, start_response)

        return NotFound()(environ, start_response)

    def start(self):
        self.server.start()

    def stop(self):
        self.server.stop()