from types import ModuleType
import sys


all_by_module = {
    'flam.web': ['expose', 'run_server', 'static_resource', 'json', 'Request',
                 'Response', 'application', 'local', 'html', 'request', 'href',
                 'redirect', 'static', 'flash', 'INFO', 'WARNING',
                 'ERROR','context_setup', 'request_setup', 'request_teardown'],
    'flam.util': ['URI', 'cached_property', 'to_iso_time', 'from_iso_time',
                  'to_boolean', 'to_list', 'get_last_traceback', 'random_sleep'],
}

attribute_modules = dict.fromkeys([])


object_origins = {}
for module, items in all_by_module.iteritems():
    for item in items:
        object_origins[item] = module


class module(ModuleType):
    """Automatically import objects from the modules."""

    def __getattr__(self, name):
        if name in object_origins:
            module = __import__(object_origins[name], None, None, [name])
            for extra_name in all_by_module[module.__name__]:
                setattr(self, extra_name, getattr(module, extra_name))
            return getattr(module, name)
        elif name in attribute_modules:
            __import__('werkzeug.' + name)
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

