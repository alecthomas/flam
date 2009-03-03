# encoding: utf-8
#
# Copyright (C) 2008-2009 Alec Thomas <alec@swapoff.org
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

"""Form validation for Genshi.

First a couple of HTML forms:

>>> from genshi import HTML
>>> html = HTML('''
... <body>
...   <form id="user">
...     <input type="text" name="name"/>
...     <input type="text" name="age"/>
...     <input type="submit" id="create" value="Create user"/>
...   </form>
...   <form id="controls">
...     <input type="text" name="page"/>
...     <input type="submit" name="delete"/>
...     <input type="submit" name="copy"/>
...   </form>
... </body>
... '''.strip())

Then some fake POST data:

>>> user_data = {'name': 'Alec', 'age': '12'}
>>> control_data = {'page': 'one'}

Finally we define our forms. Validation for fields is built up from a set of
discrete aspects we wish to validate:

>>> user_form = Form('user')
>>> user_form.add('name', MinLength(6), 'Name must be at least 6 characters.')
>>> user_form.add('age', Chain(int, Min(18)), 'Age must be an integer > 18.')

We can have multiple validators per field:

>>> user_form.add('name', Pattern(r'^[a-z]+$'), 'Name must be all lower case.')

Forms can also be defined declaratively:

>>> class ControlForm(Form):
...   page = Field('page', int, 'Page must be an integer.')
>>> control_form = ControlForm('control')

Once your forms are defined, we can validate the input:

>>> context = user_form.validate(user_data)
>>> print sorted(context.fields.items())
[('age', '12'), ('name', 'Alec')]
>>> print '\\n'.join(map(repr, sorted(context.errors.items())))
('age', ['Age must be an integer > 18.'])
('name', ['Name must be at least 6 characters.', 'Name must be all lower case.'])

And the controls form:

>>> control_context = control_form.validate(control_data)
>>> print '\\n'.join(map(repr, sorted(control_context.errors.items())))
('page', ['Page must be an integer.'])

Oops. Let's inform the user by inserting error messages into the Genshi HTML
stream:

>>> print html | context | control_context
<body>
  <form id="user">
    <input type="text" name="name" class="error"/><div class="error">Name must be all lower case.</div><div class="error">Name must be at least 6 characters.</div>
    <input type="text" name="age" class="error"/><div class="error">Age must be an integer &gt; 18.</div>
    <input type="submit" id="create" value="Create user"/>
  </form>
  <form id="controls">
    <input type="text" name="page"/>
    <input type="submit" name="delete"/>
    <input type="submit" name="copy"/>
  </form>
</body>

Then imagine they've corrected their input:

>>> user_data['name'] = 'alecthomas'
>>> user_data['age'] = '18'
>>> context = user_form.validate(user_data)
>>> sorted(context.fields.items())
[('age', 18), ('name', 'alecthomas')]
>>> context.errors
{}

Better.
"""

import re
from genshi.builder import tag
from genshi.filters.transform import Transformer


__all__ = [
    'ValidationError', 'Aspect', 'Chain', 'Range', 'Min', 'Max', 'Length',
    'MinLength', 'MaxLength', 'Pattern', 'In', 'Empty', 'AnyOf', 'Not',
    'FormInjector', 'Field', 'Context', 'Form',
    ]


class ValidationError(Exception):
    pass


class Aspect(object):
    """A marker class for validation aspects that need the validation context.

    This can be the case if validation depends on multiple fields or other
    aspects of the form.
    """
    def apply(context, value, *aspects):
        """Apply aspects of validation to a value."""
        for aspect in aspects:
            if isinstance(aspect, Aspect):
                value = aspect(context, value)
            else:
                value = aspect(value)
        return value
    apply = staticmethod(apply)


class Chain(Aspect):
    def __init__(self, *aspects):
        self.aspects = aspects

    def __call__(self, context, value):
        return Aspect.apply(context, value, *self.aspects)


class Range(object):
    def __init__(self, min=None, max=None):
        self.min = min
        self.max = max

    def __call__(self, value):
        assert self.min is None or value >= self.min
        assert self.max is None or value <= self.max
        return value


class Min(Range):
    def __init__(self, min):
        super(Min, self).__init__(min=min)


class Max(Range):
    def __init__(self, max):
        super(Max, self).__init__(max=max)


