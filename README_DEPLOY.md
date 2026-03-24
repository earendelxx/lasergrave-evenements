# LaserGrave Événements — Guide de déploiement v3.0
# Machine : Longer Ray 5 40W · LightBurn · Matériaux : bois, métal, cuir
# ══════════════════════════════════════════════════════════════════════════════

## STRUCTURE DU PROJET

```
lasergrave-evenements/
├── generate_svg.py      ← Moteur SVG (5 produits événements + 8 motifs)
├── api_server.py        ← Serveur Flask (endpoints: /health /products /generate /preview)
├── requirements.txt     ← flask==3.0.3  gunicorn==22.0.0
├── Procfile             ← web: gunicorn api_server:app
├── index.html           ← Landing page (ouvrir dans un navigateur)
└── formulaire.html      ← Formulaire de commande avec preview temps réel
```

---

## 1. DÉMARRAGE LOCAL (test rapide, 2 minutes)

```bash
# 1. Installer les dépendances
pip install flask gunicorn

# 2. Lancer le serveur
python api_server.py

# 3. Ouvrir le formulaire dans un navigateur
# → double-cliquer sur formulaire.html  OU
# → ouvrir http://localhost:5000/health pour vérifier l'API

# 4. Tester la génération SVG en local
python generate_svg.py
# → crée des fichiers SVG dans ./output/ pour les 6 exemples
```

**L'aperçu temps réel dans formulaire.html appelle http://localhost:5000/preview.**
Pas besoin de déploiement pour tester en local !

---

## 2. DÉPLOIEMENT API SUR RAILWAY (gratuit, ~5 minutes)

### Étapes

1. Créer un compte sur https://railway.app

2. "New Project" → "Deploy from GitHub repo"
   - Créer un repo GitHub et pousser ces fichiers :
     ```
     generate_svg.py  api_server.py  requirements.txt  Procfile
     ```
   - OU utiliser "Deploy from local directory"

3. Ajouter les **Variables d'environnement** dans Railway :
   ```
   API_KEY         = [générer avec : python3 -c "import secrets; print(secrets.token_hex(24))"]
   FLASK_DEBUG     = 0
   ALLOWED_ORIGINS = https://ton-site.fr,https://formulaire.ton-site.fr
   ```
   ⚠️ Ne pas mettre PORT — Railway l'injecte automatiquement.

4. Railway détecte le Procfile et lance : `gunicorn api_server:app`

5. Copier l'URL publique générée :
   ```
   https://lasergrave-xxxx.railway.app
   ```

### Test après déploiement

```bash
# Health check
curl https://lasergrave-xxxx.railway.app/health
# → {"status":"ok","service":"LaserGrave Événements API","version":"3.0.0",...}

# Liste des produits
curl https://lasergrave-xxxx.railway.app/products

# Test génération (remplacer YOUR_API_KEY)
curl -X POST https://lasergrave-xxxx.railway.app/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"product_id":"cadre_15x10","line1":"Marie & Thomas","line2":"15 Juin 2025","font_id":"script","motif_id":"alliances"}'
```

---

## 3. CONNECTER LE FORMULAIRE À L'API DÉPLOYÉE

Dans **formulaire.html**, chercher cette ligne (ligne ~300) :

```javascript
const API_URL = "http://localhost:5000";
```

Remplacer par :

```javascript
const API_URL = "https://lasergrave-xxxx.railway.app";
```

---

## 4. HÉBERGER LES FICHIERS HTML (3 options)

### Option A — GitHub Pages (gratuit, recommandé)
```bash
# Dans votre repo GitHub, aller dans Settings → Pages
# Source : "Deploy from a branch" → main → / (root)
# URL : https://votre-nom.github.io/lasergrave/
```

### Option B — Netlify (gratuit, glisser-déposer)
1. https://app.netlify.com → "Add new site" → "Deploy manually"
2. Glisser le dossier contenant index.html et formulaire.html
3. URL automatique : https://lasergrave-xxxx.netlify.app

### Option C — Railway également (tout-en-un)
Ajouter un fichier `static_server.py` ou configurer un serve statique.

---

## 5. AUTOMATISATION MAKE.COM / N8N

### Webhook de commande

Dans **formulaire.html**, décommenter et remplir dans la fonction `submitOrder()` :
```javascript
await fetch('VOTRE_WEBHOOK_MAKE_URL', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});
```

