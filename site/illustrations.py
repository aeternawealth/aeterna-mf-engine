"""Line illustrations drawn in the site's own colours (they follow light and dark themes), plus the page texture.

icon(name)   a 56px two-tone spot illustration for cards and steps
hero(name)   a wider decorative illustration for page headers (hidden on phones)
TEXTURE      a faint dot grid on the page background (shows between cards; cards stay solid)
All inline SVG, no image files. aria-hidden: they decorate, the text carries the meaning.
"""

_S = "fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'"
_A = "fill='var(--teal-soft)' stroke='none'"

ICONS = {
    "growth": f"<rect x='6' y='8' width='44' height='40' rx='8' {_A}/><path d='M12 40 L22 30 L29 35 L44 18' {_S}/><path d='M36 18 H44 V26' {_S}/><circle cx='22' cy='30' r='2.5' fill='currentColor'/><circle cx='29' cy='35' r='2.5' fill='currentColor'/>",
    "shield": f"<circle cx='28' cy='30' r='20' {_A}/><path d='M28 8 L44 14 V27 C44 38 37 45 28 48 C19 45 12 38 12 27 V14 Z' {_S}/><path d='M21 28 L26 33 L35 23' {_S}/>",
    "scale": f"<rect x='8' y='38' width='40' height='10' rx='5' {_A}/><path d='M28 10 V44 M18 44 H38 M14 18 H42' {_S}/><path d='M14 18 L8 30 H20 Z M42 18 L36 30 H48 Z' {_S}/><circle cx='28' cy='10' r='3' fill='currentColor'/>",
    "compass": f"<circle cx='28' cy='28' r='22' {_A}/><circle cx='28' cy='28' r='18' {_S}/><path d='M34 22 L30 30 L22 34 L26 26 Z' {_S}/><circle cx='28' cy='28' r='2' fill='currentColor'/>",
    "layers": f"<path d='M28 10 L48 20 L28 30 L8 20 Z' {_A}/><path d='M28 10 L48 20 L28 30 L8 20 Z' {_S}/><path d='M8 28 L28 38 L48 28 M8 36 L28 46 L48 36' {_S}/>",
    "lens": f"<circle cx='24' cy='24' r='16' {_A}/><circle cx='24' cy='24' r='13' {_S}/><path d='M34 34 L46 46' {_S}/><path d='M17 27 L22 22 L26 25 L31 19' {_S}/>",
    "calendar": f"<rect x='8' y='12' width='40' height='36' rx='6' {_A}/><rect x='8' y='12' width='40' height='36' rx='6' {_S}/><path d='M8 22 H48 M18 8 V16 M38 8 V16' {_S}/><circle cx='19' cy='31' r='2' fill='currentColor'/><circle cx='28' cy='31' r='2' fill='currentColor'/><circle cx='37' cy='31' r='2' fill='currentColor'/><circle cx='19' cy='40' r='2' fill='currentColor'/>",
    "coins": f"<ellipse cx='28' cy='40' rx='18' ry='7' {_A}/><ellipse cx='22' cy='18' rx='12' ry='5' {_S}/><path d='M10 18 V26 C10 29 15 31 22 31 C29 31 34 29 34 26 V18' {_S}/><ellipse cx='34' cy='32' rx='12' ry='5' {_S}/><path d='M22 32 V40 C22 43 27 45 34 45 C41 45 46 43 46 40 V32' {_S}/>",
    "bars": f"<rect x='6' y='8' width='44' height='40' rx='8' {_A}/><path d='M14 42 V30 M22 42 V22 M30 42 V26 M38 42 V14' {_S} stroke-width='5'/><path d='M10 44 H46' {_S}/>",
    "dots": f"<rect x='6' y='8' width='44' height='40' rx='8' {_A}/><path d='M10 44 H46 M10 12 V44' {_S}/><circle cx='18' cy='36' r='3' fill='var(--t-c)'/><circle cx='24' cy='30' r='3' fill='var(--t-b)'/><circle cx='31' cy='24' r='3' fill='var(--t-a)'/><circle cx='39' cy='17' r='3' fill='var(--t-ap)'/><circle cx='36' cy='33' r='3' fill='var(--t-b)'/>",
    "fall": f"<rect x='6' y='8' width='44' height='40' rx='8' {_A}/><path d='M10 16 L20 20 L26 38 L34 30 L46 24' {_S}/><path d='M26 38 V44' {_S} stroke-dasharray='2 3'/>",
    "tax": f"<rect x='12' y='6' width='32' height='44' rx='5' {_A}/><rect x='12' y='6' width='32' height='44' rx='5' {_S}/><path d='M19 16 H37 M19 24 H31' {_S}/><path d='M21 40 L35 30' {_S}/><circle cx='22' cy='31' r='2.5' {_S}/><circle cx='34' cy='39' r='2.5' {_S}/>",
    "people": f"<circle cx='28' cy='30' r='20' {_A}/><circle cx='21' cy='22' r='6' {_S}/><circle cx='36' cy='24' r='5' {_S}/><path d='M10 44 C11 35 16 31 21 31 C26 31 31 35 32 44 M33 33 C39 33 44 37 45 44' {_S}/>",
}


