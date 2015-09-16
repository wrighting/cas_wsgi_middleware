
##Running as a test
Ahead of running the test script you will need support for python virtualenv and pip

> sudo apt-get install python-pip
> sudo pip install virtualenv

##Running as part of a WSGI Application under Apache

> apt-get install libapache2-mod-wsgi

You will need to set up the virtualenv, see the test/run.sh script if you are unsure how to do this.

In your Apache configuration file:

```
    WSGIApplicationGroup %{GLOBAL}
    WSGIScriptReloading On

    WSGIDaemonProcess MyApp processes=2 threads=25 python-path=/path/to/virtualenv/lib/python2.7/site-packages

    Alias /MyApp/ "/path/to/MyApp/"
    <Directory "/path/to/MyApp">
        WSGIProcessGroup MyApp
        Options Indexes FollowSymLinks MultiViews ExecCGI
        MultiviewsMatch Handlers
        AddHandler wsgi-script .wsgi .py
        AddHandler cgi-script .cgi .pl
        AllowOverride All
    </Directory>
```

Copy the files from wsgi_app to /path/to/MyApp

Your URL will then be of the form /MyApp/app.wsgi/

This example allows for static HTML files to be placed in the directory /static - you can, of course, change this

##Options

###cas_root_url

This is url of your CAS server - typically https://yourdomain.com/cas

/login, /logout etc are appended to this url

###effective_url

If the application is behind a proxy server then, if the context is different frm the application server, then this parameter should be set as the proxy server context 

###logout_url

This url will be intercepted by the middleware to log you out of the application, and CAS

This will clear the local session and forward the request to the CAS logout page

###logout_dest

Where to go after you have logged out

###protocol_version

Only CAS version 2 and 3 are supported

###casfailed_url

A page to go to if authentication fails, if not set a simple message is displayed

###entry_page

It is necessary to define the entry page for single log out to work

CAS will post a message to this URL, which must be the same as the originally validated page, when a log out is performed on the CAS server.

###session_store

Werkzeug sessions are used and it's necessary to define a store to keep them in

###ignore_redirect

Sometimes when you are not authenticated you don't want to redirect to CAS, this regex defines these URLs

###ignored_callback

A function defining what to do when the ignore_redirect regex matches

###gateway_redirect

Default = None, A regular expression for pages that use a CAS gateway i.e. test if logged in but never show the log in page

###group_separator

Default = ';', How to separate the groups returned from CAS as part of attribute release

###group_environ

Default = 'HTTP_CAS_MEMBEROF', The name of the environment variable containing the groups

###cas_private_key (CAS 4.1)

Default = None, The name of a file containing the private key used for decrypting the credentials attribute when using clearpass. This will be available in the PASSWORD environment variable. The value is held in the session using encryption keys held only in memory.
