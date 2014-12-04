from pyramid.i18n import TranslationStringFactory


_ = TranslationStringFactory('voteit.liquid')


def includeme(config):
    config.include('.models')
    config.scan('.views')
    config.scan('.schemas')
