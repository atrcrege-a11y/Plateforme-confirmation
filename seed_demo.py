"""
seed_demo.py — Jeu de données de démonstration (M15 équipes épée).

Crée une compétition, 2 clubs, des qualifiés répartis dans les équipes GE1/GE2,
et une confirmation (lien magique) par club. Idempotent : repart d'une base vierge.

Usage :
    python migrate.py && python seed_demo.py
    -> imprime les liens /c/<token> par club
"""
from db import get_connection


def seed(conn):
    cur = conn
    cur.execute("INSERT INTO club(id,nom,code_ffe,email) VALUES (1,'C.E. de Châlons en Champagne','51C','chalons@x.fr')")
    cur.execute("INSERT INTO club(id,nom,code_ffe,email) VALUES (2,'CE. Romarimontain','88R','romari@x.fr')")
    cur.execute(
        "INSERT INTO competition(id,nom,categorie,format,arme,genre,date,lieu,date_limite,"
        "arbitres_requis,type_arbitrage,source_arbitres) VALUES "
        "(1,'Fête des jeunes — M15 équipes','M15','equipe','E','H','2026-06-14','Paris','2026-04-24',"
        "0,'none','aucun')"
    )
    # qualifiés : équipes mixtes (clubs différents dans la même équipe)
    q = [
        (1, 1, "JANER", "Basile", "GE1", "GE1", 8),       # club 1
        (1, 2, "HOPFNER", "Robin", "GE1", "GE1", 71),     # club 2
        (1, 1, "WILLEM", "Paul", "GE2", "GE2", 3),        # club 1
        (1, 2, "CLAUDE DESCHASEAUX", "Tristan", "Remplaçants", "Remplaçants", 13),  # club 2
    ]
    cur.executemany(
        "INSERT INTO qualifie(competition_id,club_id,nom,prenom,section,equipe,rang)"
        " VALUES (?,?,?,?,?,?,?)", q)
    # un lien magique par club
    cur.execute("INSERT INTO confirmation(id,competition_id,club_id,token) VALUES (1,1,1,'tok-chalons')")
    cur.execute("INSERT INTO confirmation(id,competition_id,club_id,token) VALUES (2,1,2,'tok-romari')")

    # --- Vétérans par équipes : catégorie d'âge + arbitrage requis (master) ---
    cur.execute(
        "INSERT INTO competition(id,nom,categorie,format,arme,genre,date,lieu,date_limite,"
        "arbitres_requis,type_arbitrage,source_arbitres) VALUES "
        "(2,'Coupe Vétérans par équipes','Veterans','equipe','E','H','2026-05-17','Metz','2026-05-01',"
        "1,'master','club')"
    )
    qv = [
        (2, 1, "LEROY", "Marc", "Équipe Vét. 1", "Équipe Vét. 1", 1),
        (2, 1, "GARNIER", "Paul", "Équipe Vét. 1", "Équipe Vét. 1", 2),
        (2, 2, "MOREAU", "Jean", "Équipe Vét. 1", "Équipe Vét. 1", 3),
    ]
    cur.executemany(
        "INSERT INTO qualifie(competition_id,club_id,nom,prenom,section,equipe,rang)"
        " VALUES (?,?,?,?,?,?,?)", qv)
    cur.execute("INSERT INTO confirmation(id,competition_id,club_id,token) VALUES (3,2,1,'tok-vet-chalons')")

    # --- Individuels Senior : sections qualifiés/remplaçants + arbitrage standard ---
    cur.execute(
        "INSERT INTO competition(id,nom,categorie,format,arme,genre,date,lieu,date_limite,"
        "arbitres_requis,type_arbitrage,source_arbitres) VALUES "
        "(3,'Championnat individuel Senior','Senior','individuel','E','H','2026-03-08','Nancy','2026-02-20',"
        "1,'standard','club')"
    )
    qi = [
        (3, 1, "DUVAL", "Hugo", "Qualifiés", None, 1),
        (3, 1, "FONTAINE", "Léo", "Qualifiés", None, 2),
        (3, 1, "ROBIN", "Tom", "Remplaçants 1-5", None, 3),
        (3, 1, "NOEL", "Axel", "Remplaçants 1-5", None, 4),
        (3, 2, "PEREZ", "Sacha", "Qualifiés", None, 5),
    ]
    cur.executemany(
        "INSERT INTO qualifie(competition_id,club_id,nom,prenom,section,equipe,rang)"
        " VALUES (?,?,?,?,?,?,?)", qi)
    cur.execute("INSERT INTO confirmation(id,competition_id,club_id,token) VALUES (4,3,1,'tok-indiv-chalons')")

    # --- M20 par équipes : formulaire simple (nom/prénom, aucun champ, sans arbitre) ---
    cur.execute(
        "INSERT INTO competition(id,nom,categorie,format,arme,genre,date,lieu,date_limite,"
        "arbitres_requis,type_arbitrage,source_arbitres) VALUES "
        "(4,'Championnat M20 par équipes','M20','equipe','F','D','2026-04-12','Reims','2026-03-30',"
        "0,'none','aucun')"
    )
    qm = [
        (4, 1, "BLANC", "Eva", "Équipe GE 1", "Équipe GE 1", 1),
        (4, 1, "HENRY", "Lina", "Équipe GE 1", "Équipe GE 1", 2),
        (4, 2, "GIRARD", "Nina", "Équipe GE 1", "Équipe GE 1", 3),
    ]
    cur.executemany(
        "INSERT INTO qualifie(competition_id,club_id,nom,prenom,section,equipe,rang)"
        " VALUES (?,?,?,?,?,?,?)", qm)
    cur.execute("INSERT INTO confirmation(id,competition_id,club_id,token) VALUES (5,4,1,'tok-m20-chalons')")

    # --- M15 individuel HD : onglets Hommes/Dames + sections quota + genre par tireur ---
    cur.execute(
        "INSERT INTO competition(id,nom,categorie,format,arme,genre,date,lieu,date_limite,"
        "arbitres_requis,type_arbitrage,source_arbitres) VALUES "
        "(5,'Fête des jeunes — M15 individuel','M15','individuel','S','HD','2026-06-13','Paris','2026-06-05',"
        "1,'standard','club')"
    )
    qhd = [
        (5, 1, "MARTIN", "Léa", "QUOTA FÉDÉRAL", None, 1, "CL NAT 1", "D"),
        (5, 1, "BERNARD", "Hugo", "QUOTA FÉDÉRAL", None, 2, "CL NAT 2", "H"),
        (5, 2, "DUBOIS", "Inès", "QUOTA LREGE", None, 3, "CL GE 3", "D"),
        (5, 2, "PETIT", "Tom", "QUOTA LREGE", None, 4, "CL GE 4", "H"),
    ]
    cur.executemany(
        "INSERT INTO qualifie(competition_id,club_id,nom,prenom,section,equipe,rang,rang_label,genre)"
        " VALUES (?,?,?,?,?,?,?,?,?)", qhd)
    cur.execute("INSERT INTO confirmation(id,competition_id,club_id,token) VALUES (6,5,1,'tok-hd-chalons')")
    cur.execute("INSERT INTO confirmation(id,competition_id,club_id,token) VALUES (7,5,2,'tok-hd-romari')")
    conn.commit()


if __name__ == "__main__":
    conn = get_connection()
    try:
        seed(conn)
        for r in conn.execute("SELECT cl.nom, cf.token FROM confirmation cf JOIN club cl ON cl.id=cf.club_id"):
            print(f"  {r['nom']:<35} -> /c/{r['token']}")
    finally:
        conn.close()
