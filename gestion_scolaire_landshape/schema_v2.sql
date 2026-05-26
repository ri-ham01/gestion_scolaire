-- ============================================================
--  EDUNOVA — SYSTÈME DE GESTION SCOLAIRE
--  BASE DE DONNÉES COMPLÈTE + EXTENSIONS
--  ─────────────────────────────────────────────────────────
--  Version      : 2.0.0
--  Moteur       : MySQL 8.0+ / InnoDB
--  Encodage     : utf8mb4 / utf8mb4_unicode_ci
--  ─────────────────────────────────────────────────────────
--  TABLES : 37 tables + 6 vues
--  ─────────────────────────────────────────────────────────
--  NOUVEAUTÉS v2.0.0 :
--    • posts_professeur      ← Posts style réseau social
--    • commentaires_posts    ← Commentaires sur les posts
--    • pdfs_emplois_temps    ← Cache PDFs emploi du temps
--    • releves_notes         ← + qr_code_token + fichier_pdf_url
--    • conversations         ← + cours_id (chat par cours)
--    • vue_posts_professeur  ← Vue agrégée des posts
-- ============================================================

CREATE DATABASE IF NOT EXISTS gestion_scolaire_landshape
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE gestion_scolaire_landshape;

SET FOREIGN_KEY_CHECKS = 0;
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET time_zone = '+00:00';

