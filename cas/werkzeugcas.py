import logging
from werkzeug.formparser import parse_form_data
from werkzeug.wrappers import Request,Response
from cas.casmiddleware import CASMiddleware
import time

logger = logging.getLogger(__name__)

class WerkzeugCAS(CASMiddleware):

    @classmethod
    def fromConfig(self, application, fs_session_store, ignored_callback = None, filename = None):

        instance = self()
        instance.loadSettings(filename, ignored_callback)
        instance._application = application
        instance._session_store = fs_session_store
        instance._ignored_callback = ignored_callback

        return (instance)

    def _is_session_expired(self):
#        
#          self._session_store.delete(self._session)
#          self._get_session(request)
#          return True
        return False

    def _remove_session_by_ticket(self, ticket_id):
      sessions = self._session_store.list()
      for sid in sessions:
        session = self._session_store.get(sid)
        logger.debug("Checking session:" + str(session))
        if self.CAS_TOKEN in session and session[self.CAS_TOKEN] == ticket_id:
          logger.info("Removed session for ticket:" + ticket_id)
          self._session_store.delete(session)

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = Response('')
        self._get_session(request)
        request_method = environ['REQUEST_METHOD']
        form = parse_form_data(environ)[1]
        path = environ.get('PATH_INFO','')
        request_url = request.url
        params = request.args
        resp = self._process_request(request_method, request_url, path, params, form)
        logging.debug(str(resp))
        if resp:
            if 'set_values' in resp:
                self._set_values(environ)
                return self._application(environ, start_response)
            if 'ignore_callback' in resp and response['ignore_callback'] == True:
                  return self._ignored_callback(environ, start_response)

            if 'status' in resp:
                response.status = resp['status']
            for name in ['Location', 'Content-Type', 'WWW-Authenticate']:
                if name in resp['headers']:
                    response.headers[name] = resp['headers'][name]
            if 'data' in resp:
                response['data'] = resp.data
            response.set_cookie(self.CAS_COOKIE_NAME, value = self._session.sid, max_age = None, expires = None)
            return response(environ, start_response)
        else:
            return self._application(environ, start_response)

    def _get_session(self, request):
        sid = request.cookies.get(self.CAS_COOKIE_NAME)
        if sid is None:
          self._session = self._session_store.new()
          self._set_session_var('_created_time', str(time.time()))
        else:
          self._session = self._session_store.get(sid)
        self._set_session_var('_accessed_time', str(time.time()))

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
        if self._session.should_save:
          logger.debug("Saving session:" + str(self._session))
          self._session_store.save(self._session)

    def _delete_session(self):
        self._session_store.delete(self._session)
    
    #Communicate values to the rest of the application
    def _set_values(self, environ):
        username = self._get_session_var(self.CAS_USERNAME)
        logger.debug('Session authenticated for ' + username)
        environ['AUTH_TYPE'] = 'CAS'
        environ['REMOTE_USER'] = str(username)
        environ['PASSWORD'] = str(self._get_encrypted_session_var(self.CAS_PASSWORD))
        environ[self._group_environ] = str(self._get_session_var(self.CAS_GROUPS))

CASMiddleware.register(WerkzeugCAS)
