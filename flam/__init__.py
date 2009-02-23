# encoding: utf-8
"""flam /flæm/ noun, verb, flammed, flam⋅ming. Informal. –noun 1. a deception
or trick. 2. a falsehood; lie. –verb (used with object), verb (used without
object) 3. to deceive; delude; cheat.

Flam - A minimalist Python application framework.
"""

from types import ModuleType
import sys


all_by_module = {
    # XXX Do not delete this section. It is automatically rebuilt by "setup
    # build".

    # BEGIN IMPORTS
    'flam.core': ['Error'],
    'flam.config': ['ListOption', 'Option', 'IntOption', 'FloatOption', 'BoolOption', 'Configuration'],
    'flam.web.auth': ['require_authentication', 'get_session_user', 'authentication_handler', 'user_loader', 'authenticator', 'set_session_user', 'user', 'clear_session_user'],
    'flam.web.core': ['static_resource', 'run_server', 'process_form', 'session', 'static', 'wsgi_application', 'redirect', 'context_setup', 'flash', 'application', 'json', 'WARNING', 'tag', 'local', 'Response', 'request_teardown', 'request_setup', 'HTML', 'expose', 'Request', 'ERROR', 'INFO', 'request', 'html', 'href'],
    'flam.validate': ['ValidationError', 'Chain', 'Min', 'Pattern', 'MaxLength', 'Range', 'Field', 'Length', 'MinLength', 'Aspect', 'Context', 'Max', 'Not', 'FormInjector', 'In', 'AnyOf', 'Empty', 'Form'],
    'flam.adaption': ['adapts', 'Adapter', 'remove', 'adapt', 'InvalidAdaption', 'Adaption'],
    'flam.util': ['to_boolean', 'cached_property', 'Signal', 'to_list', 'URI', 'to_iso_time', 'from_iso_time', 'DecoratorSignal', 'get_last_traceback', 'random_sleep'],
    'flam.aspects': ['DeferredAspect', 'AspectBase', 'Aspect', 'weave'],
    'flam.features': ['features', 'extend', 'Sequence', 'provide', 'Require', 'FeatureBroker', 'remove', 'deferred', 'UnknownFeature', 'require', 'append'],
    # END IMPORTS
    }

# List of modules to export directly.
attribute_modules = dict.fromkeys([])


object_origins = {}
for module, items in all_by_module.iteritems():
    for item in items:
        object_origins[item] = module


class module(ModuleType):
    __doc__

    def __getattr__(self, name):
        if name in object_origins:
            module = __import__(object_origins[name], None, None, [name])
            for extra_name in all_by_module[module.__name__]:
                setattr(self, extra_name, getattr(module, extra_name))
            return getattr(module, name)
        elif name in attribute_modules:
            __import__('flam.' + name)
        return ModuleType.__getattribute__(self, name)


# keep a reference to this module so that it's not garbage collected
old_module = sys.modules['flam']

# setup the new module and patch it into the dict of loaded modules
new_module = sys.modules['flam'] = module('flam')
new_module.__dict__.update({
    '__file__': __file__,
    '__path__': __path__,
    '__doc__':  __doc__,
    '__all__':  tuple(object_origins) + tuple(attribute_modules)
})

