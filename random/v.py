"""
flam_login.html
login.html
/login
authenticate(username, password)
"""



@fetch_user
def fetch_user(username):
    return User.get(username)

@authentication_handler
def login():
    return authentication_form('login.html', time=datetime.now())


@authenticate_user
def authenticate(user, password):
    if hasattr(user, 'password'):
        return user.password == password
    elif hasattr(user, 'passwd'):
        return user.passwd == password


@auth_required
@expose
def settings():
    ...


# Form validation...
@expose
def admin():
    operators = model.Operator.query.all()
    valid, html = process_form('admin.html', form_add_operator, operators=operators)
    if valid:
        password = ...
        ...
        operators.append(o)
    return html

