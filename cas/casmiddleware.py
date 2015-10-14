import logging
from cgi import parse_qs
from urllib import quote, urlencode, unquote_plus
from urlparse import urlparse
import requests
import xml.dom.minidom
import re
from ConfigParser import ConfigParser
import rsa
from abc import ABCMeta, abstractmethod

logger = logging.getLogger(__name__)


class CASMiddleware(object):

    __metaclass__ = ABCMeta

    casNamespaceUri = 'http://www.yale.edu/tp/cas'
    samlpNamespaceUri = 'urn:oasis:names:tc:SAML:2.0:protocol'
    samlNamespaceUri = 'urn:oasis:names:tc:SAML:2.0:assertion'

    # Session keys
    CAS_USERNAME = 'cas.username'
    CAS_GROUPS = 'cas.groups'
    CAS_TOKEN = 'cas.token'
    CAS_GATEWAY = 'cas.gateway'

    CAS_ORIGIN = 'cas.origin'

    CAS_COOKIE_NAME = 'cas.cookie'

    CAS_PASSWORD = 'cas.ldap.password'

    _root_url = None

    def __init__(self):
        logging.debug("Initializing middleware")

    def initialize(self, cas_root_url, entry_page = '/', effective_url = None, logout_url = '/logout', logout_dest = '', protocol_version = 2, casfailed_url=None, ignore_redirect = None, ignored_callback = None, gateway_redirect = None, group_separator = ';', group_environ = 'HTTP_CAS_MEMBEROF', cas_private_key = None, application = None):
        self._root_url = cas_root_url
        self._login_url = cas_root_url + '/login'
        self._logout_url = logout_url
        self._sso_logout_url = cas_root_url + '/logout'
        self._logout_dest = logout_dest
        self._entry_page = entry_page
        self._effective_url = effective_url
        self._protocol = protocol_version
        self._casfailed_url = casfailed_url
        self._session = None
        self._cookie_expires = False
        if ignore_redirect is not None:
          self._ignore_redirect = re.compile(ignore_redirect)
          self._ignored_callback = ignored_callback
        else:
          self._ignore_redirect = None
        if gateway_redirect is not None:
          self._gateway_redirect = re.compile(gateway_redirect)
        else:
          self._gateway_redirect = None
        self._group_separator = group_separator
        self._group_environ = group_environ
        keydata = None
        if cas_private_key and cas_private_key != '':
            with open(cas_private_key) as privatefile:
                keydata = privatefile.read()
            self._cas_private_key = rsa.PrivateKey.load_pkcs1(keydata)

    def loadSettings(self, filename = None, ignored_callback = None):
        if filename == None:
            filename = 'cas.cfg'
        config = ConfigParser(allow_no_value = True)
        config.read(filename)
        self.initialize(cas_root_url = config.get('CAS','CAS_SERVICE'), logout_url = config.get('CAS','CAS_LOGOUT_PAGE'), logout_dest = config.get('CAS','CAS_LOGOUT_DESTINATION'), protocol_version = config.getint('CAS','CAS_VERSION'), casfailed_url = config.get('CAS','CAS_FAILURE_PAGE'), entry_page = config.get('CAS','ENTRY_PAGE'), ignore_redirect = config.get('CAS','IGNORE_REDIRECT'), ignored_callback = ignored_callback, gateway_redirect = config.get('CAS','GATEWAY_REDIRECT'), cas_private_key = config.get('CAS', 'PRIVATE_KEY'))

    @classmethod
    def fromConfig(self, ignored_callback = None, filename = None):

        instance = self()
        instance.loadSettings(filename, ignored_callback)
        instance._ignored_callback = ignored_callback

        return (instance)

    def _validate(self, service_url, ticket):
        
        if self._protocol == 2:
          validate_url = self._root_url + '/serviceValidate'
        elif self._protocol == 3:
          validate_url = self._root_url + '/p3/serviceValidate'

        r = requests.get(validate_url, params = {'service': service_url, 'ticket': ticket})
        result = r.text.encode('utf8')
        logger.debug(result)
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
                    self._set_session_var(self.CAS_USERNAME, username)
            nodes = successNode.getElementsByTagNameNS(self.casNamespaceUri, 'memberOf')
            if nodes:
                groupName = []
                for groupNode in nodes:
                  if groupNode.firstChild is not None:
                    groupName.append(groupNode.firstChild.nodeValue)
                if self._protocol == 2:
                #Common but non standard extension - only one value - concatenated on the server
                    self._set_session_var(self.CAS_GROUPS, groupName[0])
                elif self._protocol == 3:
                #So that the value is the same for version 2 or 3
                    self._set_session_var(self.CAS_GROUPS, '[' + self._group_separator.join(groupName) + ']')
            nodes = successNode.getElementsByTagNameNS(self.casNamespaceUri, 'credential')
            if nodes:
                credNode = nodes[0]
                if credNode.firstChild is not None:
                    cred64 = credNode.firstChild.nodeValue
                    if self._cas_private_key:
                        credential = cred64.decode('base64')
                        pw = rsa.decrypt(credential, self._cas_private_key)
                        self._set_encrypted_session_var(self.CAS_PASSWORD, pw)
                    else:
                        logger.error('No private key set. Unable to decrypt password.')
        dom.unlink()

        return username

    @abstractmethod
    def _is_session_expired(self):
