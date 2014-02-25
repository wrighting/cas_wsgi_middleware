import wsgi_server
import os
from werkzeug.wsgi import SharedDataMiddleware
from beaker.middleware import SessionMiddleware
import config
from cas import CASMiddleware

application = wsgi_server.application

application = SharedDataMiddleware(application, {
    '/static': os.path.join(os.path.dirname(__file__), 'static')
})

if config.CAS_SERVICE != '':
  application = CASMiddleware(application, config.CAS_SERVICE, config.CAS_LOGOUT_PAGE, config.CAS_LOGOUT_DESTINATION, config.CAS_VERSION, config.CAS_FAILURE_PAGE)
  application = SessionMiddleware(application, config.session_opts)
