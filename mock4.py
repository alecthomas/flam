from elixir import *
from aspects import *


class Pet(Entity):
    name = Field(Unicode(255))
    owner = ManyToOne('Owner')


class ModelController(Controller):
    def __init__(self, model, key):
        self.model = model

    def list(self):
        return self.model.query()

    def create(self, data):
        pet = self.model(**data)
        return True

    def read(self, **key):
        return self.model.get_by(*{self.key: key})

    def update(self, **key, data):
        pet = self.read(name)
        pet.from_dict(data)
        return True

    def delete(self, name):
        pet = self.read(name)
        pet.delete()
        return True


class StripRequest(Aspect):
    """Strip "req" argument from call chain."""
    def __callnext__(self, _method, req, **args):
        return _method(**args)


class JSON(Aspect):
    """Translate between JSON requests and responses."""

    def __callnext__(self, _method, req, **args):
        args.update(req.args)
        if req.method in ('POST', 'PUT'):
            args['data'] = simplejson.loads(req.content)
        result = _method(req, **args)
        if isinstance(result, sqlalchemy.orm.Query):
            result = [r.as_dictionary() for r in result]
        return simplejson.dumps(result)


class HTML(Aspect):
    """HTML presentation of a resource."""
    def __init__(self, next, name):
        super(HTML, self).__init__(next, name=name)

    def list(self, req, **args):
        results = self.next.list(req, **args)
        return TemplateResponse(results, {'collection': results})

    def create(self, req, **args):
        results = self.next.create(req, **args)


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
        if args.get('format'):
            results = [getattr(row, self.key) for row in results]
        return results


class REST(Aspect):
    """Expose resources via a RESTful interfaces.

    This aspect *MUST* be outermost in order for dispatching to work correctly.
    """

    def __init__(self, next, endpoint, path, legacy=True, suffix=''):
        super(REST, self).__init__(
            next, endpoint=endpoint, path=path, key=key, legacy=legacy,
            suffix=suffix,
            )

    def dispatch(self, req, endpoint, args):
        method = endpoint.rsplit(endpoint, 1)[-1]
        return getattr(self, method)(req, **args)

    def get_rules(self, map):
        """Werkzeug routing rule factory."""
        collection = self.base
        join = posixpath.join
        resource = join(self.base, self.key)
        yield Rule(collection + suffix, endpoint=self.endpoint + '_list', methods=['GET'])
        yield Rule(collection + suffix, endpoint=self.endpoint + '_create', methods=['POST'])
        yield Rule(resource + suffix, endpoint=self.endpoint + '_read', methods=['GET'])
        yield Rule(resource + suffix, endpoint=self.endpoint + '_update', methods=['PUT'])
        yield Rule(resource + suffix, endpoint=self.endpoint + '_delete', methods=['DELETE'])
        if self.legacy:
            yield Rule(collection + suffix + ';new', endpoint=self.endpoint + '_new')
            yield Rule(resource + suffix + ';edit', endpoint=self.endpoint + '_edit')


pet_controller = ModelController(Pet, 'name')

pet_api = JSON(DefaultToBasicFormat(Query(StripRequest(pet_controller)), 'name'))
pet_api = REST(pet_api, 'pet_api', '/pets/[<name>]', legacy=False, suffix='.json')


html_controller = REST(HTML(Query(StripRequest(pet_controller)), 'pet'), 'pet', '/pets/', '<name>')

req = RequestStub('/pets/', method='GET')
html_controller.dispatch(req, 'pet_list', {})
print html_controller.list(req).content
