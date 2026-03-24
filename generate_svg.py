"""
LaserGrave Événements — Moteur de génération SVG v3.0
Niche : Mariages / EVJF / Baptêmes / EVG
Convention laser : rouge (#FF0000) = découpe, noir (#000000) = gravure
Machine cible   : Longer Ray 5 40W — Zone utile max 400×400 mm
Matériaux       : bois, métal, cuir (pas de verre)
"""

import math
import os
import re
from dataclasses import dataclass

# ── Catalogue produits ────────────────────────────────────────────────────────
# Dimensions en millimètres

PRODUCTS: dict = {
    "cadre_15x10": {
        "label":    "Cadre photo Souvenir — 15×10 cm",
        "width":    150, "height": 100,
        "margin":   14, "shape": "rect", "corner_r": 3,
        "material": "bois", "prix": 18,
        "max_lines": 3,
    },
    "cadre_20x15": {
        "label":    "Cadre photo Souvenir — 20×15 cm",
        "width":    200, "height": 150,
        "margin":   16, "shape": "rect", "corner_r": 4,
        "material": "bois", "prix": 27,
        "max_lines": 3,
    },
    "plaque_bois": {
        "label":    "Plaque Témoin / D.H. — Bois",
        "width":    150, "height": 100,
        "margin":   12, "shape": "rect", "corner_r": 5,
        "material": "bois", "prix": 22,
        "max_lines": 3,
    },
    "plaque_metal": {
        "label":    "Plaque Témoin / D.H. — Métal brossé",
        "width":    150, "height": 100,
        "margin":   12, "shape": "rect", "corner_r": 3,
        "material": "metal", "prix": 28,
        "max_lines": 3,
    },
    "coffret_evjf": {
        "label":    "Coffret EVJF/EVG — Couvercle bois",
        "width":    200, "height": 150,
        "margin":   18, "shape": "rect", "corner_r": 6,
        "material": "bois", "prix": 42,
        "max_lines": 3,
    },
}

# ── Polices disponibles ───────────────────────────────────────────────────────

FONTS: dict = {
    "script":    "'Dancing Script', 'Brush Script MT', cursive",
    "classique": "Georgia, 'Times New Roman', serif",
    "moderne":   "'Helvetica Neue', Arial, sans-serif",
    "gravure":   "'Courier New', Courier, monospace",
    "arrondi":   "'Trebuchet MS', 'Lucida Grande', sans-serif",
}

# ── Motifs disponibles ────────────────────────────────────────────────────────

MOTIFS: dict = {
    "sans":         "Sans motif",
    "alliances":    "Alliances (mariage)",
    "couronne":     "Couronne florale (EVJF)",
    "coeur":        "Cœur",
    "etoiles":      "Étoiles aux coins",
    "fleurs_coins": "Fleurs aux coins",
    "branches":     "Branches latérales",
    "palmier":      "Palmier (EVG)",
    "diamant":      "Diamant / Bague",
}

# ── Événements → préférences par défaut ──────────────────────────────────────

EVENT_DEFAULTS: dict = {
    "mariage": {"motif": "alliances",    "font": "script"},
    "bapteme": {"motif": "etoiles",      "font": "classique"},
    "evjf":    {"motif": "couronne",     "font": "script"},
    "evg":     {"motif": "palmier",      "font": "moderne"},
}

# ── Presets LightBurn (pour README / documentation) ──────────────────────────

LIGHTBURN_PRESETS: dict = {
    "bois_gravure":  {"puissance": "70%", "vitesse": 3000, "passes": 1},
    "metal_gravure": {"puissance": "85%", "vitesse": 1500, "passes": 2},
    "cuir_gravure":  {"puissance": "55%", "vitesse": 4000, "passes": 1},
    "decoupe_bois":  {"puissance": "100%","vitesse": 800,  "passes": 3},
}

# ── Modèle de commande ────────────────────────────────────────────────────────

