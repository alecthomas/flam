import re
from textwrap import wrap
from sqlalchemy import orm
import simplejson
from genshi.template import *
from elixir import *
from features import *
from aspects import *
from werkzeug import *
from werkzeug.routing import *
from werkzeug.utils import *


class Owner(Entity):
    name = Field(Unicode(255), primary_key=True)
    pets = OneToMany('Pet')

class Pet(Entity):
    name = Field(Unicode(255), primary_key=True)
    owner = ManyToOne('Owner')


class TemplateResponse(BaseResponse):
    loader = None
    template_paths = Require('template_paths')

    def __init__(self, template, data):
        if not self.loader:
            print 'loading templates from', self.template_paths
            TemplateResponse.loader = TemplateLoader(self.template_paths)
        tmpl = self.loader.load(template)
        content = tmpl.generate(**data).render()
        super(TemplateResponse, self).__init__(
            content, mimetype='text/html',
            )


metadata.bind = "sqlite:///:memory:"
setup_all()
create_all()

christine = Owner(name=u'Christine')
Pet(name=u'Buffy', owner=christine)
Pet(name=u'Kahlua', owner=christine)
session.flush()


class ModelController(object):
    def __init__(self, model, key):
        self.model = model
        self.key = key

    def list(self, req):
        return self.model.query()

    def create(self, req, data):
        pet = self.model(**data)
        return True

    def read(self, req, **args):
        key = args.pop(self.key)
        return self.model.get_by(**{self.key: key})

    def update(self, req, data=None, **args):
        key = args.pop(self.key)
        data = args.pop('data')
        pet = self.read(**{self.key: key})
        pet.from_dict(data)
        return True

    def delete(self, req, **args):
        key = args.pop(self.key)
        pet = self.read(**{self.key: key})
        pet.delete()
        return True


class JSON(Aspect):
    """Translate between JSON requests and responses."""

    def __callnext__(self, _method, req, **args):
        if req.method in ('POST', 'PUT'):
            args['data'] = simplejson.loads(req.content)
        result = _method(req, **args)
        if isinstance(result, orm.Query):
            result = [r.to_dict() for r in result]
        elif hasattr(result, 'to_dict'):
            result = result.to_dict()
        return BaseResponse(
            simplejson.dumps(result),
            content_type='application/json',
            )


class HTML(Aspect):
    """HTML presentation of a resource."""
    def __init__(self, next, name):
        super(HTML, self).__init__(next, name=name)

    def data(self, req, **extra):
        return dict({'req': req, 'href': req.href}, **extra)

    def list(self, req, **args):
        results = self.next.list(req, **args)
        return TemplateResponse(
            self.name + '_list.html',
            self.data(req, collection=results),
            )

    def read(self, req, **args):
        resource = self.next.read(req, **args)
        return TemplateResponse(
            self.name + '_read.html',
            self.data(req, resource=resource),
            )


class Query(Aspect):
    """Parse filter expressions in the 'q' query parameter."""
    def list(self, req, q=None, **args):
        result = self.next.list(req, **args)
        if q is not None:
            result = Query(result, q)
        return result


class DefaultToBasicFormat(Aspect):
    """Return a list of resource keys, unless "format" is defined."""

    def __init__(self, next, key):
        super(DefaultToBasicFormat, self).__init__(next, key=key)

    def list(self, req, **args):
        results = self.next.list(req, **args)
        if req.args.get('format') != 'detailed':
            results = [getattr(row, self.key) for row in results]
        return results


class REST(Aspect):
    """Expose resources via a RESTful interfaces.

    This aspect *MUST* be outermost in order for dispatching to work correctly.
    """

    def __init__(self, next, endpoint, path, legacy=True, suffix=''):
        """Construct a new REST aspect.

        :param next: Next object in aspect chain.
        :param endpoint: Generated endpoint prefix.
        :param path: Werkzeug Rule path to a resource. The "dirname" of this
                     is used as the collection path.
        :param legacy: Whether to generate legacy HTML form handler rules.
        :parma suffix: Suffix for each rule. Useful for appending "type"
                       identifiers like .json, .rss, etc.
        """
        base = posixpath.dirname(path)
        super(REST, self).__init__(
            next,
            endpoint=endpoint, base=base, resource=path,
            legacy=legacy, suffix=suffix,
            )

    def dispatch(self, req, endpoint, args):
        endpoint, method = endpoint.rsplit('_', 1)
        assert endpoint == self.endpoint, \
            'Expected endpoint %r, got %r' % (self.endpoint, endpoint)
        return getattr(self, method)(req, **args)

    def get_rules(self, map):
        """Werkzeug routing rule factory."""
        yield Rule(self.base + self.suffix, endpoint=self.endpoint + '_list', methods=['GET'])
        yield Rule(self.base + self.suffix, endpoint=self.endpoint + '_create', methods=['POST'])
        yield Rule(self.resource + self.suffix, endpoint=self.endpoint + '_read', methods=['GET'])
        yield Rule(self.resource + self.suffix, endpoint=self.endpoint + '_update', methods=['PUT'])
        yield Rule(self.resource + self.suffix, endpoint=self.endpoint + '_delete', methods=['DELETE'])
        if self.legacy:
            yield Rule(self.base + self.suffix + '/new', endpoint=self.endpoint + '_new')
            yield Rule(self.resource + self.suffix + '/edit', endpoint=self.endpoint + '_edit')


