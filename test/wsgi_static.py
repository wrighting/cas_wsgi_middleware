import os
from werkzeug.wsgi import SharedDataMiddleware
from beaker.middleware import SessionMiddleware
import config
from cas import CASMiddleware

def app(environ, start_response):
    """Simplest possible application object"""
    data = 'Hello, World!\n'
    status = '200 OK'
    response_headers = [
        ('Content-type','text/plain'),
        ('Content-Length', str(len(data)))
    ]
    start_response(status, response_headers)
    return iter([data])

app = SharedDataMiddleware(app, {
    '/static': os.path.join(os.path.dirname(__file__), 'static')
})

if config.CAS_SERVICE != '':
  app = CASMiddleware(app, config.CAS_SERVICE, config.CAS_LOGOUT_PAGE, config.CAS_LOGOUT_DESTINATION, config.CAS_VERSION, config.CAS_FAILURE_PAGE)
  app = SessionMiddleware(app, config.session_opts)
