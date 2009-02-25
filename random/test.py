from flam import *

class User(object):
    stats = Variables('user', user_loads=0)

    def __init__(self, username, password):
        self.stats.user_loads += 1
        self.username = username
        self.password = password


@variable
def time():
    import time
    return time.time()

@user_loader
def fetch_user(username):
    return User(username, 'foo')


@expose('/')
@require_authentication
def index():
    return HTML("""
        <body>Foo %s <a href="%s">logout</a></body>
        """ % (user.username, href.logout()))


@expose
def logout():
    session.pop('username', None)
    return redirect(href.index())

run_server(debug=1)
