from flam import *

"""
Operations:

CREATE:
    0. (for HTML only) Render form.
    2. Validate data.
    3. Create resource.

READ:
    1. Convert data into rendered form.

UPDATE:
    0. (for HTLM only) Render form.
    1. Validate data.
    2. Update resource.

DELETE:
    0. (for HTML only) Render confirmation form.
    1. Delete resource.

LIST:
    1. Render list.
"""


class ResourceController(object):
    def __init__(self, cls, path, resource_path=None, key=None, parent=None):
        self.cls = cls
        self.name = cls.__name__.lower()
        self.path = path
        if resource_path is None:
            resource_path = posixpath.join(self.path, '<' + self.name + '>')
        self.resource_path = resource_path
        if key is None:
            key = cls.mapper.primary_keys
            assert len(key) == 1
            key = key[0]
        self.key = key
        self.parent = parent

    def get_rules(self):
        """werkzeug.routing integration method."""
        yield Rule(self.path, endpoint='list_' + self.name, callback=self.list)
        yield Rule(self.resource_path, endpoint='read_' + self.name,
                   callback=self.read)
        yield Rule(self.resource_path, endpoint='create_' + self.name,
                   callback=self.read)

    def _lookup(self, key):
        args = {self.key: key}
        return self.cls.get_by(**args)

    def create(self, req, key, **args):
        pass

    def read(self, req, type='html'):
        renderer = adapt(type(self), type)
        return renderer.render(req)

    def update(self, req):
        pass


class Person(Entity):
    name = Field(Unicode, required=True)
    age = Field(Integer, min=18)
    cars = OneToMany('Car')


class Car(Entity):
    model = Field(Unicode, required=True)
    year = Field(Integer)


car_controller = ResourceController(Car, '/cars/')

tom = Person(name='Tom', age=27)
tom.cars.append(Car(model='Sunbird', year=1978))


def render(req, what, type='html'):
    renderer = adapt(what, type)
    return renderer.render(req)


print tom.transform('html')
print tom.render_view(req)
print req.render(tom)