class Length(Range):
    def __call__(self, value):
        super(Length, self).__call__(len(value))
        return value


class MinLength(Length):
    def __init__(self, min):
        super(MinLength, self).__init__(min=min)


class MaxLength(Length):
    def __init__(self, max):
        super(MaxLength, self).__init__(max=max)


class Pattern(object):
    def __init__(self, pattern):
        self.pattern = re.compile(pattern)

    def __call__(self, value):
        assert self.pattern.match(value)
        return value


class In(object):
    def __init__(self, element):
        self.element = element

    def __call__(self, value):
        assert self.element in value
        return value


class Empty(object):
    def __call__(self, value):
        assert not value
        return value


class AnyOf(object):
    def __init__(self, *values):
        self.values = values

    def __call__(self, value):
        assert value in self.values
        return value


class Not(object):
    def __init__(self, aspect):
        self.aspect = aspect

    def __call__(self, value):
        try:
            self.aspect(value)
            raise ValidationError()
        except (ValueError, ValidationError, AssertionError):
            return value


class FormInjector(object):
    """Insert messages into a Genshi stream."""

    def __init__(self, form, errors):
        self.form = form
        self.errors = errors

    def __call__(self, stream):
        for name, messages in self.errors.items():
            for message in messages:
                field = self.form.get_field(name)
                message = self.form.format_error(message)
                transform = Transformer('//form[@id="%s"]' % self.form.id) \
                            .select(field.path).attr('class', 'error')
                transform = getattr(transform, field.where)(message)
                stream |= transform
        return stream


class Field(object):
    def __init__(self, name, aspect=None, message='Invalid field.', hint=None,
                 path=None, where='after'):
        self.name = name
        self.message = message
        self.aspect = aspect or (lambda v: v)
        self.path = path
        self.where = where
        self.hint = hint
        if self.path is None:
            self.path = '//input[@name="%(name)s"] | ' \
                        '//textarea[@name="%(name)s"] | ' \
                        '//select[@name="%(name)s"]' % {'name': name}

    def validate(self, context, value):
        return Aspect.apply(context, value, self.aspect)


class Context(object):
    """A validation context."""
    def __init__(self, form, data, fields=None, errors=None):
        self.form = form
        self.data = data
        self.fields = fields or {}
        self.errors = errors or {}

    def inject_errors(self):
        import warnings
        warnings.warn('"stream | context.inject_errors()" is deprecated. '
                      'Use "stream | context" instead.', DeprecationWarning,
                      stacklevel=2)
        return self.form.injector(self.form, self.errors)

    def __call__(self, stream):
        return stream | self.form.injector(self.form, self.errors)

    def set_error(self, name, message):
        """Explicitly set a field error message."""
        self.errors[name] = message


class Form(object):
    """A form validator."""

    def __init__(self, id, fields=None, injector=FormInjector):
        self.fields = []
        # Load fields from object attributes.
        for key, value in self.__class__.__dict__.items():
            if isinstance(value, Field):
                if value.name is None:
                    value.name = key
                self.add(value)
        if fields:
            for field in fields:
                self.add(field)
        self.id = id
        self.injector = injector

    def get_field(self, name):
        for field in self.fields:
            if field.name == name:
                return field

    def add(self, name, *args, **kwargs):
        """Add a new Field."""
        if isinstance(name, Field):
            field = name
            name = field.name
            assert name, 'Field must have a name'
        else:
            field = Field(name, *args, **kwargs)
        self.fields.append(field)
        field.form = self

    def format_error(self, message):
        return tag.div(message, class_='error')

    def format_hint(self, hint):
        return tag.div(hint, class_='hint')

    def validate(self, data):
        """Validate the given data.

        Returns a tuple of (fields, errors) where both are dictionaries
        mapping field names to text.
        """
        context = Context(self, data)
        for field in self.fields:
            name = field.name
            context.fields[name] = value = data.get(name, '')
            try:
                context.fields[name] = field.validate(context, value)
            except ValidationError, e:
                context.errors.setdefault(name, []).append(unicode(e))
            except (ValueError, AssertionError):
                context.errors.setdefault(name, []).append(field.message)
        return context


if __name__ == '__main__':
    import doctest
    doctest.testmod()
