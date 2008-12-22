#from flam import *
from aspects import *
from features import *
from elixir import *


class Page(Entity):
    name = Field(Unicode(128), primary_key=True)
    text = Field(Text, required=True)
    author = ManyToOne('Author', required=True)
    attachments = OneToMany('Attachment')


class Attachment(Entity):
    filename = Field(Unicode(255), primary_key=True)
    data = Field(Binary)
    page = ManyToOne('Page', primary_key=True)


class Author(Entity):
    username = Field(Unicode(128), primary_key=True)
    password = Field(Password(128))
    pages = OneToMany('Page')


# EntityLogic abstracts "public" operations on a base Entity. This allows
# the business logic to be separated from the controller/veiw. EntityLogic
# itself provides the basic CRUD operations.
class AuthorLogic(EntityLogic):
    entity = Author

    def authenticate(self, username, password):
        return self.read(username).password == password


# Provide a controller on top of Logic.
class AuthorHTMLController(LogicController):
    logic = AuthorLogic

    class LoginForm(Form):
        # Ensures that "username" is a key for Author
        user = Validate(AuthorLogic)
        password = Validate(Password(128))

    @route('/login', endpoint='login')
    @form(LoginForm)
    def login(self, req, form, user=None, password=None):
        if user.password == password:
            req.session['authenticated'] = 1
            return RedirectResponse(endpoint='root')
        return TemplateResponse('login.html', **form.data)


@route('/logout', endpoint='logout')
def logout(req):
    req.session['authenticated'] = 0
    return RedirectResponse(endpoint='root')


def setup(app):
    # Setup JSON handlers under /index.json and /wiki/<page>.json.
    app.expose(JSONController(Page, '/index.json', '/<name>'))
    # Setup HTML views and forms under /wiki/<page>. If page_<op>.html templates
    # are available they will be used, otherwise default views will be rendered.
    app.expose(HTMLController(Page, '[<name>]'))
    # SA filters are built up from the free variables in the route, parsed from
    # right to left. If a name is a column on the model it is filtered on. If
    # the name is a relationship, the relationships primary key is looked up
    # and the related object becomes the focus model. These two steps are
    # repeated for all free variables.
    app.expose(JSONController(Attachment, '<page>/attachment/[<filename>]'))
    app.expose(AuthorHTMLController())
    app.expose(logout)