@dataclass
class OrderConfig:
    product_id:        str
    line1:             str
    line2:             str  = ""
    line3:             str  = ""
    font_id:           str  = "script"
    motif_id:          str  = "sans"
    decorative_border: bool = True
    event_type:        str  = "mariage"
    output_dir:        str  = "./output"


# ── Utilitaires ───────────────────────────────────────────────────────────────

def px(mm: float) -> float:
    """Convertit mm → pixels SVG (96 dpi, 1 mm ≈ 3.7795 px)"""
    return round(mm * 3.7795, 2)


def _escape_xml(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))


def _safe_filename(text: str, max_len: int = 24) -> str:
    safe = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    safe = re.sub(r"\s+", "_", safe.strip())
    return safe[:max_len]


# ── Rendus de motifs ──────────────────────────────────────────────────────────
# Toutes les coordonnées sont en pixels SVG (déjà converties via px())

def _motif_alliances(W, H, M, cx, cy):
    """Deux alliances entrelacées — centré en bas"""
    r   = min(W, H) * 0.07
    d   = r * 0.65
    y   = H - M * 0.62
    x1  = cx - d
    x2  = cx + d
    sw  = max(0.5, r * 0.07)
    return (
        f'  <circle cx="{x1:.1f}" cy="{y:.1f}" r="{r:.1f}" '
        f'fill="none" stroke="#000000" stroke-width="{sw:.2f}"/>\n'
        f'  <circle cx="{x2:.1f}" cy="{y:.1f}" r="{r:.1f}" '
        f'fill="none" stroke="#000000" stroke-width="{sw:.2f}"/>'
    )


def _motif_couronne(W, H, M, cx, cy):
    """Arc de petites fleurs en haut"""
    parts     = []
    n_flowers = 7
    arc_w     = W * 0.54
    base_y    = M * 0.72
    for i in range(n_flowers):
        t  = i / (n_flowers - 1)
        fx = cx - arc_w / 2 + arc_w * t
        fy = base_y - 3.5 * math.sin(t * math.pi)  # dips at center
        # 5 pétales
        fr = 2.2
        for j in range(5):
            a   = j * 2 * math.pi / 5 - math.pi / 2
            ppx = fx + fr * math.cos(a)
            ppy = fy + fr * math.sin(a)
            parts.append(
                f'  <circle cx="{ppx:.1f}" cy="{ppy:.1f}" r="1.0" '
                f'fill="none" stroke="#000000" stroke-width="0.35"/>'
            )
        # pistil
        parts.append(
            f'  <circle cx="{fx:.1f}" cy="{fy:.1f}" r="0.7" '
            f'fill="#000000" stroke="none"/>'
        )
        # petite tige vers le bas pour fleurs latérales
        if i in (0, 1, 5, 6):
            stem_len = 4
            parts.append(
                f'  <line x1="{fx:.1f}" y1="{fy:.1f}" '
                f'x2="{fx:.1f}" y2="{fy + stem_len:.1f}" '
                f'stroke="#000000" stroke-width="0.3"/>'
            )
    return "\n".join(parts)


def _motif_coeur(W, H, M, cx, cy):
    """Cœur paramétrique centré en bas"""
    s    = min(W, H) * 0.065
    hx   = cx
    hy   = H - M * 0.6
    n    = 48
    pts  = []
    for i in range(n + 1):
        t    = -math.pi + 2 * math.pi * i / n
        rx   = 16 * math.sin(t) ** 3
        ry   = -(13 * math.cos(t) - 5 * math.cos(2*t)
                 - 2 * math.cos(3*t) - math.cos(4*t))
        pts.append((hx + rx * s / 16, hy + ry * s / 16))
    d = "M " + " L ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts) + " Z"
    return f'  <path d="{d}" fill="none" stroke="#000000" stroke-width="0.5"/>'


