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
    'flam.config': ['Configuration', 'Option', 'IntOption', 'FloatOption', 'ListOption', 'BoolOption'],
    'flam.web.auth': ['authenticator', 'user_loader', 'authentication_handler', 'require_authentication', 'user', 'get_session_user', 'set_session_user', 'clear_session_user'],
    'flam.web.core': ['expose', 'run_server', 'static_resource', 'json', 'Request', 'Response', 'application', 'local', 'html', 'request', 'href', 'redirect', 'static', 'flash', 'INFO', 'WARNING', 'ERROR', 'context_setup', 'request_setup', 'request_teardown', 'HTML', 'tag', 'session', 'process_form'],
    'flam.validate': ['ValidationError', 'Aspect', 'Chain', 'Range', 'Min', 'Max', 'Length', 'MinLength', 'MaxLength', 'Pattern', 'In', 'Empty', 'AnyOf', 'Not', 'FormInjector', 'Field', 'Context', 'Form'],
    'flam.adaption': ['Error', 'InvalidAdaption', 'Adaption', 'Adapter', 'adapt', 'adapts', 'remove'],
    'flam.util': ['URI', 'Signal', 'DecoratorSignal', 'cached_property', 'to_iso_time', 'from_iso_time', 'to_boolean', 'to_list', 'get_last_traceback', 'random_sleep'],
    'flam.aspects': ['weave', 'AspectBase', 'DeferredAspect', 'Aspect'],
    'flam.features': ['Error', 'UnknownFeature', 'Sequence', 'deferred', 'FeatureBroker', 'Require', 'features', 'provide', 'extend', 'append', 'require', 'remove'],
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

