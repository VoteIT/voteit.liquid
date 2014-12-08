from zope.interface import Attribute
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


class ILiquidVoter(Interface):
    """ An adapter for votes that have been added to a poll.
        It will add or change votes according to the model of
        liquid democracy that's implemented.
    """
    title = Attribute("Title")
    description = Attribute("Description")
    name = Attribute("Adapter name - register the adapter with this name.")
    voter = Attribute("UserID of the person who performed an action.")
    meeting = Attribute("Meeting object, looked up from context")
    poll = Attribute("Poll object, looked up from context")
    delegators = Attribute("A tuple of UsedIDs who delegated their vote to this voter.")

    def __call__():
        """ Perform the actual vote changes. """

    def adjust_vote(userid):
        """ Create or change the vote from 'userid'
            to look like the adapted context.
        """
