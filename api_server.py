"""
LaserGrave Événements — Serveur Flask v3.0
Endpoints : /health  /products  /generate  /preview
Hébergement : Railway.app  (Procfile: web: gunicorn api_server:app)
"""

import base64
import logging
import os
import re
import time
import uuid
from datetime import datetime

from flask import Flask, jsonify, request, Response
from flask.logging import create_logger

from generate_svg import (
    PRODUCTS, FONTS, MOTIFS, EVENT_DEFAULTS,
    OrderConfig, generate_svg
)

# ── Config ────────────────────────────────────────────────────────────────────

app = Flask(__name__)
log = create_logger(app)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

API_KEY         = os.environ.get("API_KEY", "lasergrave-dev-key")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")   # restreindre en prod


# ── CORS helpers ──────────────────────────────────────────────────────────────

def _cors(response: Response) -> Response:
    response.headers["Access-Control-Allow-Origin"]  = ALLOWED_ORIGINS
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.after_request
def after_request(response):
    return _cors(response)


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        return _cors(Response(status=204))


def _require_api_key():
    key = request.headers.get("X-API-Key", "")
    if key != API_KEY:
        return jsonify({"error": "Unauthorized", "hint": "Fournir X-API-Key correct"}), 401
    return None


def _parse_bool(val, default=True) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "oui", "yes", "on")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":    "ok",
        "service":   "LaserGrave Événements API",
        "version":   "3.0.0",
        "products":  len(PRODUCTS),
        "fonts":     len(FONTS),
        "motifs":    len(MOTIFS),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


@app.route("/products", methods=["GET"])
def list_products():
    """
    Liste les produits, polices, motifs et événements disponibles.
    Utilisé par le formulaire client pour peupler les selects dynamiquement.
    """
    return jsonify({
        "products": [
            {
                "id":        k,
                "label":     v["label"],
                "width_mm":  v["width"],
                "height_mm": v["height"],
                "shape":     v["shape"],
                "material":  v.get("material", "bois"),
                "prix":      v.get("prix", 0),
                "max_lines": v.get("max_lines", 3),
            }
            for k, v in PRODUCTS.items()
        ],
        "fonts": [
            {"id": k, "family": v} for k, v in FONTS.items()
        ],
        "motifs": [
            {"id": k, "label": v} for k, v in MOTIFS.items()
        ],
        "event_defaults": EVENT_DEFAULTS,
    })


@app.route("/generate", methods=["POST"])
def generate():
    """
    Génère un SVG à partir d'une commande JSON. Nécessite X-API-Key.

    Champs requis  : product_id, line1
    Champs options : line2, line3, font_id, motif_id, border, event_type

    Réponse : svg_base64, svg_raw, filename, dimensions, product_label,
              request_id, duration_ms
    """
    auth_err = _require_api_key()
    if auth_err:
        return auth_err

    req_id = str(uuid.uuid4())[:8]
    t0     = time.time()

    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        return jsonify({"error": "JSON invalide", "request_id": req_id}), 400

    # Validation champs obligatoires
    for field in ("product_id", "line1"):
        if not data.get(field, "").strip():
            return jsonify({
                "error": f"Champ requis manquant : '{field}'",
                "request_id": req_id,
            }), 400

    config = _build_config(data)

    try:
        svg = generate_svg(config)
    except ValueError as e:
        log.warning(f"[{req_id}] Validation : {e}")
        return jsonify({"error": str(e), "request_id": req_id}), 400
    except Exception as e:
        log.error(f"[{req_id}] Erreur génération : {e}")
        return jsonify({"error": "Erreur interne de génération", "request_id": req_id}), 500

    safe     = re.sub(r"[^\w\s-]", "", config.line1, flags=re.UNICODE)
    safe     = re.sub(r"\s+", "_", safe.strip())[:20]
    filename = f"{config.product_id}_{safe}.svg"
    p        = PRODUCTS[config.product_id]
    duration = round((time.time() - t0) * 1000, 1)

    log.info(
        f"[{req_id}] ✅ {config.product_id} | '{config.line1}' "
        f"| font={config.font_id} | motif={config.motif_id} "
        f"| mat={p.get('material','bois')} | {duration}ms"
    )

    return jsonify({
        "svg_base64":    base64.b64encode(svg.encode("utf-8")).decode("utf-8"),
        "svg_raw":       svg,
        "filename":      filename,
        "dimensions":    f"{p['width']}×{p['height']} mm",
        "product_label": p["label"],
        "material":      p.get("material", "bois"),
        "prix":          p.get("prix", 0),
        "request_id":    req_id,
        "duration_ms":   duration,
    })


@app.route("/preview", methods=["POST"])
def preview():
    """
    Variante publique de /generate → renvoie le SVG brut (image/svg+xml).
    Pas de clé API requise. Utilisé pour la prévisualisation temps réel.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        return "JSON invalide", 400

    if not data.get("product_id") or not data.get("line1"):
        # Retourner un SVG placeholder si champs vides
        placeholder = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">'
            '<rect x="1" y="1" width="298" height="198" rx="4" fill="none" stroke="#ccc" stroke-width="1"/>'
            '<text x="150" y="105" text-anchor="middle" font-family="Georgia,serif" '
            'font-size="13" fill="#aaa">Aperçu de votre gravure</text>'
            '</svg>'
        )
        return Response(placeholder, mimetype="image/svg+xml")

    config = _build_config(data)

    try:
        svg = generate_svg(config)
    except Exception as e:
        return str(e), 400

    return Response(svg, mimetype="image/svg+xml")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_config(data: dict) -> OrderConfig:
    """Construit un OrderConfig depuis un dict JSON."""
    event_type  = data.get("event_type", "mariage").strip().lower()
    defaults    = EVENT_DEFAULTS.get(event_type, EVENT_DEFAULTS["mariage"])
    font_id     = data.get("font_id", defaults["font"]).strip()
    motif_id    = data.get("motif_id", defaults["motif"]).strip()
    return OrderConfig(
        product_id        = data.get("product_id", "").strip(),
        line1             = data.get("line1", "").strip(),
        line2             = data.get("line2", "").strip(),
        line3             = data.get("line3", "").strip(),
        font_id           = font_id,
        motif_id          = motif_id,
        decorative_border = _parse_bool(data.get("border", True)),
        event_type        = event_type,
    )


# ── Démarrage ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    log.info(f"🔥 LaserGrave Événements API v3.0 — port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
