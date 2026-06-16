"""
arbitrage.py — Règle d'arbitrage côté plateforme (miroir de SelecGE/REGLES.md §5).

STANDARD : seuils 4/9 plafonné à 2.  MASTER : 1 dès 1 tireur.  NONE : 0.
Niveaux d'arbitre officiels LREGE (cf. SelecGE feuille.py).
"""

NIVEAUX_ARBITRE = (
    "regional_formation", "regional",
    "national_formation", "national", "international",
)

SEUIL1_DEFAUT = 4
SEUIL2_DEFAUT = 9
STANDARD_PLAFOND = 2


def calculer_arbitres_requis(nombre_tireurs, type_arbitrage,
                             seuil1=SEUIL1_DEFAUT, seuil2=SEUIL2_DEFAUT):
    """Nombre d'arbitres requis selon le type et le nombre de tireurs."""
    n = int(nombre_tireurs or 0)
    t = type_arbitrage or "none"
    if t == "none" or n <= 0:
        return 0
    if t == "standard":
        if n < seuil1:
            return 0
        return 1 if n < seuil2 else STANDARD_PLAFOND
    if t == "master":
        return 1
    return 0
