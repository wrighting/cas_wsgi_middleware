import logging
from cgi import parse_qs
from urllib import quote, urlencode, unquote_plus
from urlparse import urlparse
import requests
import xml.dom.minidom
from werkzeug.formparser import parse_form_data

__all__ = ['CASMiddleware']


# Session keys
CAS_USERNAME = 'cas.username'
CAS_GROUPS = 'cas.groups'
CAS_TOKEN = 'cas.token'

CAS_ORIGIN = 'cas.origin'


def get_original_url(environ):
    url = environ['wsgi.url_scheme'] + '://'

    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME']

        if environ['wsgi.url_scheme'] == 'https':
            if environ['SERVER_PORT'] != '443':
                url += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
                url += ':' + environ['SERVER_PORT']

    url += quote(environ.get('SCRIPT_NAME',''))
    url += quote(environ.get('PATH_INFO',''))

    if environ.get('QUERY_STRING'):
        params = parse_qs(environ['QUERY_STRING'])
        
        for k in ('ticket',): 
            if k in params: 
              del params[k]
        if params:
            url += '?' + urlencode(params, doseq=True)

    return url


class CASMiddleware(object):

    casNamespaceUri = 'http://www.yale.edu/tp/cas'
    samlpNamespaceUri = 'urn:oasis:names:tc:SAML:2.0:protocol'
    samlNamespaceUri = 'urn:oasis:names:tc:SAML:2.0:assertion'


    def __init__(self, application, cas_root_url, entry_page = '/', logout_url = '/logout', logout_dest = '', protocol_version = 2, casfailed_url=None):
        self._application = application
        self._root_url = cas_root_url
        self._login_url = cas_root_url + '/login'
        self._logout_url = logout_url
        self._sso_logout_url = cas_root_url + '/logout'
        self._logout_dest = logout_dest
        self._entry_page = entry_page
        self._protocol = protocol_version
        self._casfailed_url = casfailed_url
        self._session = None


    def _validate(self, environ, ticket):
        
        if self._protocol == 2:
          validate_url = self._root_url + '/serviceValidate'
        elif self._protocol == 3:
          validate_url = self._root_url + '/p3/serviceValidate'

        service_url = get_original_url(environ)
        r = requests.get(validate_url, params = {'service': service_url, 'ticket': ticket})
        result = r.text
        logging.debug(result)
        dom = xml.dom.minidom.parseString(result)
        username = None
        nodes = dom.getElementsByTagNameNS(self.casNamespaceUri, 'authenticationSuccess')
        if nodes:
            successNode = nodes[0]
            nodes = successNode.getElementsByTagNameNS(self.casNamespaceUri, 'user')
            if nodes:
                userNode = nodes[0]
                if userNode.firstChild is not None:
                    username = userNode.firstChild.nodeValue
                    self._set_session_var(CAS_USERNAME, username)
            nodes = successNode.getElementsByTagNameNS(self.casNamespaceUri, 'memberOf')
            if nodes:
                groupName = []
                for groupNode in nodes:
                  if groupNode.firstChild is not None:
                    groupName.append(groupNode.firstChild.nodeValue)
                if self._protocol == 2:
                #Common but non standard extension - only one value - concatenated on the server
                    self._set_session_var(CAS_GROUPS, groupName[0])
                elif self._protocol == 3:
                #So that the value is the same for version 2 or 3
                    self._set_session_var(CAS_GROUPS, '[' + ', '.join(groupName) + ']')
        dom.unlink()

        return username

    def _is_single_sign_out(self, environ):
      logging.debug("Testing for SLO")
      if environ['REQUEST_METHOD'] == 'POST':
        current_url = environ.get('PATH_INFO','')
        origin = self._entry_page
        logging.debug("Testing for SLO:" + current_url + " vs " + origin)
        if current_url == origin:
          try:
            form = parse_form_data(environ)[1]
            request_body = form['logoutRequest']
            request_body = unquote_plus(request_body).decode('utf8') 
            dom = xml.dom.minidom.parseString(request_body)
            nodes = dom.getElementsByTagNameNS(self.samlpNamespaceUri, 'SessionIndex')
            if nodes:
              sessionNode = nodes[0]
              if sessionNode.firstChild is not None:
                sessionId = sessionNode.firstChild.nodeValue
                logging.info("Received SLO request for:" + sessionId)
                return True
          except (Exception):
            logging.warning("Exception parsing post")
            logging.exception("Exception parsing post:" + request_body)
      return False

    def _is_logout(self, environ):
      path = environ.get('PATH_INFO','')
      logging.debug("Logout check:" + str(path) + " vs " + str(self._logout_url))
      if self._logout_url != '' and self._logout_url == path:
        return True
      return False

    def __call__(self, environ, start_response):
        self._get_session(environ)
        if self._has_session_var(CAS_USERNAME):
            self._set_values(environ)
            if self._is_logout(environ):
              self._do_session_logout()
              dest = self._get_logout_redirect_url()
              start_response('302 Moved Temporarily', [
                    ('Location', 
                     '%s?service=%s' % (self._sso_logout_url,
                                        quote(dest)))
                    ])
              return []
            return self._application(environ, start_response)
        else:
            query_string = environ.get('QUERY_STRING', '')
            params = parse_qs(query_string)
            logging.debug('Session not authenticated' + str(self._session))
            if params.has_key('ticket'):
                # Have ticket, validate with CAS server
                ticket = params['ticket'][0]

                service_url = get_original_url(environ)

                username = self._validate(environ, ticket)

                if username is not None:
                    # Validation succeeded, redirect back to app
                    logging.debug('Validated ' + username)
                    self._set_session_var(CAS_ORIGIN, service_url)
                    self._set_session_var(CAS_TOKEN, ticket)
                    self._save_session()
                    start_response('302 Moved Temporarily', [
                        ('Location', service_url)
                        ])
                    return []
                else:
                    # Validation failed (for whatever reason)
                    return self._casfailed(environ, service_url, start_response)
            else:
                #Check for single sign out
                if (self._is_single_sign_out(environ)):
                  logging.debug('Single sign out request received')
                  start_response('200 OK', [])
                  return []
                logging.debug('Does not have ticket redirecting')
                service_url = get_original_url(environ)
                start_response('302 Moved Temporarily', [
                    ('Location',
                     '%s?service=%s' % (self._login_url,
                                        quote(service_url)))
                    ])
                return []
                    
    def _get_session(self, environ):
        self._session = environ['beaker.session']

    def _has_session_var(self, name):
        return name in self._session 

    def _remove_session_var(self, name):
        del self._session[name] 

    def _set_session_var(self, name, value):
        self._session[name] = value
        logging.debug("Setting session:" + name + " to " + value)

    def _get_session_var(self, name):
        return (self._session[name])

    def _save_session(self):
        logging.debug("Saving session:" + str(self._session))
        self._session.save()
    
    def _do_session_logout(self):
        self._remove_session_var(CAS_USERNAME)
        self._remove_session_var(CAS_GROUPS)
        self._save_session()
        self._session.delete()

    def _get_logout_redirect_url(self):
        dest = self._logout_dest
        if dest == '' and self._has_session_var(CAS_ORIGIN):
          dest = self._get_session_var(CAS_ORIGIN)
        logging.debug("Log out dest:" + dest)
        parsed = urlparse(dest)
        if parsed.path == self._logout_url:
          dest = self._sso_logout_url
        logging.debug("Log out redirecting to:" + dest)
        return dest

    #Communicate values to the rest of the application
    def _set_values(self, environ):
        username = self._get_session_var(CAS_USERNAME)
        logging.debug('Session authenticated for ' + username)
        environ['AUTH_TYPE'] = 'CAS'
        environ['REMOTE_USER'] = str(username)

    def _casfailed(self, environ, service_url, start_response):
        if self._casfailed_url is not None:
            start_response('302 Moved Temporarily', [
                ('Location', self._casfailed_url)
                ])
            return []
        else:
            # Default failure notice
            start_response('401 Unauthorized', [('Content-Type', 'text/plain'), ('WWW-Authenticate','CAS casUrl="' + self._root_url + '" service="' + service_url + '"')])
            return ['CAS authentication failed\n']