CREATE TABLE IF NOT EXISTS parametres_systeme (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    cle             VARCHAR(100)    NOT NULL UNIQUE,
    valeur          TEXT            NOT NULL,
    description     VARCHAR(255),
    modifiable      TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO parametres_systeme (cle, valeur, description, modifiable) VALUES
  ('nom_etablissement',              'EduNova',           'Nom officiel de l''établissement',                           1),
  ('slogan_etablissement',           'L''excellence académique redéfinie', 'Slogan affiché sur la page d''accueil',     1),
  ('email_etablissement',            'contact@edunova.dz','Email officiel de l''établissement',                         1),
  ('telephone_etablissement',        '+213 XX XX XX XX',  'Numéro de téléphone officiel',                               1),
  ('adresse_etablissement',          'Algérie',           'Adresse physique',                                           1),
  ('facebook_etablissement',         'https://facebook.com/edunova', 'Page Facebook officielle',                        1),
  ('latitude_etablissement',         '36.7372',           'Coordonnée GPS latitude (pour carte)',                       1),
  ('longitude_etablissement',        '3.0865',            'Coordonnée GPS longitude (pour carte)',                      1),
  ('seuil_passage',                  '10.00',             'Moyenne annuelle minimale pour passage en année supérieure', 1),
  ('seuil_exclusion_absences',       '10',                'Nb absences non justifiées déclenchant l''exclusion auto',   1),
  ('delai_justification_heures',     '48',                'Délai max (heures) pour qu''un parent justifie une absence', 1),
  ('coeff_devoir1',                  '1',                 'Coefficient Devoir 1 dans le calcul de la moyenne matière',  1),
  ('coeff_devoir2',                  '1',                 'Coefficient Devoir 2 dans le calcul de la moyenne matière',  1),
  ('coeff_examen',                   '2',                 'Coefficient Examen dans le calcul de la moyenne matière',    1),
  ('coeff_evaluation_continue',      '1',                 'Coefficient Évaluation Continue dans la moyenne matière',    1),
  ('annee_scolaire_active_id',       '0',                 'ID de l''année scolaire actuellement en cours',             1),
  ('version_schema',                 '2.0.0',             'Version du schéma de base de données',                       0);

CREATE TABLE IF NOT EXISTS utilisateurs (
    id                      INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    username                VARCHAR(100)    NOT NULL UNIQUE,
    password_hash           VARCHAR(255)    NOT NULL,
    email                   VARCHAR(191)    UNIQUE,
    role                    ENUM('etudiant','professeur','parent','admin') NOT NULL,
    preference_langue       ENUM('ar','fr','en') NOT NULL DEFAULT 'fr',
    est_actif               TINYINT(1)      NOT NULL DEFAULT 1,
    derniere_connexion      DATETIME,
    token_reinitialisation  VARCHAR(255),
    token_expiration        DATETIME,
    email_verifie           TINYINT(1)      NOT NULL DEFAULT 0,
    tentatives_connexion    TINYINT UNSIGNED NOT NULL DEFAULT 0,
    compte_bloque_jusqu     DATETIME,
    created_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_role          (role),
    INDEX idx_actif         (est_actif)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS annees_scolaires (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    label           VARCHAR(20)     NOT NULL UNIQUE,
    annee_debut     YEAR            NOT NULL,
    annee_fin       YEAR            NOT NULL,
    date_debut      DATE,
    date_fin        DATE,
    est_active      TINYINT(1)      NOT NULL DEFAULT 0,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_annees CHECK (annee_fin = annee_debut + 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS semestres (
    id                  INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    annee_scolaire_id   INT UNSIGNED    NOT NULL,
    numero              TINYINT UNSIGNED NOT NULL,
    date_debut          DATE            NOT NULL,
    date_fin            DATE            NOT NULL,
    est_actif           TINYINT(1)      NOT NULL DEFAULT 0,
    notes_cloturees     TINYINT(1)      NOT NULL DEFAULT 0,
    CONSTRAINT fk_sem_annee FOREIGN KEY (annee_scolaire_id) REFERENCES annees_scolaires(id) ON DELETE RESTRICT,
    UNIQUE KEY uk_annee_sem (annee_scolaire_id, numero),
    CONSTRAINT chk_sem_num CHECK (numero IN (1, 2))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS niveaux (
    id          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    nom         VARCHAR(100)    NOT NULL,
    nom_ar      VARCHAR(100),
    nom_en      VARCHAR(100),
    ordre       TINYINT UNSIGNED NOT NULL,
    description TEXT,
    est_actif   TINYINT(1)      NOT NULL DEFAULT 1,
    created_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ordre (ordre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS specialites (
    id          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    code        VARCHAR(20)     NOT NULL UNIQUE,
    nom         VARCHAR(150)    NOT NULL,
    nom_ar      VARCHAR(150),
    nom_en      VARCHAR(150),
    description TEXT,
    est_active  TINYINT(1)      NOT NULL DEFAULT 1,
    created_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sections (
    id                  INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    code_section        VARCHAR(10)     NOT NULL,
    specialite_id       INT UNSIGNED    NOT NULL,
    niveau_id           INT UNSIGNED    NOT NULL,
    annee_scolaire_id   INT UNSIGNED    NOT NULL,
    capacite_max        TINYINT UNSIGNED NOT NULL DEFAULT 35,
    est_active          TINYINT(1)      NOT NULL DEFAULT 1,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sec_spe   FOREIGN KEY (specialite_id)     REFERENCES specialites(id)      ON DELETE RESTRICT,
    CONSTRAINT fk_sec_niv   FOREIGN KEY (niveau_id)         REFERENCES niveaux(id)          ON DELETE RESTRICT,
    CONSTRAINT fk_sec_an    FOREIGN KEY (annee_scolaire_id) REFERENCES annees_scolaires(id) ON DELETE RESTRICT,
    UNIQUE KEY uk_section (specialite_id, niveau_id, annee_scolaire_id, code_section),
    INDEX idx_sec_annee (annee_scolaire_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS matieres (
    id          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    code        VARCHAR(20)     NOT NULL UNIQUE,
    nom         VARCHAR(150)    NOT NULL,
    nom_ar      VARCHAR(150),
    nom_en      VARCHAR(150),
    description TEXT,
    est_active  TINYINT(1)      NOT NULL DEFAULT 1,
    created_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS programme (
    id                      INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    matiere_id              INT UNSIGNED    NOT NULL,
    specialite_id           INT UNSIGNED    NOT NULL,
    niveau_id               INT UNSIGNED    NOT NULL,
    semestre_numero         TINYINT UNSIGNED NOT NULL,
    coefficient             TINYINT UNSIGNED NOT NULL DEFAULT 1,
    type_matiere            ENUM('principale','secondaire') NOT NULL DEFAULT 'principale',
    volume_horaire_hebdo    DECIMAL(4,1),
    est_actif               TINYINT(1)      NOT NULL DEFAULT 1,
    CONSTRAINT fk_prog_mat  FOREIGN KEY (matiere_id)    REFERENCES matieres(id)    ON DELETE RESTRICT,
    CONSTRAINT fk_prog_spe  FOREIGN KEY (specialite_id) REFERENCES specialites(id) ON DELETE RESTRICT,
    CONSTRAINT fk_prog_niv  FOREIGN KEY (niveau_id)     REFERENCES niveaux(id)     ON DELETE RESTRICT,
    UNIQUE KEY uk_programme (matiere_id, specialite_id, niveau_id, semestre_numero),
    CONSTRAINT chk_prog_sem CHECK (semestre_numero IN (1, 2)),
    CONSTRAINT chk_coeff    CHECK (coefficient BETWEEN 1 AND 10)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS administrateurs (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    utilisateur_id  INT UNSIGNED    NOT NULL UNIQUE,
    nom             VARCHAR(100)    NOT NULL,
    prenom          VARCHAR(100)    NOT NULL,
    telephone       VARCHAR(20),
    photo_url       VARCHAR(500),
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_admin_usr FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS professeurs (
    id                      INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    utilisateur_id          INT UNSIGNED    NOT NULL UNIQUE,
    matricule               VARCHAR(50)     NOT NULL UNIQUE,
    nom                     VARCHAR(100)    NOT NULL,
    prenom                  VARCHAR(100)    NOT NULL,
    date_naissance          DATE,
    lieu_naissance          VARCHAR(150),
    email_professionnel     VARCHAR(191),
    telephone               VARCHAR(20),
    photo_url               VARCHAR(500),
    date_recrutement        DATE,
    grade                   VARCHAR(100),
    specialite_id           INT UNSIGNED    NULL,
    est_actif               TINYINT(1)      NOT NULL DEFAULT 1,
    created_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_prof_usr  FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
    CONSTRAINT fk_prof_spe  FOREIGN KEY (specialite_id) REFERENCES specialites(id) ON DELETE SET NULL,
    INDEX idx_prof_mat      (matricule),
    INDEX idx_prof_spe      (specialite_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS etudiants (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    utilisateur_id  INT UNSIGNED    NOT NULL UNIQUE,
    matricule       VARCHAR(50)     NOT NULL UNIQUE,
    nom             VARCHAR(100)    NOT NULL,
    prenom          VARCHAR(100)    NOT NULL,
    date_naissance  DATE,
    sexe            ENUM('M','F'),
    lieu_naissance  VARCHAR(150),
    adresse         TEXT,
    telephone       VARCHAR(20),
    photo_url       VARCHAR(500),
    est_actif       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_etu_usr   FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
    INDEX idx_etu_mat       (matricule)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS parents (
    id                              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    utilisateur_id                  INT UNSIGNED    NOT NULL UNIQUE,
    nom                             VARCHAR(100)    NOT NULL,
    prenom                          VARCHAR(100)    NOT NULL,
    email                           VARCHAR(191)    NOT NULL UNIQUE,
    telephone                       VARCHAR(20),
    adresse                         TEXT,
    profession                      VARCHAR(150),
    statut_emploi                   ENUM('employe','sans_emploi','retraite','autre'),
    photo_url                       VARCHAR(500),
    email_verifie                   TINYINT(1)      NOT NULL DEFAULT 0,
    token_verification_email        VARCHAR(255),
    token_email_expiration          DATETIME,
    created_at                      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at                      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_par_usr   FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
    INDEX idx_par_email     (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS demandes_inscription_parent (
    id                  INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    nom                 VARCHAR(100)    NOT NULL,
    prenom              VARCHAR(100)    NOT NULL,
    email               VARCHAR(191)    NOT NULL UNIQUE,
    telephone           VARCHAR(20),
    adresse             TEXT,
    profession          VARCHAR(150),
    lien_parente        ENUM('pere','mere','tuteur','tutrice','autre') NOT NULL DEFAULT 'tuteur',
    matricule_etudiant  VARCHAR(50),
    statut              ENUM('en_attente','approuvee','rejetee') NOT NULL DEFAULT 'en_attente',
    motif_rejet         TEXT,
    traite_par          INT UNSIGNED,
    date_traitement     DATETIME,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dem_admin FOREIGN KEY (traite_par) REFERENCES administrateurs(id) ON DELETE SET NULL,
    INDEX idx_dem_statut    (statut)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS parent_etudiant (
    id                          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    parent_id                   INT UNSIGNED    NOT NULL,
    etudiant_id                 INT UNSIGNED    NOT NULL,
    lien                        ENUM('pere','mere','tuteur','tutrice','autre') NOT NULL DEFAULT 'tuteur',
    est_responsable_principal   TINYINT(1)      NOT NULL DEFAULT 1,
    peut_consulter_notes        TINYINT(1)      NOT NULL DEFAULT 1,
    peut_recevoir_notifications TINYINT(1)      NOT NULL DEFAULT 1,
    CONSTRAINT fk_pe_par    FOREIGN KEY (parent_id)   REFERENCES parents(id)   ON DELETE CASCADE,
    CONSTRAINT fk_pe_etu    FOREIGN KEY (etudiant_id) REFERENCES etudiants(id) ON DELETE CASCADE,
    UNIQUE KEY uk_par_etu   (parent_id, etudiant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS inscriptions (
    id                  INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    etudiant_id         INT UNSIGNED    NOT NULL,
    section_id          INT UNSIGNED    NOT NULL,
    annee_scolaire_id   INT UNSIGNED    NOT NULL,
    date_inscription    DATE            NOT NULL,
    semestre_courant    TINYINT UNSIGNED NOT NULL DEFAULT 1,
    statut              ENUM('actif','exclu','transfere','diplome') NOT NULL DEFAULT 'actif',
    date_fin            DATE,
    motif_fin           TEXT,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_ins_etu   FOREIGN KEY (etudiant_id)       REFERENCES etudiants(id)        ON DELETE RESTRICT,
    CONSTRAINT fk_ins_sec   FOREIGN KEY (section_id)        REFERENCES sections(id)         ON DELETE RESTRICT,
    CONSTRAINT fk_ins_an    FOREIGN KEY (annee_scolaire_id) REFERENCES annees_scolaires(id) ON DELETE RESTRICT,
    UNIQUE KEY uk_ins           (etudiant_id, annee_scolaire_id),
    INDEX idx_ins_section       (section_id),
    INDEX idx_ins_statut        (statut),
    CONSTRAINT chk_ins_sem  CHECK (semestre_courant IN (1, 2))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS affectations_enseignement (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    professeur_id   INT UNSIGNED    NOT NULL,
    matiere_id      INT UNSIGNED    NOT NULL,
    section_id      INT UNSIGNED    NOT NULL,
    semestre_id     INT UNSIGNED    NOT NULL,
    date_affectation DATE,
    est_active      TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_aff_prof  FOREIGN KEY (professeur_id) REFERENCES professeurs(id) ON DELETE RESTRICT,
    CONSTRAINT fk_aff_mat   FOREIGN KEY (matiere_id)    REFERENCES matieres(id)    ON DELETE RESTRICT,
    CONSTRAINT fk_aff_sec   FOREIGN KEY (section_id)    REFERENCES sections(id)    ON DELETE RESTRICT,
    CONSTRAINT fk_aff_sem   FOREIGN KEY (semestre_id)   REFERENCES semestres(id)   ON DELETE RESTRICT,
    UNIQUE KEY uk_affectation   (matiere_id, section_id, semestre_id),
    INDEX idx_aff_prof_sem      (professeur_id, semestre_id),
    INDEX idx_aff_sec_sem       (section_id, semestre_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS notes (
    id                      INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    etudiant_id             INT UNSIGNED    NOT NULL,
    affectation_id          INT UNSIGNED    NOT NULL,
    devoir1                 DECIMAL(5,2),
    devoir2                 DECIMAL(5,2),
    examen                  DECIMAL(5,2),
    evaluation_continue     DECIMAL(5,2),
    moyenne                 DECIMAL(5,2),
    saisie_par              INT UNSIGNED    NOT NULL,
    date_saisie             TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    est_validee             TINYINT(1)      NOT NULL DEFAULT 0,
    date_validation         DATETIME,
    validee_par             INT UNSIGNED,
    observations            TEXT,
    CONSTRAINT fk_note_etu   FOREIGN KEY (etudiant_id)    REFERENCES etudiants(id)                 ON DELETE RESTRICT,
    CONSTRAINT fk_note_aff   FOREIGN KEY (affectation_id) REFERENCES affectations_enseignement(id) ON DELETE RESTRICT,
    CONSTRAINT fk_note_prof  FOREIGN KEY (saisie_par)     REFERENCES professeurs(id)               ON DELETE RESTRICT,
    CONSTRAINT fk_note_admin FOREIGN KEY (validee_par)    REFERENCES administrateurs(id)           ON DELETE SET NULL,
    UNIQUE KEY uk_note       (etudiant_id, affectation_id),
    INDEX idx_note_aff       (affectation_id),
    CONSTRAINT chk_d1   CHECK (devoir1             IS NULL OR devoir1             BETWEEN 0 AND 20),
    CONSTRAINT chk_d2   CHECK (devoir2             IS NULL OR devoir2             BETWEEN 0 AND 20),
    CONSTRAINT chk_ex   CHECK (examen              IS NULL OR examen              BETWEEN 0 AND 20),
    CONSTRAINT chk_tc   CHECK (evaluation_continue IS NULL OR evaluation_continue BETWEEN 0 AND 20),
    CONSTRAINT chk_moy  CHECK (moyenne             IS NULL OR moyenne             BETWEEN 0 AND 20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS resultats_semestre (
    id                  INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    etudiant_id         INT UNSIGNED    NOT NULL,
    inscription_id      INT UNSIGNED    NOT NULL,
    semestre_id         INT UNSIGNED    NOT NULL,
    moyenne_generale    DECIMAL(5,2),
    rang                SMALLINT UNSIGNED,
    mention             VARCHAR(50),
    observations        TEXT,
    est_calcule         TINYINT(1)      NOT NULL DEFAULT 0,
    date_calcul         DATETIME,
    CONSTRAINT fk_rs_etu FOREIGN KEY (etudiant_id)   REFERENCES etudiants(id)    ON DELETE RESTRICT,
    CONSTRAINT fk_rs_ins FOREIGN KEY (inscription_id) REFERENCES inscriptions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_rs_sem FOREIGN KEY (semestre_id)   REFERENCES semestres(id)    ON DELETE RESTRICT,
    UNIQUE KEY uk_res_sem  (etudiant_id, inscription_id, semestre_id),
    CONSTRAINT chk_rs_moy  CHECK (moyenne_generale IS NULL OR moyenne_generale BETWEEN 0 AND 20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS resultats_annuels (
    id                      INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    etudiant_id             INT UNSIGNED    NOT NULL,
    inscription_id          INT UNSIGNED    NOT NULL,
    annee_scolaire_id       INT UNSIGNED    NOT NULL,
    moyenne_s1              DECIMAL(5,2),
    moyenne_s2              DECIMAL(5,2),
    moyenne_annuelle        DECIMAL(5,2),
    rang_annuel             SMALLINT UNSIGNED,
    decision                ENUM('en_attente','admis','redoublant','exclu','diplome') NOT NULL DEFAULT 'en_attente',
    mention                 VARCHAR(50),
    observations            TEXT,
    est_calcule             TINYINT(1)      NOT NULL DEFAULT 0,
    date_calcul             DATETIME,
    prochaine_section_id    INT UNSIGNED,
    CONSTRAINT fk_ra_etu FOREIGN KEY (etudiant_id)          REFERENCES etudiants(id)        ON DELETE RESTRICT,
    CONSTRAINT fk_ra_ins FOREIGN KEY (inscription_id)       REFERENCES inscriptions(id)     ON DELETE RESTRICT,
    CONSTRAINT fk_ra_an  FOREIGN KEY (annee_scolaire_id)    REFERENCES annees_scolaires(id) ON DELETE RESTRICT,
    CONSTRAINT fk_ra_sec FOREIGN KEY (prochaine_section_id) REFERENCES sections(id)         ON DELETE SET NULL,
    UNIQUE KEY uk_res_an  (etudiant_id, annee_scolaire_id),
    CONSTRAINT chk_ra_s1  CHECK (moyenne_s1       IS NULL OR moyenne_s1       BETWEEN 0 AND 20),
    CONSTRAINT chk_ra_s2  CHECK (moyenne_s2       IS NULL OR moyenne_s2       BETWEEN 0 AND 20),
    CONSTRAINT chk_ra_an  CHECK (moyenne_annuelle IS NULL OR moyenne_annuelle BETWEEN 0 AND 20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS releves_notes (
    id                  INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    etudiant_id         INT UNSIGNED    NOT NULL,
    annee_scolaire_id   INT UNSIGNED    NOT NULL,
    semestre_id         INT UNSIGNED,
    type                ENUM('semestre','annuel') NOT NULL,
    fichier_url         VARCHAR(500)    NOT NULL,
    nom_fichier         VARCHAR(255),
    taille_fichier_ko   INT UNSIGNED,
    qr_code_token       VARCHAR(64)     UNIQUE,
    qr_code_image_url   VARCHAR(500),
    genere_par          INT UNSIGNED,
    date_generation     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_rn_etu   FOREIGN KEY (etudiant_id)       REFERENCES etudiants(id)        ON DELETE RESTRICT,
    CONSTRAINT fk_rn_an    FOREIGN KEY (annee_scolaire_id) REFERENCES annees_scolaires(id) ON DELETE RESTRICT,
    CONSTRAINT fk_rn_sem   FOREIGN KEY (semestre_id)       REFERENCES semestres(id)        ON DELETE SET NULL,
    CONSTRAINT fk_rn_admin FOREIGN KEY (genere_par)        REFERENCES administrateurs(id)  ON DELETE SET NULL,
    INDEX idx_rn_etu_an    (etudiant_id, annee_scolaire_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS seances (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    affectation_id  INT UNSIGNED    NOT NULL,
    date_seance     DATE            NOT NULL,
    heure_debut     TIME            NOT NULL,
    heure_fin       TIME            NOT NULL,
    type_seance     ENUM('cours','td','tp','examen','rattrapage') NOT NULL DEFAULT 'cours',
    salle           VARCHAR(50),
    est_annulee     TINYINT(1)      NOT NULL DEFAULT 0,
    motif_annulation VARCHAR(255),
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sea_aff   FOREIGN KEY (affectation_id) REFERENCES affectations_enseignement(id) ON DELETE RESTRICT,
    INDEX idx_sea_aff_date  (affectation_id, date_seance)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS presences (
    id                      INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    seance_id               INT UNSIGNED    NOT NULL,
    etudiant_id             INT UNSIGNED    NOT NULL,
    statut                  ENUM('present','absent','retard','excuse') NOT NULL DEFAULT 'present',
    justification           TEXT,
    fichier_justification   VARCHAR(500),
    justifie_par_parent_id  INT UNSIGNED,
    date_justification      DATETIME,
    statut_justification    ENUM('en_attente','acceptee','refusee') DEFAULT NULL,
    traite_par_admin_id     INT UNSIGNED,
    date_traitement         DATETIME,
    enregistre_par          INT UNSIGNED    NOT NULL,
    date_enregistrement     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pre_sea   FOREIGN KEY (seance_id)              REFERENCES seances(id)         ON DELETE RESTRICT,
    CONSTRAINT fk_pre_etu   FOREIGN KEY (etudiant_id)            REFERENCES etudiants(id)        ON DELETE RESTRICT,
    CONSTRAINT fk_pre_par   FOREIGN KEY (justifie_par_parent_id) REFERENCES parents(id)          ON DELETE SET NULL,
    CONSTRAINT fk_pre_prof  FOREIGN KEY (enregistre_par)         REFERENCES professeurs(id)      ON DELETE RESTRICT,
    CONSTRAINT fk_pre_adm   FOREIGN KEY (traite_par_admin_id)    REFERENCES administrateurs(id)  ON DELETE SET NULL,
    UNIQUE KEY uk_presence      (seance_id, etudiant_id),
    INDEX idx_pre_etu_statut    (etudiant_id, statut),
    INDEX idx_pre_justif        (statut_justification)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS compteur_absences (
    id                          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    etudiant_id                 INT UNSIGNED    NOT NULL,
    inscription_id              INT UNSIGNED    NOT NULL,
    semestre_id                 INT UNSIGNED    NOT NULL,
    total_seances               INT UNSIGNED    NOT NULL DEFAULT 0,
    total_absences              INT UNSIGNED    NOT NULL DEFAULT 0,
    absences_justifiees         INT UNSIGNED    NOT NULL DEFAULT 0,
    absences_non_justifiees     INT UNSIGNED    NOT NULL DEFAULT 0,
    est_exclu                   TINYINT(1)      NOT NULL DEFAULT 0,
    date_exclusion              DATETIME,
    updated_at                  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_ca_etu FOREIGN KEY (etudiant_id)   REFERENCES etudiants(id)    ON DELETE RESTRICT,
    CONSTRAINT fk_ca_ins FOREIGN KEY (inscription_id) REFERENCES inscriptions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_ca_sem FOREIGN KEY (semestre_id)   REFERENCES semestres(id)    ON DELETE RESTRICT,
    UNIQUE KEY uk_compteur (etudiant_id, inscription_id, semestre_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS notifications (
    id                  INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    type                ENUM(
                            'absence_enregistree','absence_justifiee','absence_refusee',
                            'seuil_absences_atteint','exclusion_absences','note_publiee',
                            'devoir_publie','cours_publie','correction_publiee','message_recu',
                            'annonce','post_publie','commentaire_recu','releve_disponible',
                            'mot_de_passe_envoye','autre'
                        ) NOT NULL,
    destinataire_id     INT UNSIGNED    NOT NULL,
    destinataire_role   ENUM('etudiant','professeur','parent','admin') NOT NULL,
    titre               VARCHAR(255)    NOT NULL,
    contenu             TEXT            NOT NULL,
    est_lu              TINYINT(1)      NOT NULL DEFAULT 0,
    date_lecture        DATETIME,
    reference_table     VARCHAR(50),
    reference_id        INT UNSIGNED,
    date_envoi          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_notif_dest (destinataire_id, destinataire_role, est_lu),
    INDEX idx_notif_type (type),
    INDEX idx_notif_date (date_envoi)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS corrections_examens (
    id                      INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    affectation_id          INT UNSIGNED    NOT NULL,
    type_evaluation         ENUM('devoir1','devoir2','examen','evaluation_continue') NOT NULL,
    titre                   VARCHAR(255)    NOT NULL,
    description             TEXT,
    fichier_url             VARCHAR(500)    NOT NULL,
    type_fichier            ENUM('pdf','word','image','autre') NOT NULL,
    nom_fichier_original    VARCHAR(255),
    taille_fichier_ko       INT UNSIGNED,
    est_publie              TINYINT(1)      NOT NULL DEFAULT 0,
    date_publication        DATETIME,
    publie_par              INT UNSIGNED    NOT NULL,
    created_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_ce_aff  FOREIGN KEY (affectation_id) REFERENCES affectations_enseignement(id) ON DELETE RESTRICT,
    CONSTRAINT fk_ce_prof FOREIGN KEY (publie_par)     REFERENCES professeurs(id)               ON DELETE RESTRICT,
    INDEX idx_ce_aff_type  (affectation_id, type_evaluation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cours (
    id                      INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    affectation_id          INT UNSIGNED    NOT NULL,
    titre                   VARCHAR(255)    NOT NULL,
    description             TEXT,
    type_contenu            ENUM('pdf','image','video','audio','lien_externe') NOT NULL,
    fichier_url             VARCHAR(500),
    nom_fichier_original    VARCHAR(255),
    taille_fichier_ko       BIGINT UNSIGNED,
    ordre                   SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    est_publie              TINYINT(1)      NOT NULL DEFAULT 0,
    date_publication        DATETIME,
    publie_par              INT UNSIGNED    NOT NULL,
    created_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_crs_aff  FOREIGN KEY (affectation_id) REFERENCES affectations_enseignement(id) ON DELETE RESTRICT,
    CONSTRAINT fk_crs_prof FOREIGN KEY (publie_par)     REFERENCES professeurs(id)               ON DELETE RESTRICT,
    INDEX idx_crs_aff_pub  (affectation_id, est_publie)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cours_consultes (
    id                          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    cours_id                    INT UNSIGNED    NOT NULL,
    etudiant_id                 INT UNSIGNED    NOT NULL,
    date_premiere_consultation  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    date_derniere_consultation  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    nombre_consultations        INT UNSIGNED    NOT NULL DEFAULT 1,
    CONSTRAINT fk_cc_crs FOREIGN KEY (cours_id)    REFERENCES cours(id)     ON DELETE CASCADE,
    CONSTRAINT fk_cc_etu FOREIGN KEY (etudiant_id) REFERENCES etudiants(id) ON DELETE CASCADE,
    UNIQUE KEY uk_consultation (cours_id, etudiant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS devoirs (
    id                          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    affectation_id              INT UNSIGNED    NOT NULL,
    titre                       VARCHAR(255)    NOT NULL,
    description                 TEXT            NOT NULL,
    fichier_url                 VARCHAR(500),
    type_fichier                ENUM('pdf','image','word','autre'),
    nom_fichier_original        VARCHAR(255),
    date_publication            DATETIME        NOT NULL,
    date_limite_soumission      DATETIME        NOT NULL,
    note_maximale               DECIMAL(5,2)    NOT NULL DEFAULT 20.00,
    est_publie                  TINYINT(1)      NOT NULL DEFAULT 0,
    publie_par                  INT UNSIGNED    NOT NULL,
    created_at                  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_dev_aff  FOREIGN KEY (affectation_id) REFERENCES affectations_enseignement(id) ON DELETE RESTRICT,
    CONSTRAINT fk_dev_prof FOREIGN KEY (publie_par)     REFERENCES professeurs(id)               ON DELETE RESTRICT,
    INDEX idx_dev_aff_date (affectation_id, date_limite_soumission)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS soumissions_devoirs (
    id                      INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    devoir_id               INT UNSIGNED    NOT NULL,
    etudiant_id             INT UNSIGNED    NOT NULL,
    fichier_url             VARCHAR(500)    NOT NULL,
    type_fichier            ENUM('pdf','word','image','autre') NOT NULL,
    nom_fichier_original    VARCHAR(255),
    taille_fichier_ko       BIGINT UNSIGNED,
    date_soumission         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    est_en_retard           TINYINT(1)      NOT NULL DEFAULT 0,
    note                    DECIMAL(5,2),
    commentaire_prof        TEXT,
    date_correction         DATETIME,
    corrige_par             INT UNSIGNED,
    CONSTRAINT fk_sd_dev  FOREIGN KEY (devoir_id)   REFERENCES devoirs(id)     ON DELETE RESTRICT,
    CONSTRAINT fk_sd_etu  FOREIGN KEY (etudiant_id) REFERENCES etudiants(id)   ON DELETE RESTRICT,
    CONSTRAINT fk_sd_prof FOREIGN KEY (corrige_par) REFERENCES professeurs(id) ON DELETE SET NULL,
    UNIQUE KEY uk_soumission (devoir_id, etudiant_id),
    CONSTRAINT chk_sd_note CHECK (note IS NULL OR note BETWEEN 0 AND 20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS conversations (
    id                      INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    type                    ENUM('etudiant_professeur','parent_professeur','cours_etudiant_professeur') NOT NULL,
    participant_a_id        INT UNSIGNED    NOT NULL,
    participant_a_role      ENUM('etudiant','parent') NOT NULL,
    participant_b_id        INT UNSIGNED    NOT NULL,
    sujet                   VARCHAR(255),
    matiere_id              INT UNSIGNED,
    etudiant_concerne_id    INT UNSIGNED,
    cours_id                INT UNSIGNED    NULL,
    est_active              TINYINT(1)      NOT NULL DEFAULT 1,
    date_creation           TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    date_dernier_message    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_conv_mat   FOREIGN KEY (matiere_id)           REFERENCES matieres(id)   ON DELETE SET NULL,
    CONSTRAINT fk_conv_etu   FOREIGN KEY (etudiant_concerne_id) REFERENCES etudiants(id)  ON DELETE SET NULL,
    CONSTRAINT fk_conv_cours FOREIGN KEY (cours_id)             REFERENCES cours(id)       ON DELETE SET NULL,
    INDEX idx_conv_a     (participant_a_id, participant_a_role),
    INDEX idx_conv_b     (participant_b_id),
    INDEX idx_conv_type  (type),
    INDEX idx_conv_cours (cours_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS messages (
    id                          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    conversation_id             INT UNSIGNED    NOT NULL,
    expediteur_utilisateur_id   INT UNSIGNED    NOT NULL,
    expediteur_role             ENUM('etudiant','professeur','parent') NOT NULL,
    contenu                     TEXT            NOT NULL,
    fichier_url                 VARCHAR(500),
    type_fichier                ENUM('pdf','image','audio','video','autre'),
    est_lu                      TINYINT(1)      NOT NULL DEFAULT 0,
    date_lecture                DATETIME,
    date_envoi                  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    supprime_par_expediteur     TINYINT(1)      NOT NULL DEFAULT 0,
    supprime_par_destinataire   TINYINT(1)      NOT NULL DEFAULT 0,
    CONSTRAINT fk_msg_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_msg_conv_date (conversation_id, date_envoi)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS annonces (
    id                  INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    admin_id            INT UNSIGNED    NOT NULL,
    titre               VARCHAR(255)    NOT NULL,
    contenu             TEXT            NOT NULL,
    public_cible        SET('tous','etudiants','professeurs','parents') NOT NULL DEFAULT 'tous',
    est_publie          TINYINT(1)      NOT NULL DEFAULT 0,
    est_epinglee        TINYINT(1)      NOT NULL DEFAULT 0,
    date_publication    DATETIME,
    date_expiration     DATETIME,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_ann_admin FOREIGN KEY (admin_id) REFERENCES administrateurs(id) ON DELETE RESTRICT,
    INDEX idx_ann_pub       (est_publie, date_publication),
    INDEX idx_ann_epingle   (est_epinglee, date_publication)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS annonces_fichiers (
    id          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    annonce_id  INT UNSIGNED    NOT NULL,
    fichier_url VARCHAR(500)    NOT NULL,
    nom_fichier VARCHAR(255),
    type_fichier ENUM('pdf','image','word','video','autre'),
    CONSTRAINT fk_af_ann FOREIGN KEY (annonce_id) REFERENCES annonces(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS calendrier_examens (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    section_id      INT UNSIGNED    NOT NULL,
    matiere_id      INT UNSIGNED    NOT NULL,
    semestre_id     INT UNSIGNED    NOT NULL,
    type_examen     ENUM('devoir1','devoir2','examen','rattrapage','evaluation_continue') NOT NULL,
    date_examen     DATE            NOT NULL,
    heure_debut     TIME            NOT NULL,
    heure_fin       TIME            NOT NULL,
    salle           VARCHAR(100),
    surveillants    TEXT,
    est_publie      TINYINT(1)      NOT NULL DEFAULT 0,
    publie_par      INT UNSIGNED    NOT NULL,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_cal_sec   FOREIGN KEY (section_id)  REFERENCES sections(id)         ON DELETE RESTRICT,
    CONSTRAINT fk_cal_mat   FOREIGN KEY (matiere_id)  REFERENCES matieres(id)         ON DELETE RESTRICT,
    CONSTRAINT fk_cal_sem   FOREIGN KEY (semestre_id) REFERENCES semestres(id)        ON DELETE RESTRICT,
    CONSTRAINT fk_cal_admin FOREIGN KEY (publie_par)  REFERENCES administrateurs(id)  ON DELETE RESTRICT,
    INDEX idx_cal_sec_sem   (section_id, semestre_id),
    INDEX idx_cal_date      (date_examen)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS emploi_du_temps (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    section_id      INT UNSIGNED    NOT NULL,
    affectation_id  INT UNSIGNED    NOT NULL,
    semestre_id     INT UNSIGNED    NOT NULL,
    jour_semaine    TINYINT UNSIGNED NOT NULL,
    heure_debut     TIME            NOT NULL,
    heure_fin       TIME            NOT NULL,
    salle           VARCHAR(100),
    type_seance     ENUM('cours','td','tp') NOT NULL DEFAULT 'cours',
    est_actif       TINYINT(1)      NOT NULL DEFAULT 1,
    publie_par      INT UNSIGNED,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_edt_sec   FOREIGN KEY (section_id)     REFERENCES sections(id)                   ON DELETE RESTRICT,
    CONSTRAINT fk_edt_aff   FOREIGN KEY (affectation_id) REFERENCES affectations_enseignement(id)  ON DELETE RESTRICT,
    CONSTRAINT fk_edt_sem   FOREIGN KEY (semestre_id)    REFERENCES semestres(id)                  ON DELETE RESTRICT,
    CONSTRAINT fk_edt_admin FOREIGN KEY (publie_par)     REFERENCES administrateurs(id)            ON DELETE SET NULL,
    INDEX idx_edt_sec_jour  (section_id, jour_semaine),
    CONSTRAINT chk_edt_jour CHECK (jour_semaine BETWEEN 0 AND 6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS journal_connexions (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    utilisateur_id  INT UNSIGNED    NOT NULL,
    adresse_ip      VARCHAR(45),
    user_agent      VARCHAR(500),
    statut          ENUM('succes','echec','bloque') NOT NULL DEFAULT 'succes',
    date_connexion  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_jc_usr_date  (utilisateur_id, date_connexion),
    INDEX idx_jc_statut    (statut)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS journal_admin (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    admin_id            INT UNSIGNED    NOT NULL,
    action              VARCHAR(100)    NOT NULL,
    table_affectee      VARCHAR(100),
    enregistrement_id   INT UNSIGNED,
    details_avant       JSON,
    details_apres       JSON,
    adresse_ip          VARCHAR(45),
    date_action         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ja_admin FOREIGN KEY (admin_id) REFERENCES administrateurs(id) ON DELETE RESTRICT,
    INDEX idx_ja_admin_date (admin_id, date_action),
    INDEX idx_ja_table      (table_affectee)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS push_tokens (
    id                          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    utilisateur_id              INT UNSIGNED    NOT NULL,
    token                       VARCHAR(512)    NOT NULL,
    type_token                  ENUM('fcm','webpush','email') NOT NULL DEFAULT 'webpush',
    appareil                    VARCHAR(150),
    est_actif                   TINYINT(1)      NOT NULL DEFAULT 1,
    date_enregistrement         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    date_derniere_utilisation   TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_token         (token),
    INDEX idx_push_usr_actif    (utilisateur_id, est_actif),
    CONSTRAINT fk_pt_usr FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS file_notifications_externes (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    utilisateur_id      INT UNSIGNED    NOT NULL,
    canal               ENUM('push','email','push_et_email') NOT NULL DEFAULT 'push',
    titre               VARCHAR(255)    NOT NULL,
    corps               TEXT            NOT NULL,
    url_action          VARCHAR(500),
    icone               VARCHAR(100),
    declencheur         ENUM(
                            'nouveau_message','absence_enregistree','absence_justifiee',
                            'absence_refusee','note_publiee','devoir_publie',
                            'cours_publie','correction_publiee','releve_disponible',
                            'mot_de_passe_envoye','seuil_absences_atteint',
                            'exclusion','annonce','post_publie','commentaire_recu','autre'
                        ) NOT NULL DEFAULT 'nouveau_message',
    reference_table     VARCHAR(60),
    reference_id        BIGINT UNSIGNED,
    statut              ENUM('en_attente','envoyee','echec','ignoree') NOT NULL DEFAULT 'en_attente',
    tentatives          TINYINT UNSIGNED NOT NULL DEFAULT 0,
    derniere_tentative  DATETIME,
    erreur_detail       TEXT,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    traitee_le          DATETIME,
    CONSTRAINT fk_fne_usr FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
    INDEX idx_fne_statut_date  (statut, created_at),
    INDEX idx_fne_usr          (utilisateur_id, statut)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS messages_accuse_reception (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    message_id      INT UNSIGNED    NOT NULL,
    utilisateur_id  INT UNSIGNED    NOT NULL,
    date_lecture    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    appareil        VARCHAR(150),
    UNIQUE KEY uk_ar (message_id, utilisateur_id),
    CONSTRAINT fk_ar_msg FOREIGN KEY (message_id)    REFERENCES messages(id)      ON DELETE CASCADE,
    CONSTRAINT fk_ar_usr FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS statut_connexion (
    utilisateur_id  INT UNSIGNED    PRIMARY KEY,
    est_en_ligne    TINYINT(1)      NOT NULL DEFAULT 0,
    derniere_activite TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    socket_id       VARCHAR(100),
    CONSTRAINT fk_sc_usr FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS posts_professeur (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    professeur_id   INT UNSIGNED    NOT NULL,
    affectation_id  INT UNSIGNED    NULL,
    contenu         TEXT            NOT NULL,
    type_public     ENUM('section','tous') NOT NULL DEFAULT 'tous',
    est_publie      TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_pp_prof FOREIGN KEY (professeur_id)  REFERENCES professeurs(id)                ON DELETE CASCADE,
    CONSTRAINT fk_pp_aff  FOREIGN KEY (affectation_id) REFERENCES affectations_enseignement(id)  ON DELETE SET NULL,
    INDEX idx_pp_prof      (professeur_id, est_publie, created_at),
    INDEX idx_pp_aff       (affectation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS commentaires_posts (
    id          INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    post_id     INT UNSIGNED    NOT NULL,
    auteur_id   INT UNSIGNED    NOT NULL,
    auteur_role ENUM('etudiant','professeur') NOT NULL,
    contenu     TEXT            NOT NULL,
    created_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cp_post FOREIGN KEY (post_id) REFERENCES posts_professeur(id) ON DELETE CASCADE,
    INDEX idx_cp_post       (post_id, created_at),
    INDEX idx_cp_auteur     (auteur_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pdfs_emplois_temps (
    id              INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    specialite_id   INT UNSIGNED    NOT NULL,
    semestre_id     INT UNSIGNED    NOT NULL,
    type_pdf        ENUM('hebdomadaire','examens') NOT NULL,
    fichier_url     VARCHAR(500)    NOT NULL,
    nom_fichier     VARCHAR(255)    NOT NULL,
    taille_fichier_ko INT UNSIGNED,
    genere_par      INT UNSIGNED    NOT NULL,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_pdf_edt   (specialite_id, semestre_id, type_pdf),
    CONSTRAINT fk_pedt_spe  FOREIGN KEY (specialite_id) REFERENCES specialites(id)      ON DELETE CASCADE,
    CONSTRAINT fk_pedt_sem  FOREIGN KEY (semestre_id)   REFERENCES semestres(id)        ON DELETE CASCADE,
    CONSTRAINT fk_pedt_adm  FOREIGN KEY (genere_par)    REFERENCES administrateurs(id)  ON DELETE RESTRICT,
    INDEX idx_pedt_spe_sem  (specialite_id, semestre_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
