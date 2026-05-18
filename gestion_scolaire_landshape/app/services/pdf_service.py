# =============================================================
#  EduNova — services/pdf_service.py
#  Génération PDF : relevés de notes + emplois du temps
# =============================================================
import io
import os
from datetime import datetime
from flask import current_app
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable, Image)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


# ── Palette EduNova ───────────────────────────────────────────
INDIGO     = colors.HexColor('#4F46E5')
CYAN       = colors.HexColor('#06B6D4')
DARK_BG    = colors.HexColor('#0A0E1A')
SLATE      = colors.HexColor('#111827')
MIST       = colors.HexColor('#E2E8F0')
ASH        = colors.HexColor('#94A3B8')
SUCCESS    = colors.HexColor('#10B981')
ALERT      = colors.HexColor('#EF4444')
GOLD       = colors.HexColor('#F59E0B')
WHITE      = colors.white
BLACK      = colors.black


def generer_releve_pdf(etudiant, annee_scolaire, notes_s1: list, notes_s2: list,
                        rs1=None, rs2=None, ra=None, qr_image_path: str = None) -> bytes:
    """
    Génère un relevé de notes complet (S1 + S2 + annuel) en PDF.
    Retourne les bytes du PDF.
    """
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=2*cm,    bottomMargin=2*cm)
    story  = []
    styles = getSampleStyleSheet()

    # ── Style personnalisé ────────────────────────────────────
    titre_style = ParagraphStyle('titre', parent=styles['Title'],
                                  fontSize=18, textColor=INDIGO,
                                  alignment=TA_CENTER, spaceAfter=4)
    sous_titre  = ParagraphStyle('sous', parent=styles['Normal'],
                                  fontSize=10, textColor=ASH,
                                  alignment=TA_CENTER, spaceAfter=2)
    section_style = ParagraphStyle('section', parent=styles['Heading2'],
                                    fontSize=12, textColor=INDIGO, spaceBefore=12, spaceAfter=6)
    cell_style    = ParagraphStyle('cell', parent=styles['Normal'], fontSize=9)

    # ── En-tête ───────────────────────────────────────────────
    story.append(Paragraph('EduNova', titre_style))
    story.append(Paragraph('Relevé de Notes Officiel', sous_titre))
    story.append(HRFlowable(width='100%', thickness=2, color=INDIGO))
    story.append(Spacer(1, 0.4*cm))

    # ── Infos étudiant ────────────────────────────────────────
    insc   = etudiant.get_inscription_active()
    spe    = insc.section.specialite.nom  if insc else '—'
    niv    = insc.section.niveau.nom      if insc else '—'
    sec    = insc.section.code_section    if insc else '—'

    info_data = [
        ['Nom & Prénom', f'{etudiant.nom} {etudiant.prenom}',
         'Matricule', etudiant.matricule],
        ['Année scolaire', annee_scolaire.label,
         'Spécialité', spe],
        ['Niveau', niv, 'Section', sec],
    ]
    info_table = Table(info_data, colWidths=[3.5*cm, 6*cm, 3*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ('FONTSIZE',        (0,0), (-1,-1), 9),
        ('FONTNAME',        (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',        (2,0), (2,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR',       (0,0), (0,-1), INDIGO),
        ('TEXTCOLOR',       (2,0), (2,-1), INDIGO),
        ('BACKGROUND',      (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID',            (0,0), (-1,-1), 0.5, ASH),
        ('ROWBACKGROUNDS',  (0,0), (-1,-1), [MIST, WHITE]),
        ('PADDING',         (0,0), (-1,-1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Tableau d'un semestre ─────────────────────────────────
    def tableau_semestre(notes: list, rs, num: int):
        story.append(Paragraph(f'Semestre {num}', section_style))
        if not notes:
            story.append(Paragraph('Aucune note disponible.', cell_style))
            return

        headers = ['Matière', 'Coeff.', 'Devoir 1', 'Devoir 2', 'Éval. Cont.', 'Examen', 'Moyenne']
        rows    = [headers]
        for item in notes:
            matiere = item.get('matiere', '—')
            coeff   = item.get('coefficient', 1)
            d1      = f"{float(item['devoir1']):.2f}"  if item.get('devoir1')  is not None else '—'
            d2      = f"{float(item['devoir2']):.2f}"  if item.get('devoir2')  is not None else '—'
            ec      = f"{float(item['eval_cont']):.2f}" if item.get('eval_cont') is not None else '—'
            ex      = f"{float(item['examen']):.2f}"   if item.get('examen')   is not None else '—'
            moy     = f"{float(item['moyenne']):.2f}"  if item.get('moyenne')  is not None else '—'
            rows.append([matiere, str(coeff), d1, d2, ec, ex, moy])

        # Ligne moyenne générale
        moy_gen = f"{float(rs.moyenne_generale):.2f}" if rs and rs.moyenne_generale else '—'
        rows.append(['Moyenne générale du semestre', '', '', '', '', '', moy_gen])

        col_w = [5.5*cm, 1.5*cm, 2*cm, 2*cm, 2.5*cm, 2*cm, 2*cm]
        t = Table(rows, colWidths=col_w, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND',   (0,0),  (-1,0),  INDIGO),
            ('TEXTCOLOR',    (0,0),  (-1,0),  WHITE),
            ('FONTNAME',     (0,0),  (-1,0),  'Helvetica-Bold'),
            ('FONTSIZE',     (0,0),  (-1,-1), 8.5),
            ('ALIGN',        (1,0),  (-1,-1), 'CENTER'),
            ('ROWBACKGROUNDS',(0,1), (-1,-2), [MIST, WHITE]),
            ('BACKGROUND',   (0,-1), (-1,-1), CYAN),
            ('TEXTCOLOR',    (0,-1), (-1,-1), WHITE),
            ('FONTNAME',     (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('GRID',         (0,0),  (-1,-1), 0.3, ASH),
            ('PADDING',      (0,0),  (-1,-1), 5),
        ]))
        story.append(t)
        mention = rs.mention_label if rs else '—'
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(f'Mention : <b>{mention}</b>', cell_style))

    tableau_semestre(notes_s1, rs1, 1)
    story.append(Spacer(1, 0.4*cm))
    tableau_semestre(notes_s2, rs2, 2)
    story.append(Spacer(1, 0.5*cm))

    # ── Résultat annuel ───────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=1, color=CYAN))
    if ra:
        moy_ann = f"{float(ra.moyenne_annuelle):.2f}" if ra.moyenne_annuelle else '—'
        decision_colors = {'admis': SUCCESS, 'redoublant': ALERT,
                           'exclu': ALERT, 'en_attente': GOLD}
        dec_color = decision_colors.get(ra.decision, ASH)
        ann_data = [
            ['Moyenne Semestre 1', f"{float(ra.moyenne_s1):.2f}" if ra.moyenne_s1 else '—'],
            ['Moyenne Semestre 2', f"{float(ra.moyenne_s2):.2f}" if ra.moyenne_s2 else '—'],
            ['Moyenne Annuelle',   moy_ann],
            ['Décision',          ra.decision.upper()],
        ]
        t_ann = Table(ann_data, colWidths=[8*cm, 4*cm])
        t_ann.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN',    (1,0), (1,-1), 'CENTER'),
            ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#EEF2FF')),
            ('TEXTCOLOR',  (1,3), (1,3),  dec_color),
            ('FONTNAME',   (1,3), (1,3),  'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.3, ASH),
            ('PADDING', (0,0), (-1,-1), 7),
        ]))
        story.append(Spacer(1, 0.3*cm))
        story.append(t_ann)

    # ── QR Code ───────────────────────────────────────────────
    if qr_image_path and os.path.exists(qr_image_path):
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph('Scanner le QR code pour vérifier ce relevé :', cell_style))
        qr_img = Image(qr_image_path, width=3*cm, height=3*cm)
        story.append(qr_img)

    # ── Pied de page ──────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=ASH))
    story.append(Paragraph(
        f'Document généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")} — EduNova',
        ParagraphStyle('footer', parent=styles['Normal'], fontSize=8,
                        textColor=ASH, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buffer.getvalue()


def sauvegarder_releve_pdf(pdf_bytes: bytes, etudiant_matricule: str,
                             annee_label: str, type_releve: str = 'annuel') -> str:
    """Sauvegarde le PDF et retourne le chemin relatif."""
    dossier = os.path.join(current_app.config['UPLOAD_FOLDER'], 'releves')
    os.makedirs(dossier, exist_ok=True)
    nom = f'releve_{etudiant_matricule}_{annee_label}_{type_releve}.pdf'
    chemin = os.path.join(dossier, nom)
    with open(chemin, 'wb') as f:
        f.write(pdf_bytes)
    return f'uploads/releves/{nom}'
