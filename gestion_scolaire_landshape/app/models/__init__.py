# =============================================================
#  EduNova — models/__init__.py
#  Import centralisé de tous les modèles
# =============================================================
from app.models.user          import Utilisateur
from app.models.academic      import AnneeScolaire, Semestre, Niveau, Specialite, Section
from app.models.profiles      import Administrateur, Professeur, Etudiant, Parent, ParentEtudiant, DemandeInscriptionParent
from app.models.program       import Matiere, Programme, Inscription, AffectationEnseignement
from app.models.evaluation    import Note, ResultatSemestre, ResultatAnnuel, ReleverNotes, CorrectionExamen
from app.models.presence      import Seance, Presence, CompteurAbsences
from app.models.communication import (Notification, Conversation, Message, Annonce, AnnonceFichier,
                                      PushToken, StatutConnexion, FileNotificationExterne)
from app.models.pedagogy      import Cours, CoursConsulte, Devoir, SoumissionDevoir, PostProfesseur, CommentairePost
from app.models.planning      import CalendrierExamen, EmploiDuTemps, PdfEmploiTemps
from app.models.audit         import JournalConnexion, JournalAdmin

__all__ = [
    'Utilisateur',
    'AnneeScolaire', 'Semestre', 'Niveau', 'Specialite', 'Section',
    'Administrateur', 'Professeur', 'Etudiant', 'Parent', 'ParentEtudiant', 'DemandeInscriptionParent',
    'Matiere', 'Programme', 'Inscription', 'AffectationEnseignement',
    'Note', 'ResultatSemestre', 'ResultatAnnuel', 'ReleverNotes', 'CorrectionExamen',
    'Seance', 'Presence', 'CompteurAbsences',
    'Notification', 'Conversation', 'Message', 'Annonce', 'AnnonceFichier',
    'PushToken', 'StatutConnexion', 'FileNotificationExterne',
    'Cours', 'CoursConsulte', 'Devoir', 'SoumissionDevoir', 'PostProfesseur', 'CommentairePost',
    'CalendrierExamen', 'EmploiDuTemps', 'PdfEmploiTemps',
    'JournalConnexion', 'JournalAdmin',
]
