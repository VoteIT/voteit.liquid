from unittest import TestCase

from pyramid import testing
from pyramid.httpexceptions import HTTPForbidden
from voteit.core.models.meeting import Meeting
from voteit.core.models.user import User
from voteit.core.models.vote import Vote
from voteit.core.security import unrestricted_wf_transition_to
from voteit.core.testing_helpers import bootstrap_and_fixture
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from voteit.liquid.interfaces import IDelegationEnabled
from voteit.liquid.interfaces import IDelegationWillBeDisabled
from voteit.liquid.interfaces import ILiquidVoter
from voteit.liquid.interfaces import IRepresentativeAddedVote
from voteit.liquid.interfaces import IRepresentativeChangedVote
from voteit.liquid.interfaces import IRepresentativeEnabled
from voteit.liquid.interfaces import IRepresentativeWillBeDisabled
from voteit.liquid.interfaces import IRepresentatives


class RepresentativesTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from voteit.liquid.models import Representatives
        return Representatives

    def test_verify_class(self):
        self.failUnless(verifyClass(IRepresentatives, self._cut))

    def test_verify_object(self):
        self.failUnless(verifyObject(IRepresentatives, self._cut(Meeting())))


    def test_enable_representative(self,):
        obj = self._cut(Meeting())
        obj.enable_representative('hello')
        self.assertIn('hello', obj)
        
    def test_disable_representative(self):
        obj = self._cut(Meeting())
        obj['goodbye'] = ()
        obj.disable_representative('goodbye')
        self.assertNotIn('goodbye', obj)

    def test_disable_representative_releases_represented(self):
        obj = self._cut(Meeting())
        obj['goodbye'] = ('james', 'jane')
        self.assertEqual(obj.represented_by('james'), 'goodbye')
        obj.disable_representative('goodbye')
        self.assertNotIn('goodbye', obj)
        self.assertEqual(obj.represented_by('james'), None)

    def test_event_on_enable_repr(self):
        L = []
        def subscriber(event):
            L.append(event)
        self.config.add_subscriber(subscriber, IRepresentativeEnabled)
        obj = self._cut(Meeting())
        obj.enable_representative('hello')
        self.assertEqual(len(L), 1)

    def test_event_on_disable_repr(self):
        L = []
        def subscriber(event):
            L.append(event)
        self.config.add_subscriber(subscriber, IRepresentativeWillBeDisabled)
        obj = self._cut(Meeting())
        obj.disable_representative('hello')
        self.assertEqual(len(L), 0)
        obj['hello'] = ()
        obj.disable_representative('hello')
        self.assertEqual(len(L), 1)

    def test_represent(self):
        obj = self._cut(Meeting())
        obj['one'] = ()
        obj.represent('one', 'two')
        self.assertIn('two', obj['one'])

    def test_represent_not_a_representative(self):
        obj = self._cut(Meeting())
        self.assertRaises(AssertionError, obj.represent, 'one', 'two')

    def test_represent_self_error(self):
        obj = self._cut(Meeting())
        obj.enable_representative('one')
        self.assertRaises(AssertionError, obj.represent, 'one', 'one')

    def test_event_on_represent(self):
        L = []
        def subscriber(event):
            L.append(event)
        self.config.add_subscriber(subscriber, IDelegationEnabled)
        obj = self._cut(Meeting())
        obj['one'] = ()
        obj.represent('one', 'two')
        self.assertEqual(len(L), 1)
        self.assertEqual(L[0].representative, 'one')
        self.assertEqual(L[0].delegator, 'two')

    def test_represented_by(self):
        obj = self._cut(Meeting())
        self.assertEqual(obj.represented_by('one'), None)
        obj['two'] = ()
        obj.represent('two', 'one')
        self.assertEqual(obj.represented_by('one'), 'two')

    def test_release(self):
        obj = self._cut(Meeting())
        obj['one'] = ('two', 'three',)
        obj.release('two')
        self.assertNotIn('two', obj['one'])
        self.assertEqual(obj.represented_by('two'), None)

    def test_event_on_release(self):
        L = []
        def subscriber(event):
            L.append(event)
        self.config.add_subscriber(subscriber, IDelegationWillBeDisabled)
        obj = self._cut(Meeting())
        obj['one'] = ()
        obj.represent('one', 'two')
        obj.release('two')
        self.assertEqual(len(L), 1)
        self.assertEqual(L[0].representative, 'one')
        self.assertEqual(L[0].delegator, 'two')

    def test_del_releases(self):
        obj = self._cut(Meeting())
        obj['one'] = ('two', 'three',)
        del obj['one']
        self.assertEqual(obj.represented_by('two'), None)        

    def test_new_representation_releases_old(self):
        obj = self._cut(Meeting())
        obj['cand_one'] = ('one',)
        obj['cand_two'] = ()
        obj.represent('cand_two', 'one')
        self.assertEqual(obj['cand_one'], ())
        self.assertEqual(obj['cand_two'], ('one',))

    def test_get(self):
        obj = self._cut(Meeting())
        obj['one'] = ()
        _marker = object()
        self.assertEqual(obj.get('blabla', _marker), _marker)
        self.assertEqual(obj.get('one', _marker), ())
        self.assertEqual(obj.get('blabla'), None)

    def test_iter(self):
        obj = self._cut(Meeting())
        obj['one'] = ()
        obj['two'] = ()
        self.assertEqual([x for x in obj], ['one', 'two'])

    def test_integration(self):
        self.config.registry.settings['voteit.liquid.type'] = 'simple'
        self.config.include('voteit.liquid')
        m = Meeting()
        self.failUnless(IRepresentatives(m, None))