#        
        return False

    @abstractmethod
    def _remove_session_by_ticket(self, ticket_id):
      logger.debug("Removing session id:" + str(ticket_id))

    def _parse_logout_request(self, request_body):
        isLogout = False
        request_body = unquote_plus(request_body).decode('utf8') 
        try:
            dom = xml.dom.minidom.parseString(request_body)
            nodes = dom.getElementsByTagNameNS(self.samlpNamespaceUri, 'SessionIndex')
            if nodes:
              sessionNode = nodes[0]
              if sessionNode.firstChild is not None:
                sessionId = sessionNode.firstChild.nodeValue
                logger.info("Received SLO request for:" + sessionId)
                self._remove_session_by_ticket(sessionId)
                isLogout = True
        except (Exception):
            logger.warning("Exception parsing post")
            logger.exception("Exception parsing post:" + request_body)
        return(isLogout)

    def _is_single_sign_out(self, request_method, current_url, form):
      logger.debug("Testing for SLO")
      if request_method == 'POST':
        if current_url == self._entry_page:
          try:
            request_body = form['logoutRequest']
            logger.debug("POST:" + str(request_body))
            return self._parse_logout_request(request_body)
          except (Exception):
            logger.warning("Exception parsing post")
            logger.exception("Exception parsing post:" + request_body)
      return False

    def _is_logout(self, path):
      logger.debug("Logout check:" + str(path) + " vs " + str(self._logout_url))
      if self._logout_url != '' and self._logout_url == path:
        return True
      return False


    def _process_request(self, request_method, request_url, path, params, form):
        response = { 'status': '', 'headers': {} }

        if self._has_session_var(self.CAS_USERNAME) and not self._is_session_expired():
            if self._is_logout(path):
              self._do_session_logout()
              response = self._get_logout_redirect_url()
              response['logout'] = True
              return response
            response['set_values'] = True
            return response
        else:
            logger.debug('Session not authenticated' + str(self._session))
            if params.has_key('ticket'):
                # Have ticket, validate with CAS server
                ticket = params['ticket']

                service_url = self._effective_url or request_url

                service_url = re.sub(r".ticket=" + ticket, "", service_url)
                logger.debug('Service URL' + service_url)

                username = self._validate(service_url, ticket)

                if username is not None:
                    # Validation succeeded, redirect back to app
                    logger.debug('Validated ' + username)
                    self._set_session_var(self.CAS_ORIGIN, service_url)
                    self._set_session_var(self.CAS_TOKEN, ticket)
                    self._save_session()
                    response['status'] = '302 Moved Temporarily'
                    response['headers']['Location'] = service_url
                    return response
                else:
                    # Validation failed (for whatever reason)
                    response = self._casfailed(service_url)
                    return response
            else:
                #Check for single sign out
                if (self._is_single_sign_out(request_method, path, form)):
                  logger.debug('Single sign out request received')
                  response['logout'] = True
                  response['status'] = '200 OK'
                  return response
                if self._ignore_redirect is not None:
                  if self._ignore_redirect.match(request_url):
                    if self._ignored_callback is not None:
                      response['ignore_callback'] = True
                      return response
                is_gateway = ''
                if self._gateway_redirect is not None:
                  logger.debug('Gateway matching:' + request_url)
                  if self._gateway_redirect.match(request_url):
                    #See if we've been here before
                    gw = self._get_session_var(self.CAS_GATEWAY)
                    if gw != None:
                      logger.debug('Not logged in carrying on to:' + request_url)
                      self._remove_session_var(self.CAS_GATEWAY)
                      self._save_session()
                      #A bit paranoid but check it's the same URL
                      if gw == request_url:
                        return None
                    
                    logger.debug('Checking if logged in to CAS:' + request_url)
                    is_gateway = '&gateway=true'
                    self._set_session_var(self.CAS_GATEWAY, request_url)
                    self._save_session()
                logger.debug('Does not have ticket redirecting')
                service_url = request_url
                response['status'] = '302 Moved Temporarily'
                response['headers']['Location'] = '%s?service=%s%s' % (self._login_url, quote(service_url),is_gateway)
                return response

    @abstractmethod
    def _get_session(self, request):
        logger.critical('Must define a method to get the current session')

    @abstractmethod
    def _has_session_var(self, name):
        return name in self._session 

    @abstractmethod
    def _remove_session_var(self, name):
        if name in self._session:
            del self._session[name] 

    @abstractmethod
    def _set_session_var(self, name, value):
        self._session[name] = value
        logger.debug("Setting session:" + name + " to " + value)

    def _set_encrypted_session_var(self, name, value):
        if not hasattr(self,'_session_private_key'):
            (self._session_public_key, self._session_private_key) = rsa.newkeys(512)
        self._session[name] = rsa.encrypt(value.encode('utf8'),self._session_public_key)
    
    def _get_encrypted_session_var(self, name):
        if not hasattr(self,'_session_private_key'):
            return None
        if name in self._session:
          return (rsa.decrypt(self._session[name], self._session_private_key).decode('utf8'))
        else:
          return None
    
    @abstractmethod
    def _get_session_var(self, name):
        if name in self._session:
          return (self._session[name])
        else:
          return None

    @abstractmethod
    def _save_session(self):
        logger.critical('Must define a method to save the current session')

    @abstractmethod
    def _delete_session(self):
        #Unless overriding _do_session_logout
        logger.critical('Must define a method to delete the current session')
    
    def _do_session_logout(self):
        self._remove_session_var(self.CAS_USERNAME)
        self._remove_session_var(self.CAS_GROUPS)
        self._remove_session_var(self.CAS_PASSWORD)
        self._save_session()
        self._delete_session()

    def _get_logout_redirect_url(self):
        response = { 'headers': {} }
        dest = self._logout_dest
        if (dest == None or dest == '') and self._has_session_var(self.CAS_ORIGIN):
            dest = self._get_session_var(self.CAS_ORIGIN)
        logger.debug("Log out dest:" + str(dest))
        if dest:
            parsed = urlparse(dest)
            if parsed.path == self._logout_url:
                dest = self._sso_logout_url
        else:
            dest = ''
        logger.debug("Log out redirecting to:" + str(dest))
        response['status'] = '302 Moved Temporarily'
        response['headers']['Location'] = '%s?service=%s' % (self._sso_logout_url, quote(dest))
        return response

    #Communicate values to the rest of the application
    @abstractmethod
    def _set_values(self, environ):
        logger.critical('Must define a method to communicate the CAS values to the application')
        username = self._get_session_var(self.CAS_USERNAME)
        logger.debug('Session authenticated for ' + username)
        #environ['AUTH_TYPE'] = 'CAS'
        #environ['REMOTE_USER'] = str(username)
        #environ['PASSWORD'] = str(self._get_encrypted_session_var(self.CAS_PASSWORD))
        #environ[self._group_environ] = str(self._get_session_var(self.CAS_GROUPS))

    def _casfailed(self, service_url):

        response = { 'headers': {} }
        if self._casfailed_url is not None:
            response['status'] = '302 Moved Temporarily'
            response['headers']['Location'] = self._casfailed_url
        else:
            # Default failure notice
            response['status'] = '401 Unauthorized'
            response['headers']['Location'] = self._casfailed_url
            response['headers']['Content-Type'] = 'text/plain'
            response['headers']['WWW-Authenticate'] = 'CAS casUrl="' + self._root_url + '" service="' + service_url + '"'
            response['data'] = 'CAS authentication failed\n'
        return response

