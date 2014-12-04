from zope.component import adapter
from zope.interface import implementer
from BTrees.OOBTree import OOBTree
from voteit.core.models.interfaces import IMeeting

from voteit.liquid.interfaces import IRepresentatives


@implementer(IRepresentatives)
@adapter(IMeeting)
class Representatives(object):
    """ Handle representatives and who they're representing. """

    def __init__(self, context):
        self.context = context

    def __nonzero__(self):
        """ Make sure this is a true boolean even if it's empty. """
        return True

    @property
    def data(self):
        """ Main storage for data. Don't manipulate this directly. """
        try:
            return self.context.__representatives_data__
        except AttributeError:
            self.context.__representatives_data__ = data = OOBTree()
            return data

    @property
    def reverse_data(self):
        """ Represented to representative key value. """
        try:
            return self.context.__representatives_data_dev__
        except AttributeError:
            self.context.__representatives_data_dev__ = data = OOBTree()
            return data

    def represent(self, key, item):
        assert key in self, "%s is not a representative" % key
        self.release(item)
        representing = list(self[key])
        representing.append(item)
        self[key] = representing

    def represented_by(self, key):
        return self.reverse_data.get(key, None)

    def release(self, key):
        """ When someone doesn't want to be represented any longer,
            or chooses another representative.
        """
        if key in self.reverse_data:
            representative = self.reverse_data[key]
            representing = list(self[representative])
            representing.remove(key)
            self[representative] = representing
            del self.reverse_data[key]

    def __setitem__(self, key, item):
        for v in item:
            self.reverse_data[v] = key
        self.data[key] = tuple(item)

    def __delitem__(self, key):
        for v in self.data[key]:
            del self.reverse_data[v]
        del self.data[key]

    def __repr__(self): #pragma : no cover
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return '<%s> adapting %r' % (classname,
                                     self.context)

    def __len__(self): return len(self.data)
    def __getitem__(self, key): return self.data[key]
    def keys(self): return self.data.keys()
    def items(self): return self.data.items()
    def values(self): return self.data.values()
    def get(self, key, failobj=None):
        if key not in self:
            return failobj
        return self[key]
    def __contains__(self, key):
        return key in self.data
    def __iter__(self):
        return iter(self.data)


def includeme(config):
    config.registry.registerAdapter(Representatives)
