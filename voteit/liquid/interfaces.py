from zope.interface import Interface


class IRepresentatives(Interface):
    """ Keeps track of potential representatives and who they're representing.
    """

    def represent(key, item):
        """ key should represent item. Makes sure item isn't representet by someone else. """

    def represented_by(key):
        """ Returns id of representative or None. """

    def release(key):
        """ Releases key so they're not represented by anyone. """