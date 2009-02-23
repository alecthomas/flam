"""Provides authentication services for Flam.

There are four aspects to authentication in Flam:

  1. Force authentication for a particular URL.

      @expose('/')
      @require_authentication
      def index():
        ...

  2. Rendering a custom login page.

      @authentication_handler
      def login():
        ...

  3. Fetching an application-specific user object.

      @user_loader
      def fetch_user(username):
        ...

  4. Verifying a user's password.

      @authenticator
      def authenticate(user, password):
        ...

The only hook that *must* be implemented by an application requiring
authentication is @user_loader. If the returned objects has a password
attribute then authentication will "just work". A default
@authentication_handler will be used that assumes the existence of a
"login.html" with a single "login" form containing a "username" and "password".

eg.
  <form id="login" method="post">
    Username: <input type="text" name="username" /> <br />
    Password: <input type="password" name="password" />
  </form>

"""

from genshi.filters import HTMLFormFiller

from flam import validate
from flam.util import DecoratorSignal
from flam.web import *
from flam.web.core import view_map


__all__ = [
    'authenticator', 'user_loader', 'authentication_handler',
    'require_authentication', 'user', 'get_session_user', 'set_session_user',
    'clear_session_user',
    ]


user = local('user')

user_loader = DecoratorSignal(limit=1)
authenticator = DecoratorSignal(limit=1)
_user_authentication_endpoint = None


@request_setup
def setup_user():
    username = session.get('username', None)
    if username is not None:
        local.user = user_loader.dispatch(username)


@authenticator
def default_authenticator(user, password):
    """Default user authenticator.

    Assumes the application-specific "user" object has a .password attribute.
    """
    return user.password == password


def require_authentication(function):
    """Decorator to force authentication for a request handler."""
    def decorator(*args, **kwargs):
        if not user:
            return redirect(href[_user_authentication_endpoint]())
        return function(*args, **kwargs)
    decorator.__name__ = function.__name__
    return decorator


def authentication_handler(*args, **kwargs):
    """Identical to expose() but also registers the URL as the default
    authentication handler."""
    global _user_authentication_endpoint
    callback = expose(*args, **kwargs)
    for endpoint, endpoint_callback in view_map.iteritems():
        if callback == endpoint_callback:
            _user_authentication_endpoint = endpoint
            break
    return callback


@authentication_handler
def login():
    """Default authentication handler under /login.

    Requires a template named login.html containing a form similar to the
    following:

      <form id="login" method="post">
        Username: <input type="text" name="username" /> <br />
        Password: <input type="password" name="password" />
      </form>
    """
    login_form = validate.Form('login')
    login_form.add('username', validate.Not(validate.Empty()),
                   'A username must be provided.')
    login_form.add('password', validate.Not(validate.Empty()),
                   'A password must be provided.')

    form = request.form
    if not form:
        return html('login.html')

    context = login_form.validate(form)
    if context.errors:
        clear_session_user()
        return html('login.html') | HTMLFormFiller(data=form) | context.inject_errors()

    # Authenticate the user.
    user = user_loader.dispatch(form['username'])
    if not authenticator.dispatch(user, form['password']):
        clear_session_user()
        flash('Invalid credentials.', type=ERROR)
        return html('login.html') | HTMLFormFiller(data=form)
    session['username'] = form['username']
    # TODO(alec) How do we pass the redirect target, default or explicit?
    return redirect(href.index())


def get_session_user():
    """Get the username for the session."""
    return session.get('username', None)


def set_session_user(username):
    """Set the session user."""
    session['username'] = username
    local.user = user_loader.dispatch(session['username'])


def clear_session_user():
    """Clear the session user."""
    session.pop('username', None)
    local.user = None
