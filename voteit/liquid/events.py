from zope.interface import implementer

from voteit.liquid.interfaces import IRepresentationEvent
from voteit.liquid.interfaces import IRepresentativeEnabled
from voteit.liquid.interfaces import IRepresentativeWillBeDisabled
from voteit.liquid.interfaces import IDelegationEnabled
from voteit.liquid.interfaces import IDelegationWillBeDisabled
from voteit.liquid.interfaces import IRepresentativeAddedVote
from voteit.liquid.interfaces import IRepresentativeChangedVote


@implementer(IRepresentationEvent)
class RepresentationEvent(object):

    def __init__(self, context, representative = None, delegator = None, **kw):
        self.context = context
        self.representative = representative
        self.delegator = delegator
        self.__dict__.update(kw)


@implementer(IRepresentativeEnabled)
class RepresentativeEnabled(RepresentationEvent):
    """ See voteit.liquid.interfaces.IRepresentativeEnabled """


@implementer(IRepresentativeWillBeDisabled)
class RepresentativeWillBeDisabled(RepresentationEvent):
    """ See voteit.liquid.interfaces.IRepresentativeWillBeDisabled """


@implementer(IDelegationEnabled)
class DelegationEnabled(RepresentationEvent):
    """ See voteit.liquid.interfaces.IDelegationEnabled """


@implementer(IDelegationWillBeDisabled)
class DelegationWillBeDisabled(RepresentationEvent):
    """ See voteit.liquid.interfaces.IDelegationWillBeDisabled """


@implementer(IRepresentativeAddedVote)
class RepresentativeAddedVote(RepresentationEvent):
    """ See voteit.liquid.interfaces.IRepresentativeAddedVote """
 
 
@implementer(IRepresentativeChangedVote)
class RepresentativeChangedVote(RepresentationEvent):
    """ See voteit.liquid.interfaces.IRepresentativeChangedVote """
