A minimalist Python application framework
=========================================

Flam relies on Werkzeug and Genshi.

Web Services
------------

Convenience functions exist for many common web operations, inside the
``flam.web`` package.

Render a Genshi template::

  html(template, **data)

Render JSON::

  json(data)

Issue a HTTP redirect::

  redirect(url)

Set the "flash" session variable. This can be used by handlers to send user
messages, including after redirects::

  flash(message, type=type)


Decorators are used extensively to register hooks in Flam's web framework. The
most useful of these is probably @expose, but they all have their place.

Register login() as the request handler for /login::

    @expose
    def login():
        ...

Register user() as the request handler for /user/<username>::

    @expose('/user/<username>')
    def user(username):
        ...

Request handlers can return Werkzeug Response objects or Genshi streams.

Populate the Genshi template context per-render::

    @context_setup
    def my_context_setup(context):
        context['name'] = get_username()

Setup the system for a new request::

    @request_setup
    def my_request_setup():
        request.username = request.session.get('username', None)

Tear down any per-request state::

    @request_teardown
    def my_request_teardown():
        del request.username

URLs can be reconstructed with the href object. Each attribute on the object is
a callable representing a routing endpoint name, keywords arguments fill in the
routing path parameters::

    @expose('/user/<username>')
    def user(username):
        return html('user.html', username=username)

    >>> href.user(username='foo')
    '/user/foo'


An example::

    from flam.app import run
    from flam.web.core import expose, html, json, run_server
    from flam.web.auth import authenticator, authenticate


    # Our list of users!
    users = {'alec': 'password', 'bob': 's3cr3t'}

    # Define an authenticator
    @authenticator
    def authenticate_user(username, password):
        return users.get(username, -1) == password


    # Specify path for a handler
    @expose('/')
    @authenticate
    def index():
        return html('index.html')


    # If a path is not provided, the name of the function is used (/home)
    @expose
    @authenticate
    def home():
        return html('home.html')


    # Define an API function to return a list of users.
    @expose('/api/users')
    @authenticate
    def api_users():
        return json(list(users))


    def main(args):
        run_server()


    if __name__ == '__main__':
        run(main)
