# encoding: utf-8
#
# Copyright (C) 2008-2009 Alec Thomas <alec@swapoff.org
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

"""Provides authentication services for Flam.

There are four aspects to authentication in Flam:

  1. Force authentication for a particular URL (important: @authenticate must
     come after @expose)

      @expose('/')
      @authenticate
      def index():
        ...

  2. Rendering a custom login page.

      @authentication_handler
      def login():
        ...

  3. Verifying a user's password.

      @authenticator.register
      def authenticate(username, password):
        ...

The only hook that *must* be implemented by an application requiring
authentication is @authenticator.register.  A default @authentication_handler
will be used that assumes the existence of a "login.html" template, with a
single "login" form containing a "username" and "password".

eg.
  <form id="login" method="post">
    Username: <input type="text" name="username" /> <br />
    Password: <input type="password" name="password" />
  </form>

"""

from genshi.filters import HTMLFormFiller

from flam import validate
from flam.signal import Trigger
from flam.web.core import *
from flam.web.core import view_map


__all__ = [
    'authenticator', 'authentication_handler', 'authenticate',
    'get_session_user', 'set_session_user', 'clear_session_user',
    ]


authenticator = Trigger()
_user_authentication_endpoint = None


@on_context_setup.connect
def setup_template_context(context):
    context['username'] = get_session_user()


def authenticate(function):
    """Decorator to force authentication for a request handler."""
    def decorator(*args, **kwargs):
        if not get_session_user():
            return redirect(href[_user_authentication_endpoint](r=request.path))
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
    username = form['username']
    if not authenticator(username, form['password']):
        clear_session_user()
        flash('Invalid credentials.', type=ERROR)
        return html('login.html') | HTMLFormFiller(data=form)
    set_session_user(username)
    return redirect(request.args.get('r', '/'))


@expose
def logout():
    clear_session_user()
    return redirect(request.args.get('r', '/'))


def get_session_user():
    """Get the username for the session."""
    return session.get('username', None)


def set_session_user(username):
    """Set the session user."""
    session['username'] = username


def clear_session_user():
    """Clear the session user."""
    session.pop('username', None)
