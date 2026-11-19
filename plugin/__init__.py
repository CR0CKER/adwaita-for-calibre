from calibre.customize import InterfaceActionBase


class AdwaitaForCalibre(InterfaceActionBase):

    name = 'Adwaita for calibre'
    description = ('Makes calibre look like a native GNOME app: libadwaita colours that follow the '
                   'system accent and light/dark setting, rounded controls, Adwaita menus, tabs '
                   'and scroll bars, and the GNOME interface font.')
    supported_platforms = ['linux']
    author = 'CR0CKER'
    version = (0, 1, 0)
    # Uses calibre 9 internals (bookshelf view, layout buttons, central container); tested on 9.18.
    minimum_calibre_version = (9, 0, 0)

    actual_plugin = 'calibre_plugins.adwaita_for_calibre.main:AdwaitaAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.adwaita_for_calibre.config import ConfigWidget
        return ConfigWidget(self)

    def save_settings(self, config_widget):
        config_widget.save_settings()
