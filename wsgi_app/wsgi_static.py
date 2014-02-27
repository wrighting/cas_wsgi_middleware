import wsgi_server
import os
from werkzeug.wsgi import SharedDataMiddleware
from cas import CASMiddleware
import logging
from werkzeug.contrib.sessions import FilesystemSessionStore
from werkzeug.wrappers import Response

#logging.basicConfig(level=logging.DEBUG)

#This function is called if:
# Not authenticated
# the ignore_redirect regex matches the (full) url pattern
def ignored_callback(environ, start_response):
    response = Response('{"Error":"NotAuthenticated"}')
#    response.status = '401 Unauthorized'
    response.status = '200 OK'
    response.headers['Content-Type'] = 'application/json'

    return response(environ, start_response)

application = wsgi_server.application

application = SharedDataMiddleware(application, {
    '/static': os.path.join(os.path.dirname(__file__), 'static')
})

#The URL of your CAS server - if this is set then CAS will be enabled
# e.g. https://mydomain/cas
CAS_SERVICE = ''
#This is the CAS protocol version versions 2 and 3 supported (3 is only available in CAS 4)
CAS_VERSION = 3
#A URL to use as the link to logout
CAS_LOGOUT_PAGE = '/logout'
#Where to go when you've logged out - will send you to the entry page if not set
CAS_LOGOUT_DESTINATION = ''
#A page to show if validation fails
CAS_FAILURE_PAGE = None

if CAS_SERVICE != '':
  fs_session_store = FilesystemSessionStore()
  application = CASMiddleware(application, cas_root_url = CAS_SERVICE, logout_url = CAS_LOGOUT_PAGE, logout_dest = CAS_LOGOUT_DESTINATION, protocol_version = CAS_VERSION, casfailed_url = CAS_FAILURE_PAGE, entry_page = '/static/main.html', session_store = fs_session_store, ignore_redirect = '(.*)\?datatype=', ignored_callback = ignored_callback)

