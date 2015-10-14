import logging
from cas.casmiddleware import CASMiddleware
import time
from django.http import HttpResponse
from django.contrib.auth import logout
from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

logger = logging.getLogger(__name__)


class DjangoCAS(CASMiddleware):

    def _is_session_expired(self):
#        
#          self._session_store.delete(self._session)
#          self._get_session(request)
#          return True
        return False

    def _remove_session_by_ticket(self, ticket_id):
        logger.debug("Nothing to do")

    def loadSettings(self, filename = None, ignored_callback = None):
        self.initialize(cas_root_url = settings.CAS_SERVICE, logout_url = settings.LOGOUT_URL, logout_dest = settings.CAS_LOGOUT_DESTINATION, protocol_version = settings.CAS_VERSION, casfailed_url = settings.CAS_FAILURE_PAGE, entry_page = settings.ENTRY_PAGE, ignore_redirect = settings.IGNORE_REDIRECT, ignored_callback = ignored_callback, gateway_redirect = settings.GATEWAY_REDIRECT, cas_private_key = settings.PRIVATE_KEY)

    def process_request(self, request):

        if not self._root_url:
            self.loadSettings()

        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The Django remote user auth middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE_CLASSES setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the RemoteUserMiddleware class.")

        self._get_session(request)
        request_method = request.method
        form = None
        if request_method == "POST":
            form = request.POST
        path = request.path_info
        request_url = request.build_absolute_uri()
        params = None
        if request_method == "GET":
            params = request.GET
        resp = self._process_request(request_method, request_url, path, params, form)
        logging.debug(str(resp))
        if resp:
            if 'set_values' in resp:
                self._set_values(request)
                return None
            if 'ignore_callback' in resp and response['ignore_callback'] == True:
                  return self._ignored_callback(environ, start_response)

            response = HttpResponse(status = int(resp['status'][0:3]), reason = resp['status'][4:])
            for name in ['Location', 'Content-Type', 'WWW-Authenticate']:
                if name in resp['headers']:
                    response[name] = resp['headers'][name]
            if 'data' in resp:
                response.write(resp.data)
            if 'logout' in resp:
                logout(request)
            return response
        else:
            return None

    def _get_session(self, request):
        self._session = request.session

    def _has_session_var(self, name):
        return name in self._session 

    def _remove_session_var(self, name):
        if name in self._session:
            del self._session[name] 

    def _set_session_var(self, name, value):
        self._session[name] = value
        logger.debug("Setting session:" + name + " to " + value)

    def _get_session_var(self, name):
        if name in self._session:
          return (self._session[name])
        else:
          return None

    def _save_session(self):
        logger.debug("No need to save session")

    def _delete_session(self):
        self._session.flush()
    
    #Communicate values to the rest of the application
    def _set_values(self, request):
        username = self._get_session_var(self.CAS_USERNAME)
        logger.debug('Session authenticated for ' + username)
        # We are seeing this user for the first time in this session, attempt
        # to authenticate the user.
        user = auth.authenticate(remote_user=username)
        if user:
            # User is valid.  Set request.user and persist user in the session
            # by logging the user in.
            request.user = user
            auth.login(request, user)
#        request['META']['AUTH_TYPE'] = 'CAS'
#        request['META']['REMOTE_USER'] = str(username)
        request.session['AUTH_TYPE'] = 'CAS'
        request.session['PASSWORD'] = str(self._get_encrypted_session_var(self.CAS_PASSWORD))
        request.session[self._group_environ] = str(self._get_session_var(self.CAS_GROUPS))

CASMiddleware.register(DjangoCAS)
