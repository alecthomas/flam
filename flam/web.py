import logging
import mimetypes
import posixpath

from genshi.template import TemplateLoader
from werkzeug import Local, LocalManager, SharedDataMiddleware, Request, \
                     Response, ClosingIterator, DebuggedApplication, \
                     serving, redirect
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.utils import cached_property
from werkzeug.contrib.sessions import Session, FilesystemSessionStore
import genshi
import simplejson


__all__ = [
    'expose', 'url_for', 'run_server', 'static_resource', 'json', 'Request',
    'Response', 'application', 'local', 'html', 'request', 'register', 'href',
    'redirect', 'static',
    ]


local = Local()
local_manager = LocalManager([local])
application = local('application')
request = local('request')
static_map = {'/static': 'static'}
# URL routing rules
url_map = Map([Rule('/static/<file>', endpoint='static', build_only=True)])
# URL routing endpoint to callback mapping.
view_map = {}
# Global template loader object
template_loader = None
# Session store
session_store = None
# HTML widgets
default_context = {}


class Request(Request):
    """Request object with some useful extra methods."""

    @cached_property
    def session(self):
        sid = self.cookies.get(application.cookie_name)
        if sid is None:
            return session_store.new()
        else:
            return session_store.get(sid)

    @cached_property
    def json(self):
        return simplejson.loads(self.data)


class Application(object):
    """Core WSGI application."""

    def __init__(self, cookie_name=None, setup=None, teardown=None):
        local.application = self
        self.cookie_name = cookie_name
        if setup:
            self.setup = setup
        if teardown:
            self.teardown = teardown

    def setup(self):
        """Configure the per-request application state."""

    def teardown(self):
        """Tear down any per-request state."""

    def __call__(self, environ, start_response):
        request = Request(environ)
        local.application = self
        local.request = request
        local.url_adapter = adapter = url_map.bind_to_environ(environ)
        self.setup()
        try:
            endpoint, values = adapter.match()
            handler = view_map[endpoint]
            response = handler(**values)
            if isinstance(response, genshi.Stream):
                response = Response(response.render('html', doctype='html'),
                                    content_type='text/html')
            if request.session.should_save:
                session_store.save(request.session)
                response.set_cookie(
                    self.cookie_name, request.session.sid,
                    httponly=True,
                    )
        except HTTPException, e:
            response = e
        return ClosingIterator(response(environ, start_response),
                               [self.teardown])


def expose(rule, **kw):
    """Expose a function as a routing endpoint."""
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


def register(what, name=None):
    """Register an object in the default template context.

    (Can be used as a decorator.)
    """
    if name is None:
        name = what.__name__
    default_context[name] = what
    return what


class Href(object):
    """A convenience object for referring to endpoints."""
    def __getattr__(self, endpoint):
        def wrapper(_external=False, **values):
            return url_for(endpoint, _external=_external, **values)
        return wrapper


href = register(Href(), name='href')

@register
def static(filename):
    """Convenience function for referring to static content."""
    return href.static(file=filename) + '?1'


def url_for(endpoint, _external=False, **values):
    """Return the URL for an endpoint."""
    if callable(endpoint):
        endpoint = endpoint.__name__
    return local.url_adapter.build(endpoint, values, force_external=_external)


def static_resource(filename):
    """Serve a file."""
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
    context = dict(default_context)
    context.update(data)
    stream = tmpl.generate(session=request.session, **context)
    return stream


def run_server(host='localhost', port=0xdead, static_map=None, debug=False,
               log_level=logging.WARNING, template_paths=None,
               cookie_name=None, setup=None, teardown=None):
    """Start a new standalone application server."""
    global template_loader, session_store
    session_store = FilesystemSessionStore()
    template_loader = TemplateLoader(template_paths or ['templates'],
                                     auto_reload=debug)

    application = Application(cookie_name=cookie_name, setup=setup, teardown=teardown)
    if debug:
        application = DebuggedApplication(application, evalex=True)
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level)
    logging.getLogger('werkzeug').setLevel(log_level)
    logging.getLogger().setLevel(log_level)
    if not static_map:
        static_map = {'/static': 'static'}
    application = SharedDataMiddleware(application, static_map)
    serving.run_simple(host, port, application, use_reloader=debug)
