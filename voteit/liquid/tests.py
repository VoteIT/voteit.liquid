from unittest import TestCase

from pyramid import testing
from pyramid.httpexceptions import HTTPForbidden
from voteit.core.models.meeting import Meeting
from voteit.core.testing_helpers import bootstrap_and_fixture
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

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

    def test_represent(self):
        obj = self._cut(Meeting())
        obj['one'] = ()
        obj.represent('one', 'two')
        self.assertIn('two', obj['one'])

    def test_represent_not_a_representative(self):
        obj = self._cut(Meeting())
        self.assertRaises(AssertionError, obj.represent, 'one', 'two')

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
        self.config.include('voteit.liquid')
        m = Meeting()
        self.failUnless(IRepresentatives(m, None))


class RepresentativeFormTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()
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