def _motif_etoiles(W, H, M, cx, cy):
    """Étoile à 5 branches aux 4 coins"""
    parts = []
    pad   = M * 1.05
    pos   = [(pad, pad), (W - pad, pad), (pad, H - pad), (W - pad, H - pad)]
    ro    = min(W, H) * 0.030
    ri    = ro * 0.42
    for (sx, sy) in pos:
        verts = []
        for i in range(10):
            a = i * math.pi / 5 - math.pi / 2
            r = ro if i % 2 == 0 else ri
            verts.append((sx + r * math.cos(a), sy + r * math.sin(a)))
        d = "M " + " L ".join(f"{v[0]:.1f},{v[1]:.1f}" for v in verts) + " Z"
        parts.append(f'  <path d="{d}" fill="none" stroke="#000000" stroke-width="0.4"/>')
    return "\n".join(parts)


def _motif_fleurs_coins(W, H, M, cx, cy):
    """Fleurs à 6 pétales aux 4 coins"""
    parts  = []
    offset = M * 0.88
    pos    = [(offset, offset), (W - offset, offset),
              (offset, H - offset), (W - offset, H - offset)]
    fr     = min(W, H) * 0.030
    for (fx, fy) in pos:
        for j in range(6):
            a   = j * math.pi / 3
            ppx = fx + fr * math.cos(a)
            ppy = fy + fr * math.sin(a)
            parts.append(
                f'  <ellipse cx="{ppx:.1f}" cy="{ppy:.1f}" '
                f'rx="{fr*0.42:.1f}" ry="{fr*0.28:.1f}" '
                f'transform="rotate({math.degrees(a):.0f} {ppx:.1f} {ppy:.1f})" '
                f'fill="none" stroke="#000000" stroke-width="0.35"/>'
            )
        parts.append(
            f'  <circle cx="{fx:.1f}" cy="{fy:.1f}" r="{fr*0.22:.1f}" '
            f'fill="#000000" stroke="none"/>'
        )
    return "\n".join(parts)


def _motif_branches(W, H, M, cx, cy):
    """Branches végétales sur les côtés gauche et droit"""
    parts   = []
    n_twigs = 5
    for side in [-1, 1]:
        base_x  = cx + side * (W * 0.42 - M * 0.2)
        base_y1 = cy - H * 0.22
        base_y2 = cy + H * 0.22
        # Tige principale
        parts.append(
            f'  <line x1="{base_x:.1f}" y1="{base_y1:.1f}" '
            f'x2="{base_x:.1f}" y2="{base_y2:.1f}" '
            f'stroke="#000000" stroke-width="0.55"/>'
        )
        # Rameaux latéraux
        for i in range(n_twigs):
            t      = i / (n_twigs - 1)
            ty     = base_y1 + (base_y2 - base_y1) * t
            twig_l = min(W, H) * (0.045 + 0.02 * math.sin(t * math.pi))
            # angle en S
            twig_a = math.radians(30 + 20 * math.sin(t * math.pi)) * (-side)
            tx2    = base_x + twig_l * math.cos(twig_a)
            ty2    = ty     + twig_l * math.sin(twig_a) * (-1)
            parts.append(
                f'  <line x1="{base_x:.1f}" y1="{ty:.1f}" '
                f'x2="{tx2:.1f}" y2="{ty2:.1f}" '
                f'stroke="#000000" stroke-width="0.38"/>'
            )
            # petite feuille ovale au bout
            parts.append(
                f'  <ellipse cx="{tx2:.1f}" cy="{ty2:.1f}" '
                f'rx="1.8" ry="1.0" '
                f'transform="rotate({math.degrees(twig_a):.0f} {tx2:.1f} {ty2:.1f})" '
                f'fill="none" stroke="#000000" stroke-width="0.3"/>'
            )
    return "\n".join(parts)