class Href(object):
  """A convenience class for mapping endpoints to URLs.

  >>> map = routing.Map([
  ...   routing.Rule('/foo', endpoint='foo'),
  ...   routing.Rule('/bar/<baz>', endpoint='bar'),
  ...   routing.Rule('/baz/<waz>', endpoint='baz', methods=['POST']),
  ...   routing.Rule('/waz', endpoint='.waz'),
  ...   ])
  >>> endpoint = Href(map.bind('localhost'))

  Bare endpoint:

  >>> endpoint.foo()
  '/foo'

  Href with arguments:

  >>> endpoint.bar(baz=10)
  '/bar/10'

  Href with a particular method:

  >>> endpoint.baz(waz=20, method='POST')
  '/baz/20'

  Can also be called directly, for non-identifier endpoints:

  >>> endpoint('.waz')
  '/waz'
  """

  def __init__(self, adapter):
    """Construct a new Href.

    Args:
      adapter: werkzeug.routing.MapAdapter.
      absolute: Should the generated URL be fully qualified?
    """
    self.adapter = adapter

  def __getattr__(self, endpoint):
    """Return a proxy object for an endpoint.

    Args:
      endpoint: Endpoint name.

    Returns:
      Callable with the signature (method=None, **values), passed to the
      endpoint construction method.
    """
    def bound_href(method='GET', absolute=False, **values):
      return self.adapter.build(endpoint, values, method=method,
                                force_external=absolute)
    return bound_href

  def __call__(self, endpoint, *args, **kwargs):
    """Return the URL for non-identifier endpoint.

    Args:
      endpoint: Endpoint name.
      args: Args to pass to proxy object returned by __getattr__.
      kwargs: As with "args", but for keyword arguments.

    Returns:
      URL.
    """
    return getattr(self, endpoint)(*args, **kwargs)


class Dispatcher(Map):
    def __init__(self, controllers):
        super(Dispatcher, self).__init__(controllers)
        self.dispatch_map = {}
        for controller in controllers:
            for rule in controller.get_rules(self):
                self.dispatch_map[rule.endpoint] = controller

    def dispatch(self, req):
        mapper = self.bind_to_environ(req.environ)
        endpoint, args = mapper.match()
        return self.dispatch_map[endpoint].dispatch(req, endpoint, args)


class Request(BaseRequest):
    def __init__(self, environ, dispatcher, *args, **kwargs):
        super(Request, self).__init__(environ, *args, **kwargs)
        self.dispatcher = dispatcher
        self.adapter = dispatcher.bind_to_environ(environ)
        self.href = Href(self.adapter)


if __name__ == '__main__':
    append('template_paths', '.')
    pet_controller = ModelController(Pet, 'name')

    pet_api = JSON(DefaultToBasicFormat(Query(pet_controller), 'name'))
    pet_api = REST(pet_api, 'pet_api', '/pets/<name>',
                   legacy=False, suffix='.json')

    pet_html = HTML(Query(pet_controller), 'pet')
    pet_html = REST(pet_html, 'pet', '/pets/<name>', suffix='.html')

    dispatcher = Dispatcher([pet_api, pet_html])

    for url in ('/pets.json', '/pets/Buffy.json', '/pets.json?format=detailed', '/pets.html', '/pets/Kahlua.html'):
        environ = create_environ(url, content_type='application/json')
        req = Request(environ, dispatcher)
        response = dispatcher.dispatch(req)
        print url
        print ' ', '\n  '.join([': '.join(h) for h in response.headers])
        print
        print ' ', '\n  '.join(response.data.splitlines())
        print
