"""import_selecge.py — Receveur d'une palette SelecGE (logique pure, testable).

Contrat d'entrée (1 compétition par appel, cas INDIVIDUEL) :

    {
      "competition": {
        "nom": str,                 # obligatoire (meta.competition)
        "categorie": str,           # meta.cat_id (M15, Senior, V1...)
        "format": "individuel",     # défaut 'individuel'
        "arme": str|None,           # ex 'sabre'
        "genre": str|None,          # 'HD' (Hommes+Dames fusionnés), 'H' ou 'D'
        "date": str|None,
        "lieu": str|None,
        "date_limite": str|None,    # meta.date_limite_retour
        "arbitres_requis": 0|1,
        "type_arbitrage": "none|standard|master",
        "seuil1": int, "seuil2": int,
        "source_arbitres": str
      },
      "qualifies": [
        {"nom": str, "prenom": str, "club": str,
         "section": str|None, "rang": int|None, "equipe": str|None,
         "genre": "H"|"D"|None}
      ]
    }

Idempotent : un ré-envoi de la même palette met à jour, ne crée pas de doublon.
Les confirmations déjà saisies par les clubs sont préservées (statut non réinitialisé).

Limite connue (v1) : un tireur retiré d'un ré-import n'est PAS supprimé
(évite d'orphaniner une participation déjà confirmée). Le nettoyage des
qualifiés obsolètes est laissé à une étape ultérieure.
"""
import os
import secrets

FORMATS = ("individuel", "equipe")
TYPES_ARBITRAGE = ("none", "standard", "master")

# Arme canonique : label minuscule. Accepte lettres (E/F/S) et labels.
_ARME_CANON = {
    "e": "epee", "f": "fleuret", "s": "sabre",
    "epee": "epee", "épée": "epee", "épee": "epee", "epée": "epee",
    "fleuret": "fleuret", "sabre": "sabre",
}

def _canon_arme(a):
    if not a:
        return a
    k = str(a).strip().lower()
    return _ARME_CANON.get(k, k)


def _placeholder_email(nom_club):
    """Email club de remplacement tant que le mapping réel n'est pas fourni."""
    return os.environ.get("CLUB_EMAIL_PLACEHOLDER", "atrcrege@gmail.com")


def _val(d, *keys, default=None):
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return default


def _upsert_competition(conn, c):
    nom = (c.get("nom") or "").strip()
    if not nom:
        raise ValueError("competition.nom manquant")
    fmt = c.get("format") or "individuel"
    if fmt not in FORMATS:
        raise ValueError(f"format invalide : {fmt!r}")
    type_arb = c.get("type_arbitrage") or "none"
    if type_arb not in TYPES_ARBITRAGE:
        raise ValueError(f"type_arbitrage invalide : {type_arb!r}")

    categorie = c.get("categorie") or ""
    date = c.get("date")
    champs = dict(
        nom=nom, categorie=categorie, format=fmt,
        arme=_canon_arme(c.get("arme")), genre=c.get("genre"), date=date,
        lieu=c.get("lieu"), date_limite=c.get("date_limite"),
        arbitres_requis=1 if c.get("arbitres_requis") else 0,
        type_arbitrage=type_arb,
        seuil1=int(c.get("seuil1", 4)), seuil2=int(c.get("seuil2", 9)),
        source_arbitres=c.get("source_arbitres") or "aucun",
    )

    # Clé naturelle : (nom, categorie, format, date)
    row = conn.execute(
        "SELECT id FROM competition WHERE nom=? AND categorie=? AND format=? "
        "AND IFNULL(date,'')=IFNULL(?,'')",
        (nom, categorie, fmt, date),
    ).fetchone()
    if row:
        comp_id = row["id"]
        conn.execute(
            "UPDATE competition SET arme=?, genre=?, lieu=?, date_limite=?, "
            "arbitres_requis=?, type_arbitrage=?, seuil1=?, seuil2=?, source_arbitres=? "
            "WHERE id=?",
            (champs["arme"], champs["genre"], champs["lieu"], champs["date_limite"],
             champs["arbitres_requis"], champs["type_arbitrage"], champs["seuil1"],
             champs["seuil2"], champs["source_arbitres"], comp_id),
        )
        return comp_id, False
    cur = conn.execute(
        "INSERT INTO competition"
        "(nom,categorie,format,arme,genre,date,lieu,date_limite,"
        " arbitres_requis,type_arbitrage,seuil1,seuil2,source_arbitres)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (champs["nom"], champs["categorie"], champs["format"], champs["arme"],
         champs["genre"], champs["date"], champs["lieu"], champs["date_limite"],
         champs["arbitres_requis"], champs["type_arbitrage"], champs["seuil1"],
         champs["seuil2"], champs["source_arbitres"]),
    )
    return cur.lastrowid, True


