# encoding: utf-8
#
# Copyright (C) 2008-2009 Alec Thomas <alec@swapoff.org
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

"""Flam web framework core."""

from __future__ import with_statement

import inspect
import logging
import mimetypes
import os
import sys

from genshi import HTML
from genshi.builder import tag
from genshi.template import TemplateLoader
from genshi.filters import Transformer, HTMLFormFiller
from werkzeug import Local, LocalManager, SharedDataMiddleware, Request, \
                     Response, ClosingIterator, DebuggedApplication, \
                     serving, redirect
from werkzeug.exceptions import HTTPException, BadRequest, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.utils import cached_property
from werkzeug.contrib.sessions import FilesystemSessionStore, generate_key
import genshi
import simplejson

from flam.flags import define_flag, flags
from flam.logging import log, console, on_log_level_change
from flam.signal import Signal


__all__ = [
    'expose', 'wsgi_application', 'run_server', 'static_resource', 'json',
    'Request', 'Response', 'application', 'local', 'html', 'request', 'href',
    'redirect', 'static', 'flash', 'INFO', 'WARNING', 'ERROR',
    'on_context_setup', 'on_request_setup', 'on_request_teardown', 'HTML',
    'tag', 'session', 'process_form',
    ]


define_flag('--port', type='int', default=0xdead,
            help='specify port to bind HTTP server to [%default]')
define_flag('--host', default='localhost',
            help='address to bind HTTP server to [%default]')
define_flag('--debug', action='store_true', default=False,
            help='enable debug mode')


local = Local()
local_manager = LocalManager([local])
application = local('application')
flash_message = local('flash_message')
request = local('request')
session = local('session')
url_adapter = local('url_adapter')
# URL routing rules
url_map = Map([Rule('/static/<file>', endpoint='static', build_only=True)])
# URL routing endpoint to callback mapping.
view_map = {}
# Global template loader object
template_loader = None
# Session store
session_store = None


# flash() levels
INFO = 'info'
WARNING = 'warning'
ERROR = 'error'


on_context_setup = Signal()
on_request_setup = Signal()
on_request_teardown = Signal()


class Request(Request):
    """Request object with some useful extra methods."""

    @cached_property
    def form_token(self):
        if 'form_token' in self.cookies:
            return self.cookies['form_token']
        else:
            return generate_key()

    @cached_property
    def json(self):
        return simplejson.loads(self.data)


class Application(object):
    """Core WSGI application."""

    def __init__(self, cookie_name=None, debug=False, static_root=None):
        local.application = self
        self.cookie_name = cookie_name or os.path.basename(sys.argv[0])
        self.debug = debug
        self.static_root = static_root

    def __call__(self, environ, start_response):
        request = Request(environ)
        local.application = self
        local.request = request
        local.url_adapter = adapter = url_map.bind_to_environ(environ)
        local.flash_message = {}
        local.session = self._create_session()

        on_request_setup(request)

        try:
            # CSRF protection concept borrowed from Trac.
            session_form_token = request.form_token
            form_token = request.form.get('__FORM_TOKEN')
            if request.method == 'POST' and form_token != session_form_token:
                log.warning('Invalid form token %s != %s from %r',
                            form_token, session_form_token, request)
                raise BadRequest('Invalid form token, do you have cookies enabled?')

            endpoint, values = adapter.match()
            handler = view_map[endpoint]
            if 'flash_message' in session:
                flash_message.update(session['flash_message'])
                del session['flash_message']
            response = handler(**values)
            if isinstance(response, genshi.Stream):
                token = tag.input(type='hidden', name='__FORM_TOKEN',
                                  value=session_form_token)
                response = response | Transformer('//form').prepend(token)
                if self.static_root:
                    response = self._remap_static(response)
                response = Response(response.render('xhtml'), content_type='text/html')
                response.set_cookie('form_token', session_form_token, httponly=True)
            elif flash_message:
                session['flash_message'] = dict(flash_message)

            if session.should_save:
                # TODO This is dying with:
                #   AttributeError: 'list' object has no attribute 'set_cookie'
                # when a non-Response object is returned (eg. a list).
                session_store.save(session)
                response.set_cookie(
                    self.cookie_name, session.sid,
                    httponly=True,
                    )
        except HTTPException, e:
            response = e
        return ClosingIterator(response(environ, start_response),
                               [on_request_teardown])

    def _create_session(self):
        sid = request.cookies.get(self.cookie_name)
        if sid is None:
            return session_store.new()
        else:
            return session_store.get(sid)

    def _remap_static(self, stream, prefix='/static/'):
        """Remap links to static content to the correct URL root."""
        def map_static(name, event):
            attrs = event[1][1]
            name = attrs.get(name)[len(prefix):]
            return static(name)
        return stream | Transformer('//*[matches(@src, "^%s")]' % prefix).attr('src', map_static) | \
            Transformer('//*[matches(@href, "^%s")]' % prefix).attr('href', map_static)


def flash(text, type=INFO):
    """Flash a message to the user on next request."""
    flash_message['text'] = text
    flash_message['type'] = type


@on_context_setup.connect
def default_context_setup(context):
    """Populate the default template render context."""
    context['href'] = href
    context['static'] = static
    context['session'] = session
    context['flash_message'] = flash_message
    context['debug'] = application.debug
    context['Markup'] = genshi.Markup


