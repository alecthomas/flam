from flam import *


# context_factory is an object with callable attributes used to construct the
# real context.
#
# context_factory.req = ...
"""

Decorators provided by flam:

accept(mime_type)
route(path, endpoint, methods)
template(template)
resource(model)
unpack_form(schema)
unpack_query(schema)
"""


class Path(Unicode):
    """Represent a POSIX-style path."""
    resource_type = 'path'


class Page(Resource):
    href = Href('/api/pages/', key='path:name')

    name = Field(Path, primary_key=True)
    text = Field(UnicodeText, required=True)

    @property
    def text(self):
        """Latest page revision text."""
        return self.revisions[0]


class User(Resource):
    href = Href('/api/users/', key='name')

    name = Field(Unicode(128), resource_key=True)
    email = Feild(EMail(128))
    homepage = Field(URI(255))


class WikiController(Controller):
    # Routes can be configured explicitly by overloading Controller.routes()...
    def routes(self):
        yield Route('/login', self.login, name='login')
        yield Route('/feed', self.feed, name='feed')

    # By default a request handler returns a tuple of (template, data[, mime_type])
    def login(self):
        return 'login.html', {}

    # Some convenience decorators exist to make this a bit nicer
    @template('feed.xml', mime_type='application/xml')
    def feed(self):
        return {}

    # Routes can also be configured with a decorator, which may be stacked.
    #
    # The resource() decorator also attempts to load a resource from the URL
    # being matched. It does this by inspecting the arguments and passing them
    # to Resource.get_by(). A NotFound exception will be raised if a match is
    # not found.
    #
    # The resource is then passed to the request handler as a keyword argument
    # with the lower case name of the resource class.
    #
    # eg. The URL /HomePage would result in:
    #   view_wiki_page(page=Page.get_by(name='HomePage'))
    # (with appropriate error handling)
    #
    @route('/<path:name>', endpoint='wiki_view', methods='GET')
    @template('wiki_view.html')
    @resource(Page)
    def read_page(self, page):
        return {'page': page}

    @route('/<path:name>', endpoint='wiki_edit', methods='POST')
    @template('wiki_edit.html')
    @resource(Page)
    # unpack_form() unpacks form fields into arguments, based on the given Form
    # class (which in this case is also a Page object).
    @unpack_form(Page)
    def update_page(self, page, name, text):
        pass


# Flam uses class "statements" to aid in reducing boilerplate code. One example
# is the "resource" statement:

class WikiController(Controller):
    # The "resource()" statement automatically adds CRUD methods for the Page
    # resource, mapping to templates in the form
    # '<resource_name>_<crud_operation>.html' and performs basic form handling.
    #
    # For example, the statment "resource(Page, '/<path:name>')" would produce:
    #
    # @route('/<path:name>;create', endpoint='page_create', methods='POST')
    # @template('page_create.html')
    # @resource(Page)
    # def create_page(self, page):
    #     form = req.form
    #     page.validate(form)
    #     if form
    #
    # @route('/<path:name>', endpoint='page_view', methods='GET')
    # @template('page_view.html')
    # @resource(Page)
    # @unpack_form
    # def read_page(self, page):
    #     return {'page': page}
    #
    resource(Page, '/<path:name>')

    def read_page(self, page):
        return {'page': page}