def _motif_palmier(W, H, M, cx, cy):
    """Palmier stylisé en bas — EVG"""
    parts   = []
    base_x  = cx
    base_y  = H - M * 0.45
    trunk_h = min(H, W) * 0.18
    crown_y = base_y - trunk_h
    # Tronc (légèrement courbé)
    parts.append(
        f'  <path d="M {base_x:.1f},{base_y:.1f} '
        f'Q {base_x + 3:.1f},{base_y - trunk_h*0.5:.1f} '
        f'{base_x:.1f},{crown_y:.1f}" '
        f'fill="none" stroke="#000000" stroke-width="0.75"/>'
    )
    # Palmes
    leaf_angles = [-110, -75, -45, -15, 15, 45, 75, 110]
    for deg in leaf_angles:
        a      = math.radians(deg)
        ll     = trunk_h * 0.85
        lx2    = base_x + ll * math.cos(a)
        ly2    = crown_y + ll * math.sin(a)
        # Contrôle pour courbure de palme
        ctrl_x = base_x + ll * 0.5 * math.cos(a + math.radians(10))
        ctrl_y = crown_y + ll * 0.5 * math.sin(a + math.radians(10))
        parts.append(
            f'  <path d="M {base_x:.1f},{crown_y:.1f} '
            f'Q {ctrl_x:.1f},{ctrl_y:.1f} {lx2:.1f},{ly2:.1f}" '
            f'fill="none" stroke="#000000" stroke-width="0.45"/>'
        )
    # Noix de coco (3 petits cercles)
    for i in range(3):
        a   = math.radians(-90 + (i - 1) * 30)
        r   = min(W, H) * 0.020
        ccx = base_x + r * 1.5 * math.cos(a)
        ccy = crown_y + r * 1.5 * math.sin(a)
        parts.append(
            f'  <circle cx="{ccx:.1f}" cy="{ccy:.1f}" r="{r:.1f}" '
            f'fill="none" stroke="#000000" stroke-width="0.4"/>'
        )
    return "\n".join(parts)


def _motif_diamant(W, H, M, cx, cy):
    """Diamant / bague stylisée en bas"""
    parts = []
    s     = min(W, H) * 0.07
    dx    = cx
    dy    = H - M * 0.62
    # Diamant (losange avec facettes)
    verts = [
        (dx,      dy - s),        # haut
        (dx + s,  dy),            # droite
        (dx,      dy + s * 0.7),  # bas
        (dx - s,  dy),            # gauche
    ]
    d = "M " + " L ".join(f"{v[0]:.1f},{v[1]:.1f}" for v in verts) + " Z"
    parts.append(f'  <path d="{d}" fill="none" stroke="#000000" stroke-width="0.5"/>')
    # Ligne de table (facette centrale)
    parts.append(
        f'  <line x1="{dx - s*0.45:.1f}" y1="{dy - s*0.28:.1f}" '
        f'x2="{dx + s*0.45:.1f}" y2="{dy - s*0.28:.1f}" '
        f'stroke="#000000" stroke-width="0.35"/>'
    )
    # Facettes obliques
    for sx in [-1, 1]:
        parts.append(
            f'  <line x1="{dx:.1f}" y1="{dy - s:.1f}" '
            f'x2="{dx + sx*s*0.45:.1f}" y2="{dy - s*0.28:.1f}" '
            f'stroke="#000000" stroke-width="0.32"/>'
        )
    return "\n".join(parts)


_MOTIF_FNS = {
    "alliances":    _motif_alliances,
    "couronne":     _motif_couronne,
    "coeur":        _motif_coeur,
    "etoiles":      _motif_etoiles,
    "fleurs_coins": _motif_fleurs_coins,
    "branches":     _motif_branches,
    "palmier":      _motif_palmier,
    "diamant":      _motif_diamant,
}


def _render_motif(motif_id: str, W, H, M, cx, cy) -> str:
    fn = _MOTIF_FNS.get(motif_id)
    return fn(W, H, M, cx, cy) if fn else ""


# ── Génération principale ─────────────────────────────────────────────────────

