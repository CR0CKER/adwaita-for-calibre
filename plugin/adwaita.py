"""Adwaita colour tokens and stylesheet rendering.

Pure Python, no Qt: everything here is unit-tested outside calibre. Values come from
libadwaita 1.8 (GNOME 49), extracted with

    gresource extract /usr/lib64/libadwaita-1.so.0 /org/gnome/Adwaita/styles/default.css
"""

import re

# libadwaita's nine accent colours (`--accent-<name>` in default.css). Used as a fallback when the
# Settings portal cannot be read, and to name the portal's RGB value in logs.
ACCENTS = {
    'blue': '#3584e4',
    'teal': '#2190a4',
    'green': '#3a944a',
    'yellow': '#c88800',
    'orange': '#ed5b00',
    'red': '#e62d42',
    'pink': '#d56199',
    'purple': '#9141ac',
    'slate': '#6f8396',
}
DEFAULT_ACCENT = ACCENTS['blue']  # libadwaita's own default

# Surfaces: (dark, light). Solid colours only; overlays are derived below.
SURFACES = {
    'window_bg': ('#222226', '#fafafb'),
    'view_bg': ('#1d1d20', '#ffffff'),
    'headerbar_bg': ('#2e2e32', '#ffffff'),
    'sidebar_bg': ('#2e2e32', '#ebebed'),
    'secondary_sidebar_bg': ('#28282c', '#f3f3f5'),
    'dialog_bg': ('#36363a', '#fafafb'),
    'popover_bg': ('#36363a', '#ffffff'),
    'thumbnail_bg': ('#39393d', '#ffffff'),
}
# Foreground: white in dark mode, rgb(0 0 6 / 80%) in light mode.
FG = {True: ('#ffffff', 1.0), False: ('#000006', 0.8)}
SHADE = {True: ('#000006', 0.25), False: ('#000006', 0.07)}
DESTRUCTIVE = {True: '#c01c28', False: '#e01b24'}  # red_4 / red_3
WARNING = {True: '#cd9309', False: '#e5a50a'}
SUCCESS = {True: '#26a269', False: '#2ec27e'}


def parse_hex(c):
    c = c.lstrip('#')
    if len(c) != 6:
        raise ValueError(f'expected #rrggbb, got #{c}')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(rgb):
    return '#' + ''.join(f'{max(0, min(255, round(v))):02x}' for v in rgb)


def mix(fg, bg, alpha):
    """Composite `fg` at `alpha` over the solid colour `bg`; returns #rrggbb."""
    f, b = parse_hex(fg), parse_hex(bg)
    return to_hex(tuple(fv * alpha + bv * (1 - alpha) for fv, bv in zip(f, b, strict=True)))


def rgba(c, alpha):
    """A QSS rgba() string. Qt reads the alpha channel as 0-255."""
    r, g, b = parse_hex(c)
    return f'rgba({r}, {g}, {b}, {round(alpha * 255)})'


# --- OKLab, for libadwaita's standalone accent: oklab(from accent max(l, .85) a b) in dark,
# min(l, .5) in light. Reference: https://bottosson.github.io/posts/oklab/

def _lin(v):
    v /= 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _unlin(v):
    v = v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
    return v * 255


def to_oklab(c):
    r, g, b = (_lin(v) for v in parse_hex(c))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def from_oklab(lab):
    L, a, b = lab
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )
    return to_hex(_unlin(max(0.0, min(1.0, v))) for v in rgb)


def standalone_accent(accent_bg, dark):
    L, a, b = to_oklab(accent_bg)
    L = max(L, 0.85) if dark else min(L, 0.5)
    return from_oklab((L, a, b))


def accent_from_portal(rgb_floats):
    """The Settings portal reports accent-color as three floats in [0, 1]; values outside that
    range mean "unset"."""
    try:
        vals = [float(v) for v in rgb_floats]
    except (TypeError, ValueError):
        return None
    if len(vals) != 3 or any(not 0 <= v <= 1 for v in vals):
        return None
    return to_hex(v * 255 for v in vals)


