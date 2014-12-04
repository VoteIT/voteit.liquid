from betahaus.pyracont.factories import createSchema
from betahaus.viewcomponent.decorators import view_action
from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from pyramid.view import view_config
from voteit.core import security
from voteit.core.models.interfaces import IMeeting
from voteit.core.views.base_edit import BaseForm
from voteit.core.views.base_view import BaseView

from voteit.liquid import _
from voteit.liquid.interfaces import IRepresentatives


@view_action('meeting', 'representation', title = _(u"Representation"))
def representation_menu_link(context, request, va, **kw):
    api = kw['api']
    url = request.resource_url(api.meeting, 'representation')
    return """<li><a href="%s">%s</a></li>""" % (url, api.translate(va.title))


class RepresentationView(BaseView):

    @view_config(context = IMeeting,
                 name = 'representation',
                 permission = security.VIEW,
                 renderer = 'voteit.liquid:templates/representation.pt')
    def overview(self):
        self.response['repr'] = repr = IRepresentatives(self.context)
        return self.response


@view_config(context = IMeeting,
             name = 'representative_form',
             permission = security.VIEW, #FIXME: Permission?
             renderer = 'voteit.core:views/templates/base_edit.pt')
class RepresentativeForm(BaseForm):

    def get_schema(self):
        return createSchema('RepresentativeSchema')

    def appstruct(self):
        repr = IRepresentatives(self.context)
        return {'active': self.api.userid in repr}

    def save_success(self, appstruct):
        repr = IRepresentatives(self.context)
        userid = self.api.userid
        is_repr = appstruct['active']
        is_current = userid in repr
        if is_repr != is_current:
            if is_repr:
                self.api.flash_messages.add(_("You're now a representative"))
                repr.release(userid)
                repr[userid] = ()
            else:
                msg = _('no_longer_representative',
                        default = "You're no longer an available representative. "
                            "${votes} vote(s) were released back to their original owners.",
                            mapping = {'votes': len(repr[userid])})
                self.api.flash_messages.add(msg)
                del repr[userid]
        return HTTPFound(location = self.request.resource_url(self.context, 'representation'))


@view_config(context = IMeeting,
             name = 'select_representative_form',
             permission = security.VIEW, #FIXME: Permission?
             renderer = 'voteit.core:views/templates/base_edit.pt')
class SelectRepresentativeForm(BaseForm):

    def get_schema(self):
        return createSchema('SelectRepresentativeSchema')

    def appstruct(self):
        repr_userid = self.request.GET.get('repr', '')
        repr = IRepresentatives(self.context)
        if repr_userid not in repr:
            raise HTTPForbidden(_("That user isn't a representative"))
        return {'active': repr.represented_by(self.api.userid) == repr_userid,
                'repr': repr_userid}

    def save_success(self, appstruct):
        repr = IRepresentatives(self.context)
        userid = self.api.userid
        active = appstruct['active']
        representative = appstruct['repr']
        is_current = repr.represented_by(userid) == representative

        if is_current and not active:
            #You've deselected this person
            repr.release(userid)
            msg = _("You're no longer represented by '${userid}'",
                    mapping = {'userid': representative})
            self.api.flash_messages.add(msg)
        if not is_current and active:
            #You've selected this person - validation handled by schema
            repr.represent(representative, userid)
            msg = _("You're now represented by '${userid}'",
                    mapping = {'userid': representative})
            self.api.flash_messages.add(msg)
        #All other means unchanged
        return HTTPFound(location = self.request.resource_url(self.context, 'representation'))