def expose(path=None, **kw):
    """Expose a function as a routing endpoint.

    If arguments are omitted, the wrapped function name will be used as the
    rule name and routing path. Underscores in the function name will be
    converted to URL path separators and positional arguments will be treated
    as parameterised path components.

    >>> @expose
    ... def user_view(username):
    ...   print username
    >>> Href().user_view(username='bob')
    '/user/view/bob'
    """
    def decorate(function):
        endpoint = function.__name__
        kw.setdefault('endpoint', endpoint)
        view_map[endpoint] = function
        # Introspect rule path from function name and arguments.
        if path is None:
            inferred_path = '/' + function.__name__.replace('_', '/')
            args, _, _, defaults = inspect.getargspec(function)
            if args:
                if defaults:
                    args = args[:-len(defaults)]
                inferred_path += '/<' + '>/<'.join(args) + '>'
        else:
            inferred_path = path
        rule = Rule(inferred_path, **kw)
        url_map.add(rule)
        function._routing_rule = rule
        return function

    if callable(path):
        # decorate() assumes "path" is a string or None, we set it to the
        # latter to force auto-pathing.
        function = path
        path = None
        decorator = decorate(function)
        decorator.__name__ = function.__name__
        return decorator

    return decorate


class Href(object):
    """A convenience object for referring to endpoints.

    >>> href = Href()
    >>> @expose('/test/<token>')
    ... def test(token):
    ...   pass
    >>> href.test(token='foo', q=10)
    '/test/foo?q=10'
    """
    def __getattr__(self, endpoint):
        endpoint = [endpoint]
        def wrapper(_external=False, **values):
            if callable(endpoint[0]):
                endpoint[0] = endpoint[0].__name__
            if 'url_adapter' in local:
                adapter = local.url_adapter
            else:
                # TODO(alec) The hostname should be specified in the
                # Application object somewhere, rather than being hard-coded.
                adapter = url_map.bind('localhost')
            return adapter.build(endpoint[0], values, force_external=_external)
        return wrapper

    __getitem__ = __getattr__


href = Href()


def static(filename):
    """Convenience function for referring to static content."""
    return href.static(file=filename)


def static_resource(filename):
    """Serve a static resource."""
    mime_type, encoding = mimetypes.guess_type(filename)
    try:
        fd = open(filename)
    except EnvironmentError:
        raise NotFound()
    try:
        return Response(fd.read(), content_type=mime_type)
    finally:
        fd.close()


def json(data, indent=False):
    """Convert a fundamental Python object to a JSON response."""
    return Response(simplejson.dumps(data, indent=indent),
                    content_type='application/json')


def html(template, **data):
    """Render a HTML template."""
    tmpl = template_loader.load(template)
    context = {}
    on_context_setup(context)
    context.update(data)
    stream = tmpl.generate(**context)
    return stream


def wsgi_application(static_path=None, debug=False, template_paths=None,
                     cookie_name=None):
    """Create a new WSGI application object.

    :param static_path: Path to static content, mapped to /static.
    :param debug: Whether to enable debug mode. This enables the Werkzeug
                  debugging middleware, alters the logging level, and possibly
                  other stuff.
    :param template_paths: Template paths, defaults to ['templates'].
    :param cookie_name: A unique cookie name for the application. If one is not
                        provided, a name derived from sys.argv[0] will be used.
    """
    global template_loader, session_store
    session_store = FilesystemSessionStore()
    template_loader = TemplateLoader(template_paths or ['templates'],
                                     auto_reload=debug)

    application = Application(cookie_name=cookie_name, debug=debug,
                              static_root='/static')
    if debug:
        application = DebuggedApplication(application, evalex=True)
    if not static_path:
        static_path = os.path.join(os.getcwd(), 'static')
    application = SharedDataMiddleware(application, {'/static': static_path})
    return application


@on_log_level_change.connect
def _set_werkzeug_log_level(level):
    """Set Werkzeug log level."""
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(level)
    if not werkzeug_logger.handlers:
        werkzeug_logger.addHandler(console)


def run_server(host=None, port=None, **args):
    """Start a new standalone application server.

    :param host: Host to bind to.
    :param port: Port to bind to.
    :param args: Passed through to :func:`wsgi_application`.
    """
    debug = args.get('debug', flags.debug)
    args['debug'] = debug
    application = wsgi_application(**args)
    serving.run_simple(host or flags.host, port or flags.port,
                       application, use_reloader=debug)


def process_form(template, validator, **context):
    """Perform "typical" processing of a template form.

    This means checking that a form has been POSTed and is valid.

    :param template: A Genshi stream, or template filename as a string.
    :param validator: flam.validate.Form object.
    :param context: Template context parameters.
    :returns: A tuple of (valid, response).
    """
    if isinstance(template, basestring):
        template = html(template, **context)
    form = request.form

    if not form:
        return False, template

    validation_context = validator.validate(form)
    if validation_context.errors:
        return False, template | HTMLFormFiller(data=form) | validation_context.inject_errors()

    return True, template


if __name__ == '__main__':
    import doctest
    doctest.testmod()