def icon(name, size=56, colour="var(--teal)"):
    body = ICONS.get(name) or ICONS["growth"]
    return (f"<svg class='ill-i' viewBox='0 0 56 56' width='{size}' height='{size}' aria-hidden='true' focusable='false' "
            f"style='color:{colour};display:block;flex:none'>{body}</svg>")


def hero(name="orbit"):
    """A wide decorative piece for a header's right column. Hidden below 900px."""
    if name == "dots":
        import random
        rnd = random.Random(7)
        dots = []
        for k in range(46):
            x = 30 + rnd.random() * 300
            y = 30 + rnd.random() * 130 - (x - 30) * 0.18
            t = "var(--t-ap)" if y < 55 else "var(--t-a)" if y < 85 else "var(--t-b)" if y < 115 else "var(--t-c)"
            dots.append(f"<circle cx='{x:.0f}' cy='{y + 40:.0f}' r='{3 + rnd.random() * 3:.1f}' fill='{t}' opacity='.75'/>")
        art = ("<rect x='4' y='4' width='352' height='212' rx='18' fill='var(--surface)' stroke='var(--rule)'/>"
               "<path d='M26 190 H336 M26 30 V190' stroke='var(--rule)' stroke-width='2'/><path d='M40 175 C120 150 220 110 330 50' fill='none' stroke='var(--ink-3)' stroke-dasharray='4 5'/>"
               + "".join(dots))
    elif name == "rings":
        art = ("<rect x='4' y='4' width='352' height='212' rx='18' fill='var(--surface)' stroke='var(--rule)'/>"
               "<circle cx='120' cy='110' r='70' fill='none' stroke='var(--rule)' stroke-width='14'/>"
               "<circle cx='120' cy='110' r='70' fill='none' stroke='var(--t-ap)' stroke-width='14' stroke-linecap='round' stroke-dasharray='300 440' transform='rotate(-90 120 110)'/>"
               "<circle cx='120' cy='110' r='46' fill='none' stroke='var(--rule)' stroke-width='10'/>"
               "<circle cx='120' cy='110' r='46' fill='none' stroke='var(--brass)' stroke-width='10' stroke-linecap='round' stroke-dasharray='150 290' transform='rotate(-90 120 110)'/>"
               "<rect x='222' y='60' width='110' height='12' rx='6' fill='var(--teal-soft)'/><rect x='222' y='60' width='86' height='12' rx='6' fill='var(--teal)'/>"
               "<rect x='222' y='92' width='110' height='12' rx='6' fill='var(--teal-soft)'/><rect x='222' y='92' width='64' height='12' rx='6' fill='var(--t-a)'/>"
               "<rect x='222' y='124' width='110' height='12' rx='6' fill='var(--teal-soft)'/><rect x='222' y='124' width='96' height='12' rx='6' fill='var(--brass)'/>"
               "<rect x='222' y='156' width='110' height='12' rx='6' fill='var(--teal-soft)'/><rect x='222' y='156' width='40' height='12' rx='6' fill='var(--t-b)'/>")
    else:   # "lines": growth lines over a grid
        art = ("<rect x='4' y='4' width='352' height='212' rx='18' fill='var(--surface)' stroke='var(--rule)'/>"
               + "".join(f"<path d='M24 {y} H336' stroke='var(--rule)'/>" for y in (50, 90, 130, 170))
               + "<path d='M24 175 L70 160 L110 165 L150 130 L190 138 L230 100 L270 108 L336 52 L336 190 L24 190 Z' fill='var(--teal)' opacity='.08'/>"
               "<path d='M24 175 L70 160 L110 165 L150 130 L190 138 L230 100 L270 108 L336 52' fill='none' stroke='var(--teal)' stroke-width='3' stroke-linejoin='round'/>"
               "<path d='M24 178 L70 170 L110 172 L150 150 L190 158 L230 135 L270 140 L336 110' fill='none' stroke='var(--brass)' stroke-width='2.2' stroke-linejoin='round'/>"
               "<circle cx='336' cy='52' r='5' fill='var(--teal)'/><circle cx='336' cy='110' r='4.5' fill='var(--brass)'/>")
    return f"<svg class='ill-h' viewBox='0 0 360 220' aria-hidden='true' focusable='false'>{art}</svg>"


TEXTURE = (":root{--tex:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='22' height='22'%3E%3Ccircle cx='11' cy='11' r='1.1' fill='%2314211e' fill-opacity='.09'/%3E%3C/svg%3E\")}:root[data-theme=\"dark\"]{--tex:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='22' height='22'%3E%3Ccircle cx='11' cy='11' r='1.1' fill='%23eaf3ef' fill-opacity='.09'/%3E%3C/svg%3E\")}"
           "body{background-image:var(--tex)}"
           ".ill-h{width:100%;max-width:340px;height:auto;display:block}@media (max-width:900px){.ill-h{display:none}}")
