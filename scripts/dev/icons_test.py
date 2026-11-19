# calibre-debug -e: install the icon set into the dev profile headlessly via plugin/config.py.
import os
import sys

from calibre.gui2 import Application

app = Application([])
sys.path.insert(0, os.path.join(sys.argv[-2], 'plugin'))
# config.py imports Qt widgets only for the dialog; the functions need just calibre.
import config  # noqa: E402

action = sys.argv[-1]
print('before:', config.installed(), config.backups())
getattr(config, action)(*([sys.argv[-3]] if action == 'install' else []))
slot_dir = os.path.dirname(config.manager().user_theme_resource_file('any'))
print('after:', config.installed(), config.backups(), os.listdir(slot_dir))
