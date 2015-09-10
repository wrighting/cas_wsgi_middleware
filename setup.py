try:
  from setuptools import setup
except ImportError:
  from distutils.core import setup

setup(
    # Application name:
    name="CASWSGIMiddleware",

    # Version number (initial):
    version="0.1.0",

    # Application author details:
    author="Ian Wright",
    author_email="tech@wrighting.org",
    keywords="cas wsgi",
    # Packages
    packages=["cas"],

    # Details
    #url="http://pypi.python.org/pypi/MyApplication_v010/",
    url="https://github.com/wrighting/cas_wsgi_middleware",
    #
    # license="LICENSE.txt",
    description="Useful towel-related stuff.",

    long_description=open("README.md").read(),

    # Dependent packages (distributions)
    install_requires=[
        "Werkzeug >= 0.9.4",
	"requests >= 2.2.1"
    ],
)
