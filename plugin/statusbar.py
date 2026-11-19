"""Status bar text: only what GNOME apps show (the item count and selection), not calibre's
"calibre 9.18 created by Kovid Goyal" banner. A connected device stays visible.

Mirrors calibre's StatusBar._set_label (calibre/gui2/init.py), minus the banner.
"""


def _label(self):
    from calibre.utils.localization import _, ngettext

    if self.total != self.current:
        base = _('%(num)d of %(total)d books') % dict(num=self.current, total=self.total)
    else:
        base = ngettext('one book', '{} books', self.total).format(self.total)
    if self.selected > 0:
        base = ngettext('%(num)s, %(sel)d selected', '%(num)s, %(sel)d selected', self.selected) % dict(
            num=base, sel=self.selected)
    if self.library_total != self.total:
        base = _('{0}, {1} total').format(base, self.library_total)
    if self.device_string:
        base = f'{self.device_string} \u00b7 {base}'
    self.defmsg.setText(base)
    self.clearMessage()


def install(gui):
    from calibre.gui2.init import StatusBar
    if not getattr(StatusBar, '_adwaita_patched', False):
        StatusBar._set_label = _label
        StatusBar._adwaita_patched = True
    sb = gui.statusBar()
    if isinstance(sb, StatusBar):
        sb.set_label()
