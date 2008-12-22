class PropertyMeta(type):
    def __new__(cls, name, bases, d):
        new_cls = type.__new__(cls, name, bases, d)