def _club_id(conn, nom_club, cache, stats):
    """Retourne l'id du club (match par nom), le crée avec email placeholder sinon."""
    nom = (nom_club or "").strip() or "Club inconnu"
    if nom in cache:
        return cache[nom]
    row = conn.execute("SELECT id FROM club WHERE nom=?", (nom,)).fetchone()
    if row:
        cache[nom] = row["id"]
        return row["id"]
    cur = conn.execute(
        "INSERT INTO club(nom, code_ffe, email) VALUES (?,?,?)",
        (nom, None, _placeholder_email(nom)),
    )
    cache[nom] = cur.lastrowid
    stats["clubs_crees"] += 1
    return cur.lastrowid


def _upsert_qualifie(conn, comp_id, club_id, q, stats):
    nom = (q.get("nom") or "").strip()
    prenom = (q.get("prenom") or "").strip()
    rang = q.get("rang")
    rang = int(rang) if rang not in (None, "") else None
    section = q.get("section")
    equipe = q.get("equipe")
    genre = q.get("genre")  # 'H' | 'D' | None (onglets H/D)
    rang_label = q.get("rang_label")  # 'CL NAT 24' / 'CL GE 3' (préfixe conservé)
    row = conn.execute(
        "SELECT id FROM qualifie WHERE competition_id=? AND club_id=? AND nom=? AND prenom=?",
        (comp_id, club_id, nom, prenom),
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE qualifie SET section=?, equipe=?, rang=?, rang_label=?, genre=? WHERE id=?",
            (section, equipe, rang, rang_label, genre, row["id"]),
        )
        stats["qualifies_maj"] += 1
    else:
        conn.execute(
            "INSERT INTO qualifie(competition_id,club_id,nom,prenom,section,equipe,rang,rang_label,genre)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (comp_id, club_id, nom, prenom, section, equipe, rang, rang_label, genre),
        )
        stats["qualifies_crees"] += 1


def _ensure_confirmation(conn, comp_id, club_id, stats):
    """1 confirmation par (compétition, club). Préserve le statut existant."""
    row = conn.execute(
        "SELECT id FROM confirmation WHERE competition_id=? AND club_id=?",
        (comp_id, club_id),
    ).fetchone()
    if row:
        return
    token = secrets.token_urlsafe(24)
    conn.execute(
        "INSERT INTO confirmation(competition_id, club_id, token) VALUES (?,?,?)",
        (comp_id, club_id, token),
    )
    stats["confirmations_creees"] += 1


def importer(conn, payload):
    """Importe une palette. Retourne un résumé. Commit géré par l'appelant."""
    if not isinstance(payload, dict):
        raise ValueError("payload doit être un objet JSON")
    comp = payload.get("competition") or {}
    qualifies = payload.get("qualifies") or []

    stats = {
        "clubs_crees": 0, "qualifies_crees": 0, "qualifies_maj": 0,
        "confirmations_creees": 0,
    }
    comp_id, comp_cree = _upsert_competition(conn, comp)

    club_cache = {}
    clubs_vus = set()
    for q in qualifies:
        club_id = _club_id(conn, q.get("club"), club_cache, stats)
        _upsert_qualifie(conn, comp_id, club_id, q, stats)
        clubs_vus.add(club_id)

    for club_id in clubs_vus:
        _ensure_confirmation(conn, comp_id, club_id, stats)

    return {
        "competition_id": comp_id,
        "competition_creee": comp_cree,
        "qualifies_recus": len(qualifies),
        "clubs": len(clubs_vus),
        **stats,
    }
