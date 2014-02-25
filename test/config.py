import tempfile

#The URL of your CAS server - if this is set then CAS will be enabled
CAS_SERVICE = 'https://www.malariagen.net/sso'
#This is the CAS protocol version versions 2 and 3 supported
CAS_VERSION = 3
#A URL to use as the link to logout
CAS_LOGOUT_PAGE = '/logout'
#Where to go when you've logged out - will send you to the entry page if not set
CAS_LOGOUT_DESTINATION = ''
#A page to show if validation fails
CAS_FAILURE_PAGE = None

#If you set this to 127.0.0.1 then it will only be available on the localhost i.e. not externally
HOSTNAME='0.0.0.0'
PORT=5000

# Configure the SessionMiddleware (Beaker)
session_opts = {
    'session.type': 'file',
    'session.cookie_expires': True,
    'session.data_dir': tempfile.gettempdir() + '/cas_wsgi_middleware'
}

