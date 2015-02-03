from zope.interface import Attribute
from zope.interface import Interface


class IRepresentatives(Interface):
    """ Keeps track of potential representatives and who they're representing.
    """


    def enable_representative(key):
        """ Mark someone as a representative.
            Sends the event IRepresentativeEnabled when completed
        """

    def disable_representative(key):
        """ Remove someone from the list of representatives. This will also release the
            voting power back to the original users. (The delegators)
            See the release method too.
            
            Sends the event IRepresentativeDisabled before it's actually removed,
            to allow for cleanup or other notifications.
        """

    def represent(key, item):
        """ key should represent item. Makes sure item isn't represented by someone else.
        
            Sends the event IDelegationEnabled when a link is established.
        """

    def represented_by(key):
        """ Returns id of representative or None. """

    def release(key):
        """ Releases key so they're not represented by anyone.
        
            Sends the event I DelegationDisabled before the link is broken and the vote is released.
        """


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
            
            Sends the event IRepresentativeAddedVote
            or IRepresentativeChangedVote.
        """


class IRepresentationEvent(Interface):
    """ Raised for any significant things that might go on
        regarding liquid democracy. Subclass this to create
        specific events.
    """
    context = Attribute("The context where the event took place.")
    representative = Attribute("UserID of the representative, if present.")
    delegator = Attribute("UserID of the delegator, if present.")

    def __init__(context, repesentative = None, delegator = None, **kw):
        """ kwargs are addded as attributes. """


class IRepresentativeEnabled(IRepresentationEvent):
    """ When someone marks themselves as an eligible representative.
    """

class IRepresentativeWillBeDisabled(IRepresentationEvent):
    """ When someone no longer wish to be a representative.
    """

class IDelegationEnabled(IRepresentationEvent):
    """ The delegator picked a representative.
    """

class IDelegationWillBeDisabled(IRepresentationEvent):
    """ The delegator has chosen to either take back their vote or give it to someone else.
    """

class IRepresentativeAddedVote(IRepresentationEvent):
    """ When a representative adds a vote for a delegator.
        The context here is the vote object.
    """
 
class IRepresentativeChangedVote(IRepresentationEvent):
    """ When a representative changes a vote for a delegator.
        The context here is the vote object.
    """
