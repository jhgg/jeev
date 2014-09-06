import logging
from gevent.pywsgi import WSGIServer
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule

logger = logging.getLogger('jeev.web')


class Web(object):
    """
        Jeev's WSGI server. Routes requests to their appropriate module. See `jeev.module.Module.app` for more
        details.
    """
    _url_map = Map([
        Rule('/<module>/', endpoint='module', defaults={'rest': ''}),
        Rule('/<module>/<path:rest>', endpoint='module')
    ])

    def __init__(self, jeev, opts):
        self._jeev = jeev
        self._opts = opts
        self._bind_addr = self._opts['listen_host'], int(self._opts['listen_port'])
        self._server = WSGIServer(self._bind_addr, self._wsgi_app)

    def _wsgi_app(self, environ, start_response):
        urls = self._url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
            handler = getattr(self, '_handle_%s' % endpoint)
            return handler(args, environ, start_response)

        except HTTPException, e:
            return e(environ, start_response)

    def _handle_module(self, args, environ, start_response):
        module = self._jeev.modules.get_module(args['module'])

        if module and module.is_web:
            original_script_name = environ.get('SCRIPT_NAME', '')
            environ['SCRIPT_NAME'] = original_script_name + '/' + args['module']
            environ['PATH_INFO'] = args['rest']
            return module.app(environ, start_response)

        return NotFound()(environ, start_response)

    def start(self):
        logger.info("Starting web server on %s:%s", *self._bind_addr)
        self._server.start()

    def stop(self):
        logger.info("Stopping web server on %s:%s", *self._bind_addr)
        self._server.stop()