def generate_svg(config: OrderConfig) -> str:
    """
    Génère un SVG complet prêt pour LightBurn.
    Retourne une chaîne UTF-8.
    Lève ValueError si product_id ou font_id est inconnu.
    """
    if config.product_id not in PRODUCTS:
        raise ValueError(
            f"Produit inconnu : '{config.product_id}'. "
            f"Disponibles : {', '.join(PRODUCTS)}"
        )

    p    = PRODUCTS[config.product_id]
    font = FONTS.get(config.font_id, FONTS["script"])
    mat  = p.get("material", "bois")

    # Dimensions canevas
    W  = px(p["width"])
    H  = px(p["height"])
    M  = px(p["margin"])
    cx = round(W / 2, 2)
    cy = round(H / 2, 2)
    cr = px(p.get("corner_r", 0))

    # Lignes de texte non vides
    lines = [l.strip() for l in [config.line1, config.line2, config.line3] if l.strip()]
    n     = len(lines)

    # Taille de police adaptative
    max_chars    = max((len(l) for l in lines), default=1)
    area_w       = W - 2 * M
    raw_font     = min(area_w / max(max_chars, 1) * 1.45, H / (n + 2.5) * 0.88)
    base_font    = max(px(6), min(raw_font, px(13)))
    line_h       = base_font * 1.40

    # Ajustement vertical si motif présent (réserver espace haut/bas)
    motif_reserve = px(8) if config.motif_id != "sans" else 0
    avail_h       = H - 2 * M - motif_reserve * 2
    if n > 0:
        base_font = min(base_font, avail_h / (n + 1))
        line_h    = base_font * 1.40
    total_text_h  = line_h * n
    text_start_y  = cy - total_text_h / 2 + base_font * 0.82

    # Paramètres selon matériau
    if mat == "metal":
        stroke_main  = "#000000"
        stroke_cut   = "#FF0000"
        stroke_w_txt = "0.35px"  # trait plus fin sur métal pour précision
    else:
        stroke_main  = "#000000"
        stroke_cut   = "#FF0000"
        stroke_w_txt = "0.4px"

    parts = []

    # ── En-tête SVG ──────────────────────────────────────────────────────────
    preset = LIGHTBURN_PRESETS.get(f"{mat}_gravure", LIGHTBURN_PRESETS["bois_gravure"])
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{W}px" height="{H}px"'
        f' viewBox="0 0 {W} {H}">\n'
        f'  <!-- LaserGrave Événements v3.0 -->\n'
        f'  <!-- Produit   : {p["label"]} — {p["width"]}×{p["height"]} mm -->\n'
        f'  <!-- Matériau  : {mat.upper()} -->\n'
        f'  <!-- GRAVURE   : vitesse={preset["vitesse"]} puissance={preset["puissance"]} passes={preset["passes"]} -->\n'
        f'  <!-- DÉCOUPE   : vitesse=800 puissance=100% passes=3 -->\n'
        f'  <!-- Machine   : Longer Ray 5 40W — LightBurn -->\n'
        f'  <defs><style>'
        f'text{{font-family:{font};fill:none;stroke:{stroke_main};'
        f'stroke-width:{stroke_w_txt};paint-order:stroke;}}'
        f'</style></defs>'
    )

    # ── Couche preview fond (uniquement pour rendu navigateur, pas LightBurn) ─
    if mat == "metal":
        parts.append(
            f'\n  <!-- PREVIEW_BG (ignorer dans LightBurn) -->'
            f'\n  <rect x="0" y="0" width="{W}" height="{H}" '
            f'fill="#D8D8D8" opacity="0.18" stroke="none"/>'
        )

    # ── Contour produit (DÉCOUPE = rouge) ────────────────────────────────────
    parts.append('\n  <!-- ═══ DECOUPE (rouge) ═══ -->')
    parts.append(
        f'  <rect x="1" y="1" width="{round(W-2,2)}" height="{round(H-2,2)}"'
        f' rx="{cr}" ry="{cr}"'
        f' fill="none" stroke="{stroke_cut}" stroke-width="0.5"/>'
    )

    # ── Bordure décorative (GRAVURE = noir) ──────────────────────────────────
    if config.decorative_border:
        bd  = round(M * 0.50, 2)
        bw  = round(W - 2 * bd, 2)
        bh  = round(H - 2 * bd, 2)
        bcr = max(0, round(cr - px(1.5), 2))
        # Double filet pour métal, tirets pour bois
        if mat == "metal":
            parts.append('\n  <!-- ═══ BORDURE METAL ═══ -->')
            parts.append(
                f'  <rect x="{bd}" y="{bd}" width="{bw}" height="{bh}"'
                f' rx="{bcr}" ry="{bcr}"'
                f' fill="none" stroke="{stroke_main}" stroke-width="0.55"/>'
            )
            # Second filet intérieur serré
            bd2 = bd + px(1.0)
            bw2 = round(W - 2 * bd2, 2)
            bh2 = round(H - 2 * bd2, 2)
            parts.append(
                f'  <rect x="{bd2:.1f}" y="{bd2:.1f}" width="{bw2:.1f}" height="{bh2:.1f}"'
                f' rx="{bcr}" ry="{bcr}"'
                f' fill="none" stroke="{stroke_main}" stroke-width="0.30"/>'
            )
        else:
            parts.append('\n  <!-- ═══ BORDURE BOIS ═══ -->')
            parts.append(
                f'  <rect x="{bd}" y="{bd}" width="{bw}" height="{bh}"'
                f' rx="{bcr}" ry="{bcr}"'
                f' fill="none" stroke="{stroke_main}" stroke-width="0.55"'
                f' stroke-dasharray="4,2.5"/>'
            )

    # ── Motif décoratif ───────────────────────────────────────────────────────
    if config.motif_id != "sans":
        motif_svg = _render_motif(config.motif_id, W, H, M, cx, cy)
        if motif_svg:
            parts.append(f'\n  <!-- ═══ MOTIF : {config.motif_id.upper()} ═══ -->')
            parts.append(motif_svg)

    # ── Texte gravé ───────────────────────────────────────────────────────────
    if lines:
        parts.append("\n  <!-- ═══ TEXTE ═══ -->")
        for i, line in enumerate(lines):
            y      = round(text_start_y + i * line_h, 2)
            weight = "bold" if (i == 0 and n > 1) else "normal"
            size   = round(base_font * (1.08 if i == 0 else 1.0), 2)
            style  = "" if i == 0 else f' font-style="italic"' if config.font_id == "script" else ""
            parts.append(
                f'  <text x="{cx}" y="{y}"'
                f' font-size="{size}" font-weight="{weight}"{style}'
                f' text-anchor="middle" dominant-baseline="auto">'
                f'{_escape_xml(line)}</text>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


# ── Sauvegarde sur disque ─────────────────────────────────────────────────────

def save_order(config: OrderConfig) -> str:
    """Génère et sauvegarde le SVG. Retourne le chemin du fichier."""
    os.makedirs(config.output_dir, exist_ok=True)
    name     = _safe_filename(config.line1)
    filename = f"{config.product_id}_{name}.svg"
    path     = os.path.join(config.output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(generate_svg(config))
    p = PRODUCTS[config.product_id]
    print(f"✅  {filename}  ({p['width']}×{p['height']} mm — {p['material']})")
    return path


# ── Tests / démo ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    samples = [
        OrderConfig("cadre_15x10",  "Marie & Thomas", "15 Juin 2025",   "Pour toujours",            "script",    "alliances",    True, "mariage"),
        OrderConfig("cadre_20x15",  "Léa & Antoine",  "12 Juillet 2025","Ensemble pour l'éternité", "script",    "branches",     True, "mariage"),
        OrderConfig("plaque_bois",  "Chloé",          "Veux-tu être ma demoiselle d'honneur ?", "Juin 2025", "classique", "fleurs_coins", True, "mariage"),
        OrderConfig("plaque_metal", "Emma",           "Ma témoin préférée", "Merci d'être là",      "gravure",   "diamant",      True, "mariage"),
        OrderConfig("coffret_evjf", "Sophie",         "EVJF 20 Mai 2025","Lucie · Eva · Camille",   "script",    "couronne",     True, "evjf"),
        OrderConfig("coffret_evjf", "Maxime",         "EVG 18 Mai 2025", "Thomas · Romain · Jules", "moderne",   "palmier",      True, "evg"),
    ]
    for s in samples:
        save_order(s)
    print(f"\n📁 Fichiers générés dans ./output/")