def tokens(dark, accent=DEFAULT_ACCENT):
    """Every colour the palette and stylesheet use, as strings."""
    i = 0 if dark else 1
    t = {k: v[i] for k, v in SURFACES.items()}
    fg, fg_a = FG[dark]
    shade, shade_a = SHADE[dark]
    win = t['window_bg']

    # Solid foregrounds (QPalette prefers opaque colours).
    t['fg'] = mix(fg, win, fg_a)
    t['fg_dim'] = mix(fg, win, fg_a * 0.55)
    t['fg_disabled'] = mix(fg, win, fg_a * 0.5)
    t['view_fg'] = mix(fg, t['view_bg'], fg_a)

    # Translucent overlays for QSS (rgba); they composite over whatever surface is underneath.
    def over(alpha):
        return rgba(fg, fg_a * alpha)

    t['border'] = over(0.15)
    t['hover'] = over(0.07)
    t['active'] = over(0.16)
    t['button_bg'] = over(0.10)
    t['button_hover'] = over(0.15)
    t['button_active'] = over(0.30)
    t['trough'] = over(0.15)
    t['separator'] = over(0.30)  # split-button divider in header bars
    t['popover_outline'] = rgba('#000000', 0.14)
    # AdwToggleGroup: --active-toggle-bg-color
    t['active_toggle'] = rgba('#ffffff', 0.20) if dark else '#ffffff'
    t['slider'] = over(0.20)
    t['slider_hover'] = over(0.40)
    t['slider_active'] = over(0.60)
    t['shade'] = rgba(shade, shade_a)
    t['card_bg'] = rgba('#ffffff', 0.08) if dark else '#ffffff'

    # Solid button fill over the window, for QPalette.Button.
    t['button_solid'] = mix(fg, win, fg_a * 0.10)
    t['alternate_base'] = mix(fg, t['view_bg'], fg_a * 0.03)

    t['accent_bg'] = accent
    t['accent_fg'] = '#ffffff'
    t['accent'] = standalone_accent(accent, dark)
    t['accent_hover'] = mix('#ffffff', accent, 0.10) if dark else mix('#000006', accent, 0.10)
    # libadwaita: outline 2px accent @ 50%. QSS has no outline, only a border, and a translucent
    # border shows the field's translucent background through it as a second band. Use the
    # solid equivalent over the window colour.
    t['focus_ring'] = mix(accent, win, 0.5)
    t['selection_bg'] = mix(accent, t['view_bg'], 0.30)
    t['selection_text'] = rgba(accent, 0.30)
    t['tooltip_bg'] = '#000000'  # libadwaita: rgb(0 0 0 / 80%) osd, both modes
    t['tooltip_fg'] = '#ffffff'

    t['destructive_bg'] = DESTRUCTIVE[dark]
    t['warning_bg'] = WARNING[dark]
    t['success_bg'] = SUCCESS[dark]
    return t


_TOKEN = re.compile(r'@([a-z_]+)@')


def render(template, values):
    """Replace @name@ placeholders. QSS is full of braces, so str.format is not usable."""
    missing = set()

    def sub(m):
        k = m.group(1)
        if k not in values:
            missing.add(k)
            return m.group(0)
        return str(values[k])

    out = _TOKEN.sub(sub, template)
    if missing:
        raise KeyError(f'unknown stylesheet tokens: {", ".join(sorted(missing))}')
    return out


def recolor_svg(svg, color):
    """Symbolic icons ship with one placeholder fill (#222222 / #2e3436 / #2e3434)."""
    return re.sub(r'fill="#(?:222222|2e3436|2e3434|000000|474747|241f31)"', f'fill="{color}"', svg)


def parse_font(spec):
    """'Adwaita Sans 11' -> ('Adwaita Sans', 11.0). GSettings font strings put the size last."""
    parts = (spec or '').strip().rsplit(' ', 1)
    if len(parts) != 2:
        return None
    try:
        size = float(parts[1])
    except ValueError:
        return None
    family = parts[0]
    # Drop Pango style words GNOME may append ("Adwaita Sans Bold 11").
    for word in (' Bold', ' Italic', ' Regular', ' Medium', ' Light'):
        if family.endswith(word):
            family = family[: -len(word)]
    return (family, size) if family and size > 0 else None
