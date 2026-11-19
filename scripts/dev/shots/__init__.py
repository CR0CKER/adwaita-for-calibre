from calibre.customize import InterfaceActionBase


class AdwaitaDevShots(InterfaceActionBase):
    # Development only: never shipped. Screenshots calibre's main windows when
    # ADWAITA_SHOT_DIR is set, then quits.
    name = 'Adwaita Dev Shots'
    description = 'Development helper for Adwaita for calibre.'
    supported_platforms = ['linux']
    author = 'CR0CKER'
    version = (0, 0, 1)
    minimum_calibre_version = (7, 0, 0)
    actual_plugin = 'calibre_plugins.adwaita_dev_shots.main:Shots'
