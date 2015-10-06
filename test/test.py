import os
import logging
from werkzeug.wrappers import Request, Response
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.contrib.sessions import FilesystemSessionStore
from pprint import pformat

from ConfigParser import ConfigParser

from cas.werkzeugcas import WerkzeugCAS

#This function is called if:
# Not authenticated
# the ignore_redirect regex matches the (full) url pattern
def ignored_callback(environ, start_response):
    response = Response('{"Error":"NotAuthenticated"}')
#    response.status = '401 Unauthorized'
    response.status = '200 OK'
    response.headers['Content-Type'] = 'application/json'

    return response(environ, start_response)

class MyApp(object):

#Nothing to do
#    def __init__(self, config):

    def dispatch_request(self, request, environ):
        user = environ.get('REMOTE_USER', 'guest')
        data ='Hello ' + user + '!'
        if 'REMOTE_USER' in environ:
          data += '<a href="/logout">Logout</a>'
        if 'HTTP_CAS_MEMBEROF' in environ:
          data += environ['HTTP_CAS_MEMBEROF']
        for keys,values in environ.items():
          print(keys)
          print(values)
        data += '%s<br/>' % pformat(environ)
        data += '%s<br/>' % pformat(request)
        return Response(data, headers = { ('Content-type', 'text/html')})

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request, environ)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


def create_app(with_static=True):
    app = MyApp()
    
    if with_static:
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/static':  os.path.join(os.path.dirname(__file__), 'static')
        })

        fs_session_store = FilesystemSessionStore()
        app.wsgi_app = WerkzeugCAS.fromConfig(app.wsgi_app, fs_session_store, ignored_callback = ignored_callback, filename = 'test.cfg')
    return app

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    logging.basicConfig(level=logging.DEBUG)
    config = ConfigParser(allow_no_value = True)
    config.read('test.cfg')
    app = create_app()

    run_simple(config.get('Test','HOSTNAME'), config.getint('Test','PORT'), app, use_debugger=True, use_reloader=True)


