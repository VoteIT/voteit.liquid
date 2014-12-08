from logging import getLogger

from pyramid.i18n import TranslationStringFactory


_ = TranslationStringFactory('voteit.liquid')


def includeme(config):
    logger = getLogger(__name__)
    ld_type = config.registry.settings.get('voteit.liquid.type', None)
    if ld_type:
        logger.info("voteit.liquid model set to '%s'" % ld_type)
        config.include('.models')
        config.scan('.views')
        config.scan('.schemas')
    else:
        logger.warn("'voteit.liquid.type' must be set if you want to include this plugin.")
