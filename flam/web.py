import mimetypes
import simplejson

from werkzeug import Local, LocalManager, SharedDataMiddleware, Request, \
                     Response, ClosingIterator, DebuggedApplication, \
                     serving
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.utils import cached_property


__all__ = ['expose', 'url_for', 'run_server', 'static_resource', 'json',
           'Request', 'Response', 'application', 'local']


local = Local()
local_manager = LocalManager([local])
application = local('application')
static_map = {'/static': 'static'}
# URL routing rules
url_map = Map([Rule('/static/<file>', endpoint='static', build_only=True)])
# URL routing endpoint to callback mapping.
view_map = {}


class Request(Request):
    """Request object with some useful extra methods."""

    @cached_property
    def json(self):
        return simplejson.loads(self.data)


class Application(object):
    """Core JSF WSGI application."""

    def __init__(self):
        local.application = self

    def __call__(self, environ, start_response):
        local.application = self
        request = Request(environ)
        local.url_adapter = adapter = url_map.bind_to_environ(environ)
        try:
            endpoint, values = adapter.match()
            handler = view_map[endpoint]
            response = handler(request, **values)
        except HTTPException, e:
            response = e
        #return ClosingIterator(response(environ, start_response),
        #                       [session.remove, local_manager.cleanup])
        return response(environ, start_response)


def expose(rule, **kw):
    """Expose a function as a routing endpoint."""
    def decorate(f):
        endpoint = f.__name__
        kw.setdefault('endpoint', endpoint)
        view_map[endpoint] = f
        url_map.add(Rule(rule, **kw))
        return f
    return decorate


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


def run_server(host='localhost', port=0xdead,
               static=None, debug=False):
    application = Application()
    if debug:
        application = DebuggedApplication(application, evalex=True)
    static = static_map.copy()
    static.update(static or {})
    application = SharedDataMiddleware(application, static)
    serving.run_simple(host, port, application, use_reloader=debug)
