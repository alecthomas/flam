from __future__ import with_statement

import hashlib
import logging
import mimetypes
import os
import posixpath

from genshi.builder import tag
from genshi.template import TemplateLoader
from genshi.filters import Transformer
from werkzeug import Local, LocalManager, SharedDataMiddleware, Request, \
                     Response, ClosingIterator, DebuggedApplication, \
                     serving, redirect
from werkzeug.exceptions import HTTPException, BadRequest, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.utils import cached_property
from werkzeug.contrib.sessions import Session, FilesystemSessionStore, generate_key
import genshi
import simplejson

from flam.util import Signal


__all__ = [
    'expose', 'run_server', 'static_resource', 'json', 'Request', 'Response',
    'application', 'local', 'html', 'request', 'href', 'redirect', 'static',
    'flash', 'INFO', 'WARNING', 'ERROR','context_setup', 'request_setup',
    'request_teardown',
    ]


local = Local()
local_manager = LocalManager([local])
application = local('application')
flash_message = local('flash_message')
request = local('request')
session = local('session')
user = local('session')
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


class Request(Request):
    """Request object with some useful extra methods."""

    @property
    def username(self):
        return self.session.get('username')

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

    def __init__(self, cookie_name=None, debug=False, static_root=None, static_map=None):
        local.application = self
        self.cookie_name = cookie_name
        self.debug = debug
        self.static_root = static_root
        self.static_map = static_map

    def __call__(self, environ, start_response):
        request = Request(environ)
        local.application = self
        local.request = request
        local.url_adapter = adapter = url_map.bind_to_environ(environ)
        local.flash_message = {}
        local.session = self._create_session()
        local.user = None

        request_setup_signal()

        try:
            # CSRF protection concept borrowed from Trac.
            session_form_token = request.form_token
            form_token = request.form.get('__FORM_TOKEN')
            if request.method == 'POST' and form_token != session_form_token:
                logging.warning('Invalid form token %s != %s from %r',
                                form_token, session_form_token, request)
                raise BadRequest('Invalid form token, do you have cookies enabled?')

            endpoint, values = adapter.match()
            handler = view_map[endpoint]
            if 'flash' in request.session:
                flash_message.update(request.session['flash'])
                del request.session['flash']
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
                request.session['flash'] = dict(flash_message)

            if request.session.should_save:
                session_store.save(request.session)
                response.set_cookie(
                    self.cookie_name, request.session.sid,
                    httponly=True,
                    )
        except HTTPException, e:
            response = e
        return ClosingIterator(response(environ, start_response),
                               [request_teardown_signal()])

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
            if self.static_map:
                name = self.static_map.get(name, name)
            return static(name)
        return stream | Transformer('//*[matches(@src, "^%s")]' % prefix).attr('src', map_static) | \
            Transformer('//*[matches(@href, "^%s")]' % prefix).attr('href', map_static)


def flash(message, type=INFO):
    """Flash a message to the user on next request."""
    flash_message['message'] = message
    flash_message['type'] = type


@context_setup
def default_context_setup(context):
    """Populate the default template render context."""
    context['href'] = href
    context['static'] = static
    context['session'] = request.session
    context['flash'] = flash_message
    context['debug'] = application.debug
    context['Markup'] = genshi.Markup


def expose(rule=None, **kw):
    """Expose a function as a routing endpoint.

    If arguments are omitted, the wrapped function name will be used as the
    rule name and routing path.
    """
    def decorate(f):
        endpoint = f.__name__
        kw.setdefault('endpoint', endpoint)
        view_map[endpoint] = f
        new_rule = '/' + f.__name__ if rule is None else rule
        url_map.add(Rule(new_rule, **kw))
        return f
    if callable(rule):
        f = rule
        rule = None
        return decorate(f)
    return decorate


class Href(object):
    """A convenience object for referring to endpoints."""
    def __getattr__(self, endpoint):
        endpoint = [endpoint]
        def wrapper(_external=False, **values):
            if callable(endpoint[0]):
                endpoint[0] = endpoint[0].__name__
            return local.url_adapter.build(endpoint[0], values, force_external=_external)
        return wrapper

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


def json(data):
    """Convert a fundamental Python object to a JSON response."""
    return Response(simplejson.dumps(data), content_type='application/json')


def html(template, **data):
    """Render a HTML template."""
    tmpl = template_loader.load(template)
    context = {}
    context_setup_signal(context)
    context.update(data)
    stream = tmpl.generate(
        **context
        )
    return stream


def load_static_map(mapping_file):
    """Load a mapping of real filenames to pre-processed hashed filenames."""
    map = {}
    with open(mapping_file) as fd:
        for line in fd:
            v, k = line.strip().split(None, 1)
            map[k] = v
    return map


def run_server(host='localhost', port=0xdead, static_path=None, debug=False,
               log_level=logging.WARNING, template_paths=None,
               cookie_name=None, static_map=None):
    """Start a new standalone application server."""
    global template_loader, session_store
    session_store = FilesystemSessionStore()
    template_loader = TemplateLoader(template_paths or ['templates'],
                                     auto_reload=debug)

    if isinstance(static_map, basestring):
        static_map = load_static_map(static_map)
    application = Application(cookie_name=cookie_name, debug=debug,
                              static_root='/static', static_map=static_map)
    if debug:
        application = DebuggedApplication(application, evalex=True)
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level)
    logging.getLogger('werkzeug').setLevel(log_level)
    logging.getLogger().setLevel(log_level)
    if not static_path:
        static_path = os.path.join(os.getcwd(), 'static')
    application = SharedDataMiddleware(application, {'/static': static_path})
    serving.run_simple(host, port, application, use_reloader=debug)


class Callback(Signal):
    def __init__(self, help):
        super(Callback, self).__init__()
        self.__doc__ = help
        self.dispatch = self.__call__
        self.__call__ = self.connect


context_setup_signal = Signal()
context_setup = context_setup_signal.connect
context_setup.__doc__ = 'Register a function as a

request_setup_signal = Signal()
request_setup = request_setup_signal.connect

request_teardown_signal = Signal()
request_teardown = request_teardown_signal.connect


