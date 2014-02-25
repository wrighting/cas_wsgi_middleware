import os
import logging
from werkzeug.wrappers import Request, Response
from werkzeug.wsgi import SharedDataMiddleware
from beaker.middleware import SessionMiddleware

import config
from cas import CASMiddleware

class Shortly(object):

#Nothing to do
#    def __init__(self, config):

    def dispatch_request(self, request, environ):
        data ='Hello ' + environ['REMOTE_USER'] + '!'
        data += '<a href="/logout">Logout</a>'
        return Response(data, headers = { ('Content-type', 'text/html')})

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request, environ)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


def create_app(with_static=True):
    app = Shortly()
    
    if with_static:
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/static':  os.path.join(os.path.dirname(__file__), 'static')
        })

        if config.CAS_SERVICE != '':
          app.wsgi_app = CASMiddleware(app.wsgi_app, cas_root_url = config.CAS_SERVICE, logout_url = config.CAS_LOGOUT_PAGE, logout_dest = config.CAS_LOGOUT_DESTINATION, protocol_version = config.CAS_VERSION, casfailed_url = config.CAS_FAILURE_PAGE, entry_page = '/')
          app.wsgi_app = SessionMiddleware(app.wsgi_app, config.session_opts)
    return app

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    logging.basicConfig(level=logging.DEBUG)
    app = create_app()
    run_simple(config.HOSTNAME, config.PORT, app, use_debugger=True, use_reloader=True)


