from ape.web import *
from ape.adaption import *


class Pet(Entity):
    name = Field(Unicode(255), resource_key=True)
    owner = ManyToOne('Owner')


class PetController(Controller):
    def list(self):
        query = Pet.query()
        return adapt(query, JSONResponse)
        args = req.args
        q = args.get('q', '')
        if q:
            query = Filter(query, q)
        if req.content_type == 'application/json':
            format = args.get('format', 'brief')
            if format == 'brief':
                return JSONResponse([c.name for c in query])
            elif format == 'detailed':
                return JSONResponse(query.all())
        else:
            query = Paginate(query, args)
            return TemplateResponse('pet_list.html', {'pets': query})

    def create(self):
        if req.content_type == 'application/json':
            data = adapt(req, dict)
        else:
            data = req.form
        pet = Pet(**data)
        db.commit()
        if req.content_type == 'application/json':
            return JSONResponse(pet.as_dict(), status=201)
        else:
            return TemplateResponse('pet_read.html', {'pet': pet})

    def read(self, key):
        pet = Pet.get_by(name=key)
        if req.content_type == 'application/json':
            return pet.to_dictionary()
        else:
            return TemplateResponse('pet_read.html', {'pet': pet})

    def update(self, key):
        pet = Pet.get_by(name=key)
        if req.content_type == 'application/json':
            data = adapt(req, dict)
        else:
            data = req.form
        pet.from_dict(data)
        if req.content_type == 'application/json':
            return JSONResponse(pet.as_dict(), status=201)
        else:
            return TemplateResponse('pet_read.html', {'pet': pet})




class ModelOps(object):
    """Model operations."""

    def list(self, query):
        """Filter and return the SQLAlchemy query."""

    def create(self, cls, data):
        """Filter data before creating a new entity."""

    def read(self, entity):
        """Filter and return the given entity."""

    def update(self, entity, data):
        """Filter data before it is applied to entity."""

    def delete(self, entity):
        """Filter before deleting entity."""


class ModelToView(object):
    """Translation to and from the model and view."""

    def list(self, query):
        """Build and return an SQLAlchemy query for the model."""
        return cls.query()

    def create(self, cls, data):
        """Create a new entity from the provided data."""
        return cls(**data)

    def read(self, cls, key):
        """Return entity object for the given resource key."""
        resource_key = cls.resource_key
        return cls.get_by(**{resource_key: key})

    def update(self, cls, key, data):
        """Update an entity."""


class JSONController(CRUDController):
    def discriminate(self):
        return 'application/json' in req.accept_mimetypes

    def list(self, query):
        return cls.query()
