-- ════════════════════════════════════════════════════════════════
-- Plateforme Confirmation LREGE — schéma SQLite (v1)
-- Auth : lien magique par (club, compétition) via confirmation.token
-- ════════════════════════════════════════════════════════════════
PRAGMA foreign_keys = ON;

-- Référentiel ------------------------------------------------------
CREATE TABLE IF NOT EXISTS club (
    id        INTEGER PRIMARY KEY,
    nom       TEXT NOT NULL,
    code_ffe  TEXT UNIQUE,
    email     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS competition (
    id              INTEGER PRIMARY KEY,
    nom             TEXT NOT NULL,
    categorie       TEXT NOT NULL,                 -- M15, M17, M20, Senior, V1..V4
    format          TEXT NOT NULL CHECK(format IN ('individuel','equipe')),
    arme            TEXT,
    genre           TEXT,
    date            TEXT,
    lieu            TEXT,
    date_limite     TEXT,
    -- bloc arbitrage (contrat export 1.4 / REGLES.md §5)
    arbitres_requis INTEGER NOT NULL DEFAULT 0,    -- bool 0/1
    type_arbitrage  TEXT NOT NULL DEFAULT 'none'
                    CHECK(type_arbitrage IN ('none','standard','master')),
    seuil1          INTEGER NOT NULL DEFAULT 4,
    seuil2          INTEGER NOT NULL DEFAULT 9,
    source_arbitres TEXT NOT NULL DEFAULT 'aucun'
);

-- Qualifiés (importés de l'export SelecGE) -------------------------
CREATE TABLE IF NOT EXISTS qualifie (
    id              INTEGER PRIMARY KEY,
    competition_id  INTEGER NOT NULL REFERENCES competition(id) ON DELETE CASCADE,
    club_id         INTEGER NOT NULL REFERENCES club(id)        ON DELETE CASCADE,
    nom             TEXT NOT NULL,
    prenom          TEXT NOT NULL,
    section         TEXT,                          -- 'qualifie' | 'remplacant' | 'N1'..'N3'
    equipe          TEXT,                          -- nom d'équipe si format=equipe, sinon NULL
    rang            INTEGER
);

-- Acte de confirmation du club (1 par club × compétition) ----------
CREATE TABLE IF NOT EXISTS confirmation (
    id                  INTEGER PRIMARY KEY,
    competition_id      INTEGER NOT NULL REFERENCES competition(id) ON DELETE CASCADE,
    club_id             INTEGER NOT NULL REFERENCES club(id)        ON DELETE CASCADE,
    token               TEXT NOT NULL UNIQUE,                       -- lien magique
    statut              TEXT NOT NULL DEFAULT 'en_attente'
                        CHECK(statut IN ('en_attente','confirmee')),
    date_confirmation   TEXT,
    confirme_par_email  TEXT,
    corrige_par         TEXT,                       -- email admin/secrétariat si correction manuelle
    date_correction     TEXT,
    UNIQUE(competition_id, club_id)
);

-- Ce que le club confirme réellement -------------------------------
CREATE TABLE IF NOT EXISTS participation_tireur (
    id              INTEGER PRIMARY KEY,
    confirmation_id INTEGER NOT NULL REFERENCES confirmation(id) ON DELETE CASCADE,
    qualifie_id     INTEGER          REFERENCES qualifie(id)     ON DELETE SET NULL,
    present         INTEGER NOT NULL DEFAULT 1,                   -- bool 0/1
    taille_veste    TEXT,                                         -- M15
    categorie_age   TEXT                                          -- Vétérans : 'V1-V2' | 'V3-V4'
);

-- Arbitres saisis par le club --------------------------------------
CREATE TABLE IF NOT EXISTS arbitre (
    id              INTEGER PRIMARY KEY,
    confirmation_id INTEGER NOT NULL REFERENCES confirmation(id) ON DELETE CASCADE,
    nom             TEXT NOT NULL,
    prenom          TEXT NOT NULL,
    club            TEXT NOT NULL,
    -- niveaux officiels LREGE (cf. SelecGE feuille.py / dropdown Excel)
    niveau          TEXT NOT NULL CHECK(niveau IN
                    ('regional_formation','regional',
                     'national_formation','national','international'))
);

-- Index ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_qualifie_comp     ON qualifie(competition_id);
CREATE INDEX IF NOT EXISTS ix_qualifie_club     ON qualifie(club_id);
CREATE INDEX IF NOT EXISTS ix_confirmation_comp ON confirmation(competition_id);
CREATE INDEX IF NOT EXISTS ix_confirmation_tok  ON confirmation(token);
CREATE INDEX IF NOT EXISTS ix_partic_conf       ON participation_tireur(confirmation_id);
CREATE INDEX IF NOT EXISTS ix_arbitre_conf      ON arbitre(confirmation_id);

-- Comptes d'accès au dashboard (admin / secrétariat) ---------------
CREATE TABLE IF NOT EXISTS utilisateur (
    id        INTEGER PRIMARY KEY,
    email     TEXT NOT NULL UNIQUE,
    nom       TEXT NOT NULL,
    mdp_hash  TEXT NOT NULL,
    role      TEXT NOT NULL CHECK(role IN ('admin','secretariat'))
);
