"""Preferences -> Plugins -> Adwaita for calibre -> Customize: install or remove the icon set.

calibre loads user icon themes from <config>/icons-{any,dark,light}.rcc. The Adwaita set goes
into the "any" slot (it carries its own -for-dark-theme / -for-light-theme variants). Whatever
was there before, including dark/light-only themes that would shadow it, is renamed to
*.pre-adwaita and put back by "Restore previous icons".
"""

import os
import shutil
import tempfile
import zipfile

from qt.core import QCheckBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

THEME_NAME = 'adwaita'
SLOTS = ('any', 'dark', 'light')
BACKUP = '.pre-adwaita'


def manager():
    from calibre.gui2 import icon_resource_manager
    return icon_resource_manager


def installed():
    return manager().user_icon_theme_metadata('any').get('name') == THEME_NAME


def backups():
    m = manager()
    return [s for s in SLOTS if os.path.exists(m.user_theme_resource_file(s) + BACKUP)]


def install(plugin_zip):
    from calibre.utils.rcc import compile_icon_dir_as_themes

    m = manager()
    if not installed():
        for slot in SLOTS:
            path = m.user_theme_resource_file(slot)
            if os.path.exists(path):
                shutil.copy2(path, path + BACKUP)
                m.remove_user_theme(slot)
    else:
        m.remove_user_theme('any')
    with tempfile.TemporaryDirectory() as tdir, zipfile.ZipFile(plugin_zip) as zf:
        for name in zf.namelist():
            if name.startswith('icons/') and not name.endswith('/'):
                # Keep subfolders (mimetypes/, devices/, plugins/): calibre names those icons
                # by relative path.
                rel = name[len('icons/'):]
                if '..' in rel.split('/'):
                    continue
                dest = os.path.join(tdir, *rel.split('/'))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with zf.open(name) as src, open(dest, 'wb') as out:
                    shutil.copyfileobj(src, out)
        compile_icon_dir_as_themes(
            tdir, m.user_theme_resource_file('any'),
            theme_name='calibre-user-any', inherits='calibre-default', for_theme='any')
    refresh()


def restore():
    m = manager()
    if installed():
        m.remove_user_theme('any')
    for slot in SLOTS:
        path = m.user_theme_resource_file(slot)
        if os.path.exists(path + BACKUP):
            os.replace(path + BACKUP, path)
    refresh()


def refresh():
    m = manager()
    m.user_icon_theme_metadata.cache_clear()
    m.register_user_resource_files()
    m.set_theme()


class ConfigWidget(QWidget):
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        layout = QVBoxLayout(self)
        intro = QLabel(
            'Colours, controls and the font follow GNOME automatically.<p>'
            'The <b>icon set</b> is optional: it replaces calibre\'s toolbar and menu icons with '
            'GNOME\'s Adwaita symbolic icons. Your current icon theme is kept and can be restored. '
            'Restart calibre after changing icons.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.status = QLabel()
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.install_button = QPushButton('Use Adwaita icons')
        self.install_button.clicked.connect(self.do_install)
        self.restore_button = QPushButton('Restore previous icons')
        self.restore_button.clicked.connect(self.do_restore)
        row.addWidget(self.install_button)
        row.addWidget(self.restore_button)
        row.addStretch()
        layout.addLayout(row)

        from calibre_plugins.adwaita_for_calibre.main import prefs
        self.prefs = prefs()
        self.integrated = QCheckBox('Integrated title bar (experimental, X11/XWayland only)')
        self.integrated.setToolTip(
            'Hide the separate title bar and use the header bar instead, with its own window '
            'buttons, rounded corners and shadow. Needs calibre running on X11 or XWayland. '
            'Takes effect after a restart.')
        self.integrated.setChecked(self.prefs['integrated_titlebar'])
        layout.addWidget(self.integrated)
        self.viewer = QCheckBox('Apply to the e-book viewer')
        self.viewer.setToolTip(
            'Adwaita colours for the viewer window, and its "System" reading colour scheme '
            '(page background, text and links), following light/dark and the accent. '
            'Takes effect after a restart.')
        self.viewer.setChecked(self.prefs['theme_viewer'])
        layout.addWidget(self.viewer)
        layout.addStretch()
        self.update_state()

    def update_state(self):
        on = installed()
        prev = backups()
        if on:
            text = 'Adwaita icons are installed.'
        else:
            text = 'Current icons: ' + manager().user_theme_title
        self.status.setText(text)
        self.install_button.setText('Reinstall Adwaita icons' if on else 'Use Adwaita icons')
        self.restore_button.setEnabled(on or bool(prev))
        self.restore_button.setText('Restore previous icons' if prev else 'Use calibre\'s default icons')

    def run(self, fn, *args):
        from calibre.gui2 import error_dialog, info_dialog
        try:
            fn(*args)
        except Exception as e:  # noqa: BLE001 -- shown to the user in an error dialog
            import traceback
            error_dialog(self, 'Adwaita for calibre', str(e), det_msg=traceback.format_exc(), show=True)
        else:
            info_dialog(self, 'Adwaita for calibre', 'Done. Restart calibre to see every icon change.',
                        show=True, show_copy_button=False)
        self.update_state()

    def do_install(self):
        self.run(install, self.plugin.plugin_path)

    def do_restore(self):
        self.run(restore)

    def save_settings(self):
        self.prefs['integrated_titlebar'] = self.integrated.isChecked()
        self.prefs['theme_viewer'] = self.viewer.isChecked()
