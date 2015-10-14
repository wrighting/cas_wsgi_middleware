try:
  from setuptools import setup
except ImportError:
  from distutils.core import setup

setup(
    # Application name:
    name="CASWSGIMiddleware",

    # Version number (initial):
    version="1.1.0",

    # Application author details:
    author="Ian Wright",
    author_email="tech@wrighting.org",
    keywords="cas wsgi python",
    # Packages
    packages=["cas"],

    # Details
    #url="http://pypi.python.org/pypi/MyApplication_v010/",
    url="https://github.com/wrighting/cas_wsgi_middleware",
    #
    # license="LICENSE.txt",
    description="A WSGI middleware module to enable CAS authentication",

    long_description=open("README.md").read(),

    # Dependent packages (distributions)
    install_requires=[
        "rsa >= 3.2",
	"requests >= 2.2.1"
    ],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 2'
    ]
)