### Payload envoyé au webhook
```json
{
  "product_id":     "cadre_15x10",
  "line1":          "Marie & Thomas",
  "line2":          "15 Juin 2025",
  "line3":          "Pour toujours",
  "font_id":        "script",
  "motif_id":       "alliances",
  "border":         true,
  "event_type":     "mariage",
  "customer_name":  "Marie Dupont",
  "customer_email": "marie@email.fr",
  "comment":        "",
  "accessories":    { "briquet": false, "pcle": false, "plaque-acc": false },
  "prix_total":     "18"
}
```

### Scénario Make recommandé
```
[Webhook] → [HTTP POST /generate avec X-API-Key] → [Upload SVG → Google Drive]
         → [Email toi : nouvelle commande + lien SVG]
         → [Email client : confirmation]
         → [Google Sheets : ajouter ligne commande]
```

---

## 6. PRODUITS ET TARIFS (Longer Ray 5 40W)

| Produit ID     | Dimensions     | Matériau | Prix public |
|----------------|---------------|----------|-------------|
| cadre_15x10    | 150×100 mm    | Bois     | 18 €        |
| cadre_20x15    | 200×150 mm    | Bois     | 27 €        |
| plaque_bois    | 150×100 mm    | Bois     | 22 €        |
| plaque_metal   | 150×100 mm    | Métal    | 28 €        |
| coffret_evjf   | 200×150 mm    | Bois     | 42 €        |

**Zone utile max Longer Ray 5 : 400×400 mm** — tous les produits sont dans les limites.

---

## 7. PRESETS LIGHTBURN

| Matériau | Puissance | Vitesse | Passes | Usage          |
|----------|-----------|---------|--------|----------------|
| Bois     | 70%       | 3000    | 1      | Gravure        |
| Métal    | 85%       | 1500    | 2      | Gravure        |
| Cuir     | 55%       | 4000    | 1      | Gravure        |
| Bois     | 100%      | 800     | 3      | Découpe        |

⚠️ Ces valeurs sont des points de départ. **Toujours tester sur chute avant gravure finale.**

**Convention couleurs SVG → LightBurn :**
- 🔴 Rouge `#FF0000` = couche DÉCOUPE
- ⚫ Noir `#000000` = couche GRAVURE
- 🔵 Bleu (si présent) = ignorer (preview uniquement)

---

## 8. ORGANISATION GOOGLE DRIVE (recommandée)

```
LaserGrave/
├── 01_EN_ATTENTE/     ← SVG reçus, à graver
├── 02_EN_COURS/       ← Déplacer manuellement quand machine allumée
├── 03_ENVOYE/         ← Archivage après expédition
└── 04_TEMPLATES/      ← Gabarits de base par produit
```

**Installer Google Drive Desktop** sur le PC de gravure → LightBurn ouvre
directement les SVG depuis le dossier synchronisé.

**Convention nommage fichiers SVG :**
```
AAAAMMJJ_<product_id>_<prenom>.svg
ex : 20250615_cadre_15x10_Marie_Thomas.svg
```

---

## 9. CHECKLIST AVANT MISE EN LIGNE

- [ ] Variables d'environnement Railway configurées (API_KEY, FLASK_DEBUG=0)
- [ ] ALLOWED_ORIGINS mis à jour avec votre vrai domaine
- [ ] URL API mise à jour dans formulaire.html
- [ ] Test /health OK
- [ ] Test génération cadre + plaque + coffret
- [ ] Test formulaire complet (remplir → aperçu → télécharger SVG)
- [ ] Test LightBurn : ouvrir SVG, vérifier couches rouge/noir
- [ ] Webhook Make configuré et testé
- [ ] Emails de confirmation envoyés et reçus

---

## 10. DÉPANNAGE FRÉQUENT

**Le preview ne s'affiche pas**
→ Vérifier que le serveur tourne (`python api_server.py`)
→ Vérifier CORS : `ALLOWED_ORIGINS` doit inclure l'origine du formulaire
→ Ouvrir la console navigateur (F12) pour voir l'erreur

**Erreur "Produit inconnu"**
→ Vérifier que `product_id` est bien l'un de : cadre_15x10, cadre_20x15, plaque_bois, plaque_metal, coffret_evjf

**Le SVG s'ouvre mal dans LightBurn**
→ File → Import → choisir le .svg
→ Les couches rouge (découpe) et noir (gravure) doivent apparaître séparément
→ Si non, aller dans Edit → Material Library et assigner les couches manuellement

**Police manquante dans l'aperçu navigateur**
→ Ajouter `@import url('https://fonts.googleapis.com/css2?family=Dancing+Script')` en CSS
→ Dans LightBurn, la police sera substituée par une police système — c'est normal

---

*Généré par LaserGrave Événements v3.0 — Machine : Longer Ray 5 40W*
