"""Render the Adwaita symbolic icon theme for calibre.

Run through calibre's Python so Qt's SVG renderer matches what calibre uses:

    flatpak run --command=calibre-debug com.calibre_ebook.calibre -e scripts/build_icons.py -- OUT_DIR

Writes <name>-for-dark-theme.png and <name>-for-light-theme.png (128 px, like calibre's own) plus
metadata.json into OUT_DIR. Source SVGs come from the host's adwaita-icon-theme.
"""
import json
import os
import sys

# calibre-debug -e runs this file via exec, so __file__ is unreliable; argv[0] is the script.
HERE = sys.argv[0] if sys.argv[0].endswith('.py') else __file__
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(HERE)))
for p in (os.path.join(ROOT, 'icons'), os.path.join(ROOT, 'plugin')):
    sys.path.insert(0, p)

import adwaita  # noqa: E402  (colour maths only)
from mapping import MAPPING  # noqa: E402

SIZE = 128
# Glyphs that sit off-centre on their canvas and look misaligned next to a centred neighbour:
# Adwaita's magnifier fills only the top-left 120x120, the search-field cog fills all 128.
RECENTRE = {'fts.png', 'search.png'}
SOURCES = ('/run/host/usr/share/icons/Adwaita/symbolic', '/usr/share/icons/Adwaita/symbolic')
HICOLOR = ('/run/host/usr/share/icons/hicolor/symbolic', '/usr/share/icons/hicolor/symbolic')


def svg_path(src, icon):
    if icon.startswith('local:'):
        return os.path.join(ROOT, 'icons', 'extra', icon[len('local:'):] + '-symbolic.svg')
    if icon.startswith('hicolor:'):
        base = next(d for d in HICOLOR if os.path.isdir(d))
        return os.path.join(base, icon[len('hicolor:'):] + '-symbolic.svg')
    return os.path.join(src, icon + '-symbolic.svg')
COLORS = {
    'dark': '#ffffff',
    'light': adwaita.mix('#000006', '#ffffff', 0.8),  # libadwaita fg on a light surface
}
METADATA = {
    'name': 'adwaita',
    'title': 'Adwaita',
    'author': 'CR0CKER',
    'version': 1,
    'license': 'LGPL-3.0-only or CC-BY-SA-3.0 (GNOME adwaita-icon-theme)',
    'url': 'https://github.com/CR0CKER/adwaita-for-calibre',
    'description': "GNOME's Adwaita symbolic icons, recoloured for calibre's light and dark modes.",
    'color_palette': 'any',
}


def source_dir():
    for d in SOURCES:
        if os.path.isdir(d):
            return d
    raise SystemExit('adwaita-icon-theme not found (looked in %s)' % ', '.join(SOURCES))


def render(svg_text, color, out_path, recentre=False):
    """Like GTK's symbolic recolouring: every painted pixel takes `color`, alpha is kept, so
    unfilled paths (default black) and fill-opacity shading are recoloured too."""
    from qt.core import QBuffer, QByteArray, QColor, QImage, QImageReader, QIODevice, QPainter, QSize, Qt

    # calibre's bundle has the SVG image plugin but no QtSvg Python module.
    buf = QBuffer()
    buf.setData(QByteArray(svg_text.encode('utf-8')))
    buf.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buf, b'svg')
    reader.setScaledSize(QSize(SIZE, SIZE))
    src = reader.read()
    if src.isNull():
        raise ValueError(f'{out_path}: {reader.errorString()}')
    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.drawImage(0, 0, src)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    p.fillRect(img.rect(), QColor(color))
    p.end()
    if recentre:
        img = _recentre(img)
    if not img.save(out_path):
        raise OSError(out_path)


def _recentre(img):
    from qt.core import QImage, QPainter, QRect, Qt
    xs, ys = [], []
    for y in range(img.height()):
        for x in range(img.width()):
            if img.pixelColor(x, y).alpha() > 8:
                xs.append(x)
                ys.append(y)
    if not xs:
        return img
    box = QRect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
    out = QImage(img.size(), QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.drawImage((img.width() - box.width()) // 2, (img.height() - box.height()) // 2, img, *box.getRect())
    p.end()
    return out


def main(out):
    from calibre.gui2 import Application
    Application([])
    src = source_dir()
    os.makedirs(out, exist_ok=True)
    for name, icon in sorted(MAPPING.items()):
        with open(svg_path(src, icon), encoding='utf-8') as f:
            svg = f.read()
        base = name[:-4]
        os.makedirs(os.path.dirname(os.path.join(out, base)), exist_ok=True)
        for mode, color in COLORS.items():
            render(svg, color, os.path.join(out, f'{base}-for-{mode}-theme.png'), name in RECENTRE)
    with open(os.path.join(out, 'metadata.json'), 'w') as f:
        json.dump(METADATA, f, indent=2)
    print(len(MAPPING), 'icons ->', out)


if __name__ == '__main__':
    main(os.path.abspath(sys.argv[-1]))