def _voting_fixture(config):
    #Note: active_poll_fixture may clear registry.settings
    from voteit.core.testing_helpers import active_poll_fixture
    config.include('voteit.core.plugins.majority_poll')
    root = active_poll_fixture(config)
    poll = root['meeting']['ai']['poll']
    poll.set_field_value('poll_plugin', 'majority_poll')
    poll['one'] = vote = Vote(creators = ['one'])
    vote.set_vote_data({'a': 1, 'b': 2}, notify = False)
    return vote


class LiquidVoterTests(TestCase):
 
    def setUp(self):
        self.config = testing.setUp()
        self.config.include('voteit.liquid.models')
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from voteit.liquid.models import LiquidVoter
        return LiquidVoter
 
    def test_verify_class(self):
        self.failUnless(verifyClass(ILiquidVoter, self._cut))
 
    def test_verify_object(self):
        vote = _voting_fixture(self.config)
        self.failUnless(verifyObject(ILiquidVoter, self._cut(vote)))
 
    def test_adjust_owner(self):
        vote = _voting_fixture(self.config)
        vote.creators = ['someone_else']
        obj = self._cut(vote)
        obj.adjust_owner('one')
        self.assertIn('one', vote.creators)
        self.assertNotIn('someone_else', vote.creators)
 
    def test_adjust_vote_new_vote(self):
        vote = _voting_fixture(self.config)
        obj = self._cut(vote)
        obj.repr.enable_representative('one')
        obj.repr.represent('one', 'other')
        obj.adjust_vote('other')
        poll = vote.__parent__
        self.assertIn('other', poll)
        self.assertEqual(poll['other'].get_vote_data(), {'a': 1, 'b': 2})
 
    def test_adjust_vote_existing(self):
        vote = _voting_fixture(self.config)
        poll = vote.__parent__
        other = Vote(creators = ['one'])
        other.set_vote_data({'c': 3}, notify = False)
        poll['other'] = other
        obj = self._cut(vote)
        obj.adjust_vote('other')
        self.assertIn('other', poll)
        self.assertEqual(poll['other'].get_vote_data(), {'a': 1, 'b': 2})

    def test_adjust_vote_wont_touch_delegators_own_votes(self):
        vote = _voting_fixture(self.config)
        poll = vote.__parent__
        obj = self._cut(vote)
        obj.repr.enable_representative('one')
        obj.repr.represent('one', 'other')
        other = Vote(creators = ['other'])
        other.set_vote_data({'c': 3}, notify = False)
        poll['other'] = other
        obj = self._cut(other)
        obj.adjust_vote('other')
        self.assertEqual(vote.get_vote_data(), {'a': 1, 'b': 2})
        self.assertEqual(other.get_vote_data(), {'c': 3})
        self.assertEqual(obj.repr.represented_by('other'), 'one')

 
