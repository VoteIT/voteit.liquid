from __future__ import unicode_literals

from betahaus.pyracont.decorators import schema_factory
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


@schema_factory()
class SelectRepresentativeSchema(colander.Schema):
    repr = colander.SchemaNode(colander.String(),
                               widget = deform.widget.HiddenWidget(),
                               validator = existing_representative_validator)
    active = colander.SchemaNode(colander.Bool(),
                                 title = _("Active"),
                                 default = False,
                                 missing = False)


@schema_factory()
class RepresentativeSchema(colander.Schema):
    active = colander.SchemaNode(colander.Bool(),
                                 title = _("Active representative?"),
                                 default = False,
                                 missing = False)
