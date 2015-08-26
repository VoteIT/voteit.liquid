from arche.views.base import BaseForm
from arche.views.base import BaseView
from betahaus.viewcomponent.decorators import view_action
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from voteit.core import security
from voteit.core.models.interfaces import IMeeting
from voteit.core.models.interfaces import IVote

from voteit.liquid import _
from voteit.liquid.interfaces import ILiquidVoter
from voteit.liquid.interfaces import IRepresentatives


@view_action('meeting_menu', 'representation', title = _(u"Representation"))
def representation_menu_link(context, request, va, **kw):
    url = request.resource_url(request.meeting, 'representation')
    return """<li><a href="%s">%s</a></li>""" % (url, request.localizer.translate(va.title))


def _get_ld_adapter(request):
    ld_name = request.registry.settings.get('voteit.liquid.type', None)
    if not ld_name:
        return
    for reg in request.registry.registeredAdapters():
        if reg.provided == ILiquidVoter and reg.name == ld_name and IVote in reg.required:
            return reg.factory


@view_config(context = IMeeting,
             name = 'representation',
             permission = security.VIEW,
             renderer = 'voteit.liquid:templates/representation.pt')
class RepresentationView(BaseView):

    def __call__(self):
        response = {}
        response['open'] = self.context.get_workflow_state() != 'closed'
        response['repr'] = repr = IRepresentatives(self.context)
        response['ld_type'] = _get_ld_adapter(self.request)
        return response


@view_config(context = IMeeting,
             name = 'representative_form',
             permission = security.VIEW, #FIXME: Permission?
             renderer = 'arche:templates/form.pt')
class RepresentativeForm(BaseForm):
    type_name = 'Meeting'
    schema_name = 'representative_form'

    def __call__(self):
        if self.context.get_workflow_state() == 'closed':
            raise HTTPForbidden(_("Meeting already closed"))
        return super(RepresentativeForm, self).__call__()

    def appstruct(self):
        repr = IRepresentatives(self.context)
        return {'active': self.request.authenticated_userid in repr}

    def cancel_success(self, *args):
        return HTTPFound(location = self.request.resource_url(self.context, 'representation'))

    def save_success(self, appstruct):
        repr = IRepresentatives(self.context)
        userid = self.request.authenticated_userid
        is_repr = appstruct['active']
        is_current = userid in repr
        if is_repr != is_current:
            if is_repr:
                self.flash_messages.add(_("You're now a representative"))
                repr.release(userid)
                repr.enable_representative(userid)
            else:
                msg = _('no_longer_representative',
                        default = "You're no longer an available representative. "
                            "${votes} vote(s) were released back to their original owners.",
                            mapping = {'votes': len(repr[userid])})
                self.flash_messages.add(msg)
                repr.disable_representative(userid)
        return HTTPFound(location = self.request.resource_url(self.context, 'representation'))


@view_config(context = IMeeting,
             name = 'select_representative_form',
             permission = security.VIEW, #FIXME: Permission?
             renderer = 'arche:templates/form.pt')
class SelectRepresentativeForm(BaseForm):
    type_name = 'Meeting'
    schema_name = 'select_representative_form'

    def __call__(self):
        if self.context.get_workflow_state() == 'closed':
            raise HTTPForbidden(_("Meeting already closed"))
        return super(SelectRepresentativeForm, self).__call__()

    def appstruct(self):
        repr_userid = self.request.GET.get('repr', '')
        repr = IRepresentatives(self.context)
        if repr_userid not in repr:
            raise HTTPForbidden(_("That user isn't a representative"))
        return {'active': repr.represented_by(self.request.authenticated_userid) == repr_userid,
                'repr': repr_userid}

    def cancel_success(self, *args):
        return HTTPFound(location = self.request.resource_url(self.context, 'representation'))

    def save_success(self, appstruct):
        repr = IRepresentatives(self.context)
        userid = self.request.authenticated_userid
        active = appstruct['active']
        representative = appstruct['repr']
        is_current = repr.represented_by(userid) == representative
        if is_current and not active:
            #You've deselected this person
            repr.release(userid)
            msg = _("You're no longer represented by '${userid}'",
                    mapping = {'userid': representative})
            self.flash_messages.add(msg)
        if not is_current and active:
            #You've selected this person - validation handled by schema
            repr.represent(representative, userid)
            msg = _("You're now represented by '${userid}'",
                    mapping = {'userid': representative})
            self.flash_messages.add(msg)
        #All other means unchanged
        return HTTPFound(location = self.request.resource_url(self.context, 'representation'))


def includeme(config):
    config.scan()
