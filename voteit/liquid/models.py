from BTrees.OOBTree import OOBTree
from pyramid.decorator import reify
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from pyramid.traversal import find_interface
from pyramid.traversal import resource_path
from voteit.core.interfaces import IObjectAddedEvent
from voteit.core.interfaces import IObjectUpdatedEvent
from voteit.core.models.interfaces import IMeeting
from voteit.core.models.interfaces import IPoll
from voteit.core.models.interfaces import IVote
from voteit.core.security import ADD_VOTE
from voteit.core.security import find_authorized_userids
from voteit.core.security import ROLE_OWNER
from zope.component import adapter
from zope.event import notify
from zope.interface import implementer

from voteit.liquid import _
from voteit.liquid import logger
from voteit.liquid.events import DelegationEnabled
from voteit.liquid.events import DelegationWillBeDisabled
from voteit.liquid.events import RepresentativeAddedVote
from voteit.liquid.events import RepresentativeChangedVote
from voteit.liquid.events import RepresentativeEnabled
from voteit.liquid.events import RepresentativeWillBeDisabled
from voteit.liquid.interfaces import ILiquidVoter
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

    def enable_representative(self, key):
        if key not in self:
            self.release(key)
            self[key] = ()
            event = RepresentativeEnabled(self.context, representative = key)
            notify(event)

    def disable_representative(self, key):
        if key in self:
            event = RepresentativeWillBeDisabled(self.context, representative = key)
            notify(event)
            for delegator in self[key]:
                self.release(delegator)
            del self[key]

    def represent(self, key, item):
        assert key in self, "%s is not a representative" % key
        assert key != item, "Representative and represented can't be the same"
        self.release(item)
        representing = list(self[key])
        representing.append(item)
        self[key] = representing
        event = DelegationEnabled(self.context, representative = key, delegator = item)
        notify(event)

    def represented_by(self, key):
        return self.reverse_data.get(key, None)

    def release(self, key):
        """ When someone doesn't want to be represented any longer,
            or chooses another representative.
        """
        if key in self.reverse_data:
            representative = self.reverse_data[key]
            event = DelegationWillBeDisabled(self.context, representative = representative, delegator = key)
            notify(event)
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


@adapter(IVote)
@implementer(ILiquidVoter)
class LiquidVoter(object):
    title = ""
    description = ""
    name = ""

    def __init__(self, context):
        self.context = context

    @reify
    def meeting(self):
        return find_interface(self.context, IMeeting)

    @reify
    def poll(self):
        return find_interface(self.context, IPoll)

    @reify
    def repr(self):
        return IRepresentatives(self.meeting)

    def __call__(self, voter):
        """ Note that voter here represents the person who initiated the action. """
        raise NotImplementedError() #pragma : no cover

    def adjust_owner(self, userid):
        if userid == self.context.__name__ and userid not in self.context.creators:
            self.context.add_groups(userid, (ROLE_OWNER,), event = False)
            self.context.del_groups(self.context.creators[0], (ROLE_OWNER,), event = False)
            self.context.creators = [userid]

    def adjust_vote(self, userid):
        """ Adjust another vote to look like the adapted context. """
        #FIXME: Should the adjustments be tracked in some way?
        logger.debug("Adjusting vote for '%s'" % userid)
        representative = self.repr.represented_by(userid)
        if userid in self.poll:
            vote = self.poll[userid]
            if userid in vote.creators:
                logger.debug("%r has voted themselves to representative %r won't have any effect on the vote %r" % (userid, representative, vote))
            else:
                logger.debug("Changing vote %r to look like %r" % (resource_path(vote), resource_path(self.context)))
                vote.set_vote_data(self.context.get_vote_data())
                event = RepresentativeChangedVote(vote, representative = representative, delegator = userid)
                notify(event)
        else:
            poll_plugin = self.poll.get_poll_plugin()
            Vote = poll_plugin.get_vote_class()
            assert representative is not None, "Tried to adjust vote where no representative was found"
            vote = Vote(creators = [representative], representative = representative)
            vote.set_vote_data(self.context.get_vote_data(), notify = False)
            self.poll[userid] = vote
            logger.debug("Added new vote %r that looks like %r" % (resource_path(vote), resource_path(self.context)))
            event = RepresentativeAddedVote(vote, representative = representative, delegator = userid)
            notify(event)


def handle_votes(context, event):
    request = get_current_request()
    ld_name = request.registry.settings.get('voteit.liquid.type', None)
    voter = request.authenticated_userid
    if voter is None:
        logger.warn("handle_votes method couldn't find a valid userid. This should only happen during scripts or testing. Will abourt vote delegation.")
        return
    if ld_name:
        lv = request.registry.getAdapter(context, ILiquidVoter, name = ld_name)
        lv(voter)


class SimpleAdjustVotes(LiquidVoter):
    title = _("Simple add/adjust votes")
    description = __doc__ = _("""
        Adds votes for delegators. If a vote has been changed by a delegator,
        the representative won't have any effect on that vote.
        
        Note that delegators still need the permission to add a vote for their votes to be added.
        It's not enough that the representative has the permission to do so.
    """)
    name = "simple"

    def __call__(self, voter):
        if voter not in self.repr:
            logger.debug("Curren't user wasn't a representative, but we may need to adjust ownership")
            self.adjust_owner(voter)
            return
        all_voters = find_authorized_userids(self.poll, [ADD_VOTE])
        for userid in self.repr.get(voter, ()):
            if userid in all_voters:
                logger.info("%r adjusted vote for %r in poll %r" % (voter, userid, resource_path(self.poll)))
                self.adjust_vote(userid)
            else:
                logger.debug("%r doesn't have the add vote permission, so representative %r can't add one for this user." % (userid, voter))


def includeme(config):
    config.registry.registerAdapter(Representatives)
    config.registry.registerAdapter(SimpleAdjustVotes, name = SimpleAdjustVotes.name)
    config.add_subscriber(handle_votes, (IVote, IObjectAddedEvent))
    config.add_subscriber(handle_votes, (IVote, IObjectUpdatedEvent))
