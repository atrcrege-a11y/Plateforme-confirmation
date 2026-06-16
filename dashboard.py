"""
dashboard.py — Vue secrétariat globale (3.1).

NON cloisonné : c'est la vue d'ensemble (accès réservé à l'admin, cf.
`admin_token()`). Contrairement aux liens club (/c/<token>), le dashboard voit
TOUTES les compétitions et TOUS les clubs.

Fonctions pures (testables sans Flask) :
  - agreger(conn)            -> agrégat par compétition + détail par club
  - participations_export(conn, competition_id) -> lignes tireurs + arbitres
  - construire_xlsx(...)     -> classeur openpyxl (feuilles Tireurs / Arbitres)

Auth : un token admin unique (accès permanent, une seule personne). Surchargé
par la variable d'env ADMIN_TOKEN ; défaut de dev pour les tests/seed.
"""
import io
import os

DEFAULT_ADMIN_TOKEN = "admin-local"  # dev/local uniquement ; surcharger en prod


def admin_token():
    """Token admin courant (env ADMIN_TOKEN > défaut dev)."""
    return os.environ.get("ADMIN_TOKEN", DEFAULT_ADMIN_TOKEN)


def is_admin(token):
    return token == admin_token()


# ── Agrégat dashboard ────────────────────────────────────────────────
def agreger(conn):
    """Agrégat par compétition + détail par club.

    Pour chaque compétition : nb clubs total / confirmés / en attente,
    nb tireurs présents confirmés, nb arbitres. Pour chaque club : statut,
    date de confirmation, nb présents, nb arbitres, token (accès saisie).
    """
    competitions = conn.execute(
        "SELECT id, nom, categorie, format, date, lieu, date_limite "
        "FROM competition ORDER BY date_limite, nom"
    ).fetchall()

    out = []
    for comp in competitions:
        confs = conn.execute(
            "SELECT cf.id, cf.token, cf.statut, cf.date_confirmation, "
            "       cf.confirme_par_email, cl.nom AS club_nom, cl.email AS club_email "
            "FROM confirmation cf JOIN club cl ON cl.id = cf.club_id "
            "WHERE cf.competition_id = ? ORDER BY cl.nom",
            (comp["id"],),
        ).fetchall()

        clubs = []
        n_confirmes = n_presents = n_arbitres = 0
        for cf in confs:
            presents = conn.execute(
                "SELECT COUNT(*) AS n FROM participation_tireur "
                "WHERE confirmation_id = ? AND present = 1",
                (cf["id"],),
            ).fetchone()["n"]
            arbitres = conn.execute(
                "SELECT COUNT(*) AS n FROM arbitre WHERE confirmation_id = ?",
                (cf["id"],),
            ).fetchone()["n"]
            confirmee = cf["statut"] == "confirmee"
            if confirmee:
                n_confirmes += 1
            n_presents += presents
            n_arbitres += arbitres
            clubs.append({
                "club": cf["club_nom"],
                "email": cf["club_email"],
                "statut": cf["statut"],
                "date_confirmation": cf["date_confirmation"],
                "confirme_par_email": cf["confirme_par_email"],
                "presents": presents,
                "arbitres": arbitres,
                "token": cf["token"],
            })

        total = len(confs)
        out.append({
            "id": comp["id"],
            "nom": comp["nom"],
            "categorie": comp["categorie"],
            "format": comp["format"],
            "date": comp["date"],
            "lieu": comp["lieu"],
            "date_limite": comp["date_limite"],
            "clubs_total": total,
            "clubs_confirmes": n_confirmes,
            "clubs_en_attente": total - n_confirmes,
            "tireurs_presents": n_presents,
            "arbitres": n_arbitres,
            "clubs": clubs,
        })
    return out


# ── Export Excel ─────────────────────────────────────────────────────
def participations_export(conn, competition_id):
    """Lignes d'export pour une compétition : (tireurs, arbitres).

    tireurs : club, équipe, section, nom, prénom, présent, veste, catégorie d'âge.
    arbitres : club (confirmant), nom, prénom, club arbitre, niveau.
    Seules les confirmations CONFIRMÉES sont exportées.
    """
    tireurs = conn.execute(
        "SELECT cl.nom AS club, q.equipe, q.section, q.nom, q.prenom, "
        "       pt.present, pt.taille_veste, pt.categorie_age "
        "FROM participation_tireur pt "
        "JOIN confirmation cf ON cf.id = pt.confirmation_id "
        "JOIN club cl ON cl.id = cf.club_id "
        "LEFT JOIN qualifie q ON q.id = pt.qualifie_id "
        "WHERE cf.competition_id = ? AND cf.statut = 'confirmee' "
        "ORDER BY cl.nom, q.equipe, q.rang",
        (competition_id,),
    ).fetchall()

    arbitres = conn.execute(
        "SELECT cl.nom AS club_confirmant, a.nom, a.prenom, a.club, a.niveau "
        "FROM arbitre a "
        "JOIN confirmation cf ON cf.id = a.confirmation_id "
        "JOIN club cl ON cl.id = cf.club_id "
        "WHERE cf.competition_id = ? AND cf.statut = 'confirmee' "
        "ORDER BY cl.nom, a.nom",
        (competition_id,),
    ).fetchall()
    return tireurs, arbitres


def construire_xlsx(comp_nom, tireurs, arbitres):
    """Construit un classeur openpyxl (feuilles Tireurs + Arbitres) et le
    retourne en bytes (.xlsx)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    gras = Font(bold=True)

    ws = wb.active
    ws.title = "Tireurs"
    entetes_t = ["Club", "Équipe", "Section", "Nom", "Prénom",
                 "Présent", "Veste", "Catégorie d'âge"]
    ws.append(entetes_t)
    for c in ws[1]:
        c.font = gras
    for t in tireurs:
        ws.append([
            t["club"], t["equipe"], t["section"], t["nom"], t["prenom"],
            "Oui" if t["present"] else "Non",
            t["taille_veste"] or "", t["categorie_age"] or "",
        ])

    wa = wb.create_sheet("Arbitres")
    entetes_a = ["Club confirmant", "Nom", "Prénom", "Club arbitre", "Niveau"]
    wa.append(entetes_a)
    for c in wa[1]:
        c.font = gras
    for a in arbitres:
        wa.append([a["club_confirmant"], a["nom"], a["prenom"], a["club"], a["niveau"]])

    # largeurs lisibles
    for sheet, entetes in ((ws, entetes_t), (wa, entetes_a)):
        for i, _ in enumerate(entetes, start=1):
            sheet.column_dimensions[chr(64 + i)].width = 20

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
