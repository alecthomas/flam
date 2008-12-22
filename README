Built around REST.

Use context-local globals to avoid passing stuff like "req" around
everywhere.

Direct correlation between model, forms (or data input) and REST interface.
Automatically expose via a JSON/XML API.

Data model objects will know how to link to themselves via URLS, and there will
be a class method on each model to allow referencing arbitrary models.

  class Host(Entity):
    hostname = Field(Unicode(128), resource_key=True)
    owner = Field(Unicode(128))

    def list(self, query):
      return query

    def read(self, host):
      return host

    def 

  >>> print Host.json.href.read('host.example.com')
  '/j/hosts/host.example.com'
  >>> print Host.json.href()


HTML built from widgets. Makes replacing fragments from AJAX easier.

Validation built in to models and forms. Automatic form filling and addition of
validation errors.
