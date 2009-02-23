from flam.web.auth import *
from flam.web import *


class User(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password


@user_loader
def fetch_user(username):
    print 'Loading user', username
    return User(username, 'foo')


@expose('/')
@require_authentication
def index():
    print 'index', user
    return HTML("""
        <body>Foo %s <a href="%s">logout</a></body>
        """ % (user.username, href.logout()))


@expose
def logout():
    session.pop('username', None)
    return redirect(href.index())

run_server(debug=1)
