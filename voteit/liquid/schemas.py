from __future__ import unicode_literals

import colander
import deform

from voteit.liquid import _
from voteit.liquid.interfaces import IRepresentatives


@colander.deferred
def existing_representative_validator(node, kw):
    context = kw['context']
    return ExistingRepresentativeValidator(context)


class ExistingRepresentativeValidator(object):

    def __init__(self, context):
        self.context = context

    def __call__(self, node, value):
        repr = IRepresentatives(self.context)
        if value not in repr:
            raise colander.Invalid(node, _("Not an existing representative"))


class SelectRepresentativeSchema(colander.Schema):
    repr = colander.SchemaNode(colander.String(),
                               widget = deform.widget.HiddenWidget(),
                               validator = existing_representative_validator)
    active = colander.SchemaNode(colander.Bool(),
                                 title = _("Select this representative?"),
                                 description = _("If you tick the box below, this person will represent you. If you wish, you may still vote yourself even if you're represented."),
                                 default = False,
                                 missing = False)


class RepresentativeSchema(colander.Schema):
    active = colander.SchemaNode(colander.Bool(),
                                 title = _("Do you wish to be a representative?"),
                                 description = _("If the box below is ticked, you'll be able to receive votes from others. "
                                                 "If you untick it, you'll give back any votes that have been delegated to you. "
                                                 "NOTE: If you become a representative, anyone delegating their vote to you will see how you've voted."),
                                 default = False,
                                 missing = False)


def includeme(config):
    config.add_content_schema('Meeting', SelectRepresentativeSchema, 'select_representative_form')
    config.add_content_schema('Meeting', RepresentativeSchema, 'representative_form')
    