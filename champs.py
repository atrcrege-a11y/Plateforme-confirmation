"""
champs.py — Champs de saisie par tireur selon la catégorie de compétition.

Le front (confirmation.html) est générique : il rend une colonne par champ
renvoyé ici. Permet de couvrir M15 / Vétérans / Individuels / M17-M20-Sénior
avec un seul moteur.

  - M15            -> taille de veste
  - Vétérans (V1..V4) -> catégorie d'âge (V1-V2 / V3-V4)
  - autres         -> aucun champ (présence seule)
"""

VESTE = {
    "key": "taille_veste", "label": "Veste", "type": "select",
    "options": ["T8", "T10", "T12", "T14", "S", "M", "L", "XL"],
    "required": True,
}
CAT_AGE = {
    "key": "categorie_age", "label": "Catégorie", "type": "select",
    "options": ["V1-V2", "V3-V4"],
    "required": True,
}

_VETERANS = {"V1", "V2", "V3", "V4", "VETERANS", "VÉTÉRANS"}


def champs_tireur(categorie):
    """Retourne la liste des champs à saisir pour un tireur de cette catégorie."""
    cat = (categorie or "").strip().upper()
    if cat.startswith("M15"):
        return [VESTE]
    if cat in _VETERANS or cat.startswith("VETERAN") or cat.startswith("VÉTÉRAN"):
        return [CAT_AGE]
    return []