class SimpleAdjustVotesTests(TestCase):
 
    def setUp(self):
        self.config = testing.setUp()
        
    def tearDown(self):
        testing.tearDown()
 
    @property
    def _cut(self):
        from voteit.liquid.models import SimpleAdjustVotes
        return SimpleAdjustVotes
 
    def test_verify_class(self):
        self.failUnless(verifyClass(ILiquidVoter, self._cut))
 
    def test_verify_object(self):
        self.config.include('voteit.liquid.models')
        vote = _voting_fixture(self.config)
        self.failUnless(verifyObject(ILiquidVoter, self._cut(vote)))

    def test_delegators_without_voting_perm(self):
        vote = _voting_fixture(self.config)
        self.config.testing_securitypolicy(userid = 'jane')
        poll = vote.__parent__
        self.config.registry.settings['voteit.liquid.type'] = 'simple'
        self.config.include('voteit.liquid.models')
        obj = self._cut(vote)
        repr = IRepresentatives(obj.meeting)
        repr['jane'] = ('james', 'john')
        new_v = Vote(creators = ['jane'])
        new_v.set_vote_data({'a': 1}, notify = False)
        poll['jane'] = new_v
        self.assertNotIn('james', poll)

    def test_delegators_get_votes(self):
        vote = _voting_fixture(self.config)
        self.config.testing_securitypolicy(userid = 'jane')
        poll = vote.__parent__
        unrestricted_wf_transition_to(poll, 'ongoing')
        self.config.registry.settings['voteit.liquid.type'] = 'simple'
        self.config.include('voteit.liquid.models')
        obj = self._cut(vote)
        root = obj.meeting.__parent__
        root.users['james'] = User()
        root.users['john'] = User()
        obj.meeting.add_groups('james', ['role:Voter'])
        obj.meeting.add_groups('john', ['role:Voter'])
        repr = IRepresentatives(obj.meeting)
        repr['jane'] = ('james', 'john')
        new_v = Vote(creators = ['jane'])
        new_v.set_vote_data({'a': 1}, notify = False)
        poll['jane'] = new_v
        self.assertIn('james', poll)
        self.assertIn('john', poll)
        self.assertEqual(poll['james'].get_vote_data(), {'a': 1})

    def test_call_adjusts_ownership_for_delegators_who_vote(self):
        vote = _voting_fixture(self.config)
        poll = vote.__parent__
        poll['jane'] = v2 = Vote(creators = ['someone'])
        self.config.include('voteit.liquid.models')
        obj = self._cut(v2)
        obj.adjust_owner('jane')
        self.assertIn('jane', v2.creators)
        self.assertNotIn('someone', v2.creators)


class RepresentativeFormTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.registry.settings['voteit.liquid.type'] = 'simple'
        self.config.include('voteit.liquid')

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from voteit.liquid.views import RepresentativeForm
        return RepresentativeForm

    def _fixture(self):
        root = bootstrap_and_fixture(self.config)
        self.config.testing_securitypolicy('jane', permissive = True)
        root['m'] = context = Meeting()
        return context

    def test_appstruct(self):
        context = self._fixture()
        request = testing.DummyRequest()
        obj = self._cut(context, request)
        self.assertEqual(obj.appstruct()['active'], False)
        repr = IRepresentatives(context)
        repr['jane'] = ()
        self.assertEqual(obj.appstruct()['active'], True)

    def test_become_representative(self):
        context = self._fixture()
        request = testing.DummyRequest(method = 'POST',
                                       params = {'active': 'true',
                                                 'save': 'Save'})
        obj = self._cut(context, request)
        obj.check_csrf = False
        response = obj()
        repr = IRepresentatives(context)
        self.assertIn('jane', repr)
        self.assertEqual(response.location, 'http://example.com/m/representation')

    def test_end_representative(self):
        context = self._fixture()
        repr = IRepresentatives(context)
        repr['jane'] = ()
        request = testing.DummyRequest(method = 'POST',
                                       params = {'active': 'false',
                                                 'save': 'Save'})
        obj = self._cut(context, request)
        obj.check_csrf = False
        response = obj()
        self.assertNotIn('jane', repr)
        self.assertEqual(response.location, 'http://example.com/m/representation')

    def test_already_set_has_no_effect(self):
        context = self._fixture()
        repr = IRepresentatives(context)
        repr['jane'] = ('one', 'two',)
        request = testing.DummyRequest(method = 'POST',
                                       params = {'active': 'true',
                                                 'save': 'Save'})
        obj = self._cut(context, request)
        obj.check_csrf = False
        response = obj()
        self.assertIn('jane', repr)
        self.assertEqual(repr['jane'] ,('one', 'two',))


class SelectRepresentativeFormTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from voteit.liquid.views import SelectRepresentativeForm
        return SelectRepresentativeForm

    def _fixture(self):
        self.config.registry.settings['voteit.liquid.type'] = 'simple'
        self.config.include('voteit.liquid')
        self.config.testing_securitypolicy('jane', permissive = True)
        root = bootstrap_and_fixture(self.config)
        root['m'] = Meeting()
        return root['m']

    def test_appstruct_with_repr(self):
        context = self._fixture()
        repr = IRepresentatives(context)
        repr['president'] = ()
        request = testing.DummyRequest(params = {'repr': 'president',})
        obj = self._cut(context, request)
        self.assertEqual(obj.appstruct()['repr'], 'president')

    def test_appstruct_active(self):
        context = self._fixture()
        repr = IRepresentatives(context)
        repr['president'] = ('jane',)
        request = testing.DummyRequest(params = {'repr': 'president',})
        obj = self._cut(context, request)
        self.assertEqual(obj.appstruct()['active'], True)

    def test_appstruct_bogus_user(self):
        context = self._fixture()
        request = testing.DummyRequest(params = {'repr': '404',})
        obj = self._cut(context, request)
        self.assertRaises(HTTPForbidden, obj.appstruct)

    def test_set_representative(self):
        context = self._fixture()
        repr = IRepresentatives(context)
        repr['zwork'] = ()
        request = testing.DummyRequest(method = 'POST',
                                       params = {'repr': 'zwork',
                                                 'active': 'true',
                                                 'save': 'Save'})
        obj = self._cut(context, request)
        obj.check_csrf = False
        response = obj()
        self.assertEqual(repr.represented_by('jane'), 'zwork')
        self.assertEqual(response.location, 'http://example.com/m/representation')

    def test_set_nonexistent_repr(self):
        context = self._fixture()
        request = testing.DummyRequest(method = 'POST',
                                       params = {'repr': '404',
                                                 'active': 'true',
                                                 'save': 'Save'})
        obj = self._cut(context, request)
        obj.check_csrf = False
        #This will cause the form to render once again...
        response = obj()
        self.assertIn('form', response)

    def test_repr_already_set(self):
        context = self._fixture()
        repr = IRepresentatives(context)
        repr['zwork'] = ('jane', 'jeff',)
        request = testing.DummyRequest(method = 'POST',
                                       params = {'repr': 'zwork',
                                                 'active': 'true',
                                                 'save': 'Save'})
        obj = self._cut(context, request)
        obj.check_csrf = False
        response = obj()
        self.assertEqual(repr.represented_by('jane'), 'zwork')
        self.assertEqual(repr['zwork'], ('jane', 'jeff',))
        self.assertEqual(response.location, 'http://example.com/m/representation')

    def test_unset_repr(self):
        context = self._fixture()
        repr = IRepresentatives(context)
        repr['zwork'] = ('jane', 'jeff',)
        request = testing.DummyRequest(method = 'POST',
                                       params = {'repr': 'zwork',
                                                 'active': 'false',
                                                 'save': 'Save'})
        obj = self._cut(context, request)
        obj.check_csrf = False
        response = obj()
        self.assertEqual(repr.represented_by('jane'), None)
        self.assertEqual(repr['zwork'], ('jeff',))
        self.assertEqual(response.location, 'http://example.com/m/representation')
