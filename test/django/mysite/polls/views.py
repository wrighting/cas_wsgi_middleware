from django.http import HttpResponse
import pprint

def index(request):
    return HttpResponse('<div><span id="hello">Hello, world. You are at the polls index.</span>' +\
                        '<span id="user">' + request.user.username + '</div>')
