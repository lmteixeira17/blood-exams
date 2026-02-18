"""
Management command to seed the Biomarker catalog with common blood test markers.
"""

from django.core.management.base import BaseCommand

from core.models import Biomarker

BIOMARKERS = [
    # ===== HEMOGRAMA =====
    {"name": "Hemoglobina", "code": "HGB", "unit": "g/dL", "category": "Hemograma",
     "ref_min_male": 13.0, "ref_max_male": 17.5, "ref_min_female": 12.0, "ref_max_female": 15.5,
     "aliases": "Hemoglobin,Hb", "description": "Proteína dos glóbulos vermelhos que transporta oxigênio."},
    {"name": "Hematócrito", "code": "HCT", "unit": "%", "category": "Hemograma",
     "ref_min_male": 38.0, "ref_max_male": 50.0, "ref_min_female": 36.0, "ref_max_female": 44.0,
     "aliases": "Hematocrit,Ht", "description": "Percentual do sangue ocupado por glóbulos vermelhos."},
    {"name": "Hemácias", "code": "RBC", "unit": "milhões/mm³", "category": "Hemograma",
     "ref_min_male": 4.5, "ref_max_male": 6.1, "ref_min_female": 4.0, "ref_max_female": 5.4,
     "aliases": "Eritrócitos,Red Blood Cells,Glóbulos Vermelhos", "description": "Contagem de glóbulos vermelhos."},
    {"name": "Leucócitos", "code": "WBC", "unit": "/mm³", "category": "Hemograma",
     "ref_min_male": 4000, "ref_max_male": 11000, "ref_min_female": 4000, "ref_max_female": 11000,
     "aliases": "Glóbulos Brancos,White Blood Cells,Leucocitos Totais", "description": "Células de defesa do organismo."},
    {"name": "Plaquetas", "code": "PLT", "unit": "/mm³", "category": "Hemograma",
     "ref_min_male": 150000, "ref_max_male": 400000, "ref_min_female": 150000, "ref_max_female": 400000,
     "aliases": "Platelets,Trombócitos", "description": "Fragmentos celulares essenciais para coagulação."},
    {"name": "VCM", "code": "VCM", "unit": "fL", "category": "Hemograma",
     "ref_min_male": 80, "ref_max_male": 100, "ref_min_female": 80, "ref_max_female": 100,
     "aliases": "Volume Corpuscular Médio,MCV", "description": "Volume médio dos glóbulos vermelhos."},
    {"name": "HCM", "code": "HCM", "unit": "pg", "category": "Hemograma",
     "ref_min_male": 27, "ref_max_male": 33, "ref_min_female": 27, "ref_max_female": 33,
     "aliases": "Hemoglobina Corpuscular Média,MCH", "description": "Quantidade média de hemoglobina por eritrócito."},
    {"name": "CHCM", "code": "CHCM", "unit": "g/dL", "category": "Hemograma",
     "ref_min_male": 32, "ref_max_male": 36, "ref_min_female": 32, "ref_max_female": 36,
     "aliases": "Concentração de Hemoglobina Corpuscular Média,MCHC", "description": "Concentração média de hemoglobina nos eritrócitos."},
    {"name": "RDW", "code": "RDW", "unit": "%", "category": "Hemograma",
     "ref_min_male": 11.5, "ref_max_male": 14.5, "ref_min_female": 11.5, "ref_max_female": 14.5,
     "aliases": "Red Cell Distribution Width,Amplitude de Distribuição dos Glóbulos Vermelhos", "description": "Variação no tamanho dos glóbulos vermelhos."},
    {"name": "Neutrófilos", "code": "NEUT", "unit": "/mm³", "category": "Hemograma",
     "ref_min_male": 1800, "ref_max_male": 7000, "ref_min_female": 1800, "ref_max_female": 7000,
     "aliases": "Neutrophils,Segmentados", "description": "Principal tipo de leucócito de defesa contra bactérias."},
    {"name": "Linfócitos", "code": "LYMPH", "unit": "/mm³", "category": "Hemograma",
     "ref_min_male": 1000, "ref_max_male": 4800, "ref_min_female": 1000, "ref_max_female": 4800,
     "aliases": "Lymphocytes", "description": "Leucócitos responsáveis pela imunidade adaptativa."},

    # ===== LIPIDOGRAMA =====
    {"name": "Colesterol Total", "code": "CT", "unit": "mg/dL", "category": "Lipidograma",
     "ref_min_male": None, "ref_max_male": 190, "ref_min_female": None, "ref_max_female": 190,
     "aliases": "Total Cholesterol,Colesterol", "description": "Nível total de colesterol no sangue."},
    {"name": "HDL Colesterol", "code": "HDL", "unit": "mg/dL", "category": "Lipidograma",
     "ref_min_male": 40, "ref_max_male": None, "ref_min_female": 50, "ref_max_female": None,
     "aliases": "HDL,Colesterol HDL,HDL-C", "description": "Colesterol 'bom' que remove gordura das artérias."},
    {"name": "LDL Colesterol", "code": "LDL", "unit": "mg/dL", "category": "Lipidograma",
     "ref_min_male": None, "ref_max_male": 130, "ref_min_female": None, "ref_max_female": 130,
     "aliases": "LDL,Colesterol LDL,LDL-C", "description": "Colesterol 'ruim' que pode acumular nas artérias."},
    {"name": "VLDL Colesterol", "code": "VLDL", "unit": "mg/dL", "category": "Lipidograma",
     "ref_min_male": None, "ref_max_male": 30, "ref_min_female": None, "ref_max_female": 30,
     "aliases": "VLDL,Colesterol VLDL", "description": "Lipoproteína de muito baixa densidade."},
    {"name": "Triglicerídeos", "code": "TG", "unit": "mg/dL", "category": "Lipidograma",
     "ref_min_male": None, "ref_max_male": 150, "ref_min_female": None, "ref_max_female": 150,
     "aliases": "Triglicérides,Triglycerides,Triglicerides", "description": "Tipo de gordura no sangue associada a risco cardiovascular."},

    # ===== GLICEMIA =====
    {"name": "Glicose em Jejum", "code": "GLI", "unit": "mg/dL", "category": "Glicemia",
     "ref_min_male": 70, "ref_max_male": 99, "ref_min_female": 70, "ref_max_female": 99,
     "aliases": "Glicemia de Jejum,Glucose,Glicose,Glicemia", "description": "Nível de açúcar no sangue em jejum."},
    {"name": "Hemoglobina Glicada", "code": "HBA1C", "unit": "%", "category": "Glicemia",
     "ref_min_male": None, "ref_max_male": 5.7, "ref_min_female": None, "ref_max_female": 5.7,
     "aliases": "HbA1c,A1C,Hemoglobina Glicosilada,Glicohemoglobina", "description": "Média de glicose dos últimos 2-3 meses."},
    {"name": "Insulina", "code": "INS", "unit": "µUI/mL", "category": "Glicemia",
     "ref_min_male": 2.6, "ref_max_male": 24.9, "ref_min_female": 2.6, "ref_max_female": 24.9,
     "aliases": "Insulina Basal,Insulin", "description": "Hormônio que regula o açúcar no sangue."},

    # ===== FUNÇÃO HEPÁTICA =====
    {"name": "TGO (AST)", "code": "TGO", "unit": "U/L", "category": "Função Hepática",
     "ref_min_male": None, "ref_max_male": 40, "ref_min_female": None, "ref_max_female": 32,
     "aliases": "AST,Aspartato Aminotransferase,Transaminase Oxalacética", "description": "Enzima hepática indicadora de lesão celular."},
    {"name": "TGP (ALT)", "code": "TGP", "unit": "U/L", "category": "Função Hepática",
     "ref_min_male": None, "ref_max_male": 41, "ref_min_female": None, "ref_max_female": 33,
     "aliases": "ALT,Alanina Aminotransferase,Transaminase Pirúvica", "description": "Enzima mais específica do fígado."},
    {"name": "GGT", "code": "GGT", "unit": "U/L", "category": "Função Hepática",
     "ref_min_male": None, "ref_max_male": 60, "ref_min_female": None, "ref_max_female": 40,
     "aliases": "Gama GT,Gama Glutamil Transferase,Gamma GT", "description": "Enzima sensível a doenças hepáticas e uso de álcool."},
    {"name": "Fosfatase Alcalina", "code": "FA", "unit": "U/L", "category": "Função Hepática",
     "ref_min_male": 40, "ref_max_male": 129, "ref_min_female": 35, "ref_max_female": 104,
     "aliases": "Alkaline Phosphatase,ALP", "description": "Enzima presente no fígado e ossos."},
    {"name": "Bilirrubina Total", "code": "BILT", "unit": "mg/dL", "category": "Função Hepática",
     "ref_min_male": None, "ref_max_male": 1.2, "ref_min_female": None, "ref_max_female": 1.2,
     "aliases": "Bilirrubina,Total Bilirubin", "description": "Produto da degradação da hemoglobina."},
    {"name": "Bilirrubina Direta", "code": "BILD", "unit": "mg/dL", "category": "Função Hepática",
     "ref_min_male": None, "ref_max_male": 0.3, "ref_min_female": None, "ref_max_female": 0.3,
     "aliases": "Direct Bilirubin,Bilirrubina Conjugada", "description": "Bilirrubina processada pelo fígado."},
    {"name": "Albumina", "code": "ALB", "unit": "g/dL", "category": "Função Hepática",
     "ref_min_male": 3.5, "ref_max_male": 5.0, "ref_min_female": 3.5, "ref_max_female": 5.0,
     "aliases": "Albumin", "description": "Principal proteína do sangue, produzida pelo fígado."},

    # ===== FUNÇÃO RENAL =====
    {"name": "Creatinina", "code": "CREA", "unit": "mg/dL", "category": "Função Renal",
     "ref_min_male": 0.7, "ref_max_male": 1.2, "ref_min_female": 0.5, "ref_max_female": 0.9,
     "aliases": "Creatinine", "description": "Indicador de função renal."},
    {"name": "Ureia", "code": "UREA", "unit": "mg/dL", "category": "Função Renal",
     "ref_min_male": 15, "ref_max_male": 40, "ref_min_female": 15, "ref_max_female": 40,
     "aliases": "Urea,BUN", "description": "Produto do metabolismo de proteínas filtrado pelos rins."},
    {"name": "Ácido Úrico", "code": "AU", "unit": "mg/dL", "category": "Função Renal",
     "ref_min_male": 3.5, "ref_max_male": 7.2, "ref_min_female": 2.6, "ref_max_female": 6.0,
     "aliases": "Uric Acid,Acido Urico", "description": "Produto do metabolismo das purinas."},
    {"name": "TFG Estimada", "code": "TFG", "unit": "mL/min/1.73m²", "category": "Função Renal",
     "ref_min_male": 90, "ref_max_male": None, "ref_min_female": 90, "ref_max_female": None,
     "aliases": "Taxa de Filtração Glomerular,eGFR,GFR", "description": "Estimativa da capacidade de filtração dos rins."},

    # ===== TIREOIDE =====
    {"name": "TSH", "code": "TSH", "unit": "µUI/mL", "category": "Tireoide",
     "ref_min_male": 0.4, "ref_max_male": 4.0, "ref_min_female": 0.4, "ref_max_female": 4.0,
     "aliases": "Hormônio Tireoestimulante,Thyroid Stimulating Hormone", "description": "Hormônio que regula a tireoide."},
    {"name": "T4 Livre", "code": "T4L", "unit": "ng/dL", "category": "Tireoide",
     "ref_min_male": 0.8, "ref_max_male": 1.8, "ref_min_female": 0.8, "ref_max_female": 1.8,
     "aliases": "Free T4,Tiroxina Livre,FT4", "description": "Hormônio tireoidiano ativo."},
    {"name": "T3 Livre", "code": "T3L", "unit": "pg/mL", "category": "Tireoide",
     "ref_min_male": 2.3, "ref_max_male": 4.2, "ref_min_female": 2.3, "ref_max_female": 4.2,
     "aliases": "Free T3,Triiodotironina Livre,FT3", "description": "Hormônio tireoidiano mais ativo."},

    # ===== VITAMINAS E MINERAIS =====
    {"name": "Vitamina D (25-OH)", "code": "VITD", "unit": "ng/mL", "category": "Vitaminas e Minerais",
     "ref_min_male": 30, "ref_max_male": 100, "ref_min_female": 30, "ref_max_female": 100,
     "aliases": "25-Hidroxivitamina D,Vitamin D,25(OH)D,Vitamina D", "description": "Vitamina essencial para ossos e imunidade."},
    {"name": "Vitamina B12", "code": "B12", "unit": "pg/mL", "category": "Vitaminas e Minerais",
     "ref_min_male": 200, "ref_max_male": 900, "ref_min_female": 200, "ref_max_female": 900,
     "aliases": "Cobalamina,Vitamin B12,Cianocobalamina", "description": "Vitamina essencial para o sistema nervoso e produção de sangue."},
    {"name": "Ácido Fólico", "code": "FOLATO", "unit": "ng/mL", "category": "Vitaminas e Minerais",
     "ref_min_male": 3.0, "ref_max_male": 17.0, "ref_min_female": 3.0, "ref_max_female": 17.0,
     "aliases": "Folato,Folic Acid,Vitamina B9", "description": "Vitamina B9 essencial para produção celular."},
    {"name": "Ferro Sérico", "code": "FE", "unit": "µg/dL", "category": "Vitaminas e Minerais",
     "ref_min_male": 65, "ref_max_male": 175, "ref_min_female": 50, "ref_max_female": 170,
     "aliases": "Ferro,Iron,Serum Iron", "description": "Nível de ferro circulante no sangue."},
    {"name": "Ferritina", "code": "FERR", "unit": "ng/mL", "category": "Vitaminas e Minerais",
     "ref_min_male": 30, "ref_max_male": 400, "ref_min_female": 13, "ref_max_female": 150,
     "aliases": "Ferritin", "description": "Proteína de armazenamento de ferro."},
    {"name": "Zinco", "code": "ZN", "unit": "µg/dL", "category": "Vitaminas e Minerais",
     "ref_min_male": 70, "ref_max_male": 120, "ref_min_female": 70, "ref_max_female": 120,
     "aliases": "Zinc", "description": "Mineral essencial para imunidade e cicatrização."},
    {"name": "Magnésio", "code": "MG", "unit": "mg/dL", "category": "Vitaminas e Minerais",
     "ref_min_male": 1.7, "ref_max_male": 2.2, "ref_min_female": 1.7, "ref_max_female": 2.2,
     "aliases": "Magnesium,Magnesio", "description": "Mineral essencial para músculos e nervos."},
    {"name": "Cálcio", "code": "CA", "unit": "mg/dL", "category": "Vitaminas e Minerais",
     "ref_min_male": 8.6, "ref_max_male": 10.2, "ref_min_female": 8.6, "ref_max_female": 10.2,
     "aliases": "Calcium,Calcio", "description": "Mineral essencial para ossos e função muscular."},
    {"name": "Sódio", "code": "NA", "unit": "mEq/L", "category": "Vitaminas e Minerais",
     "ref_min_male": 136, "ref_max_male": 145, "ref_min_female": 136, "ref_max_female": 145,
     "aliases": "Sodium,Sodio", "description": "Eletrólito essencial para equilíbrio hídrico."},
    {"name": "Potássio", "code": "K", "unit": "mEq/L", "category": "Vitaminas e Minerais",
     "ref_min_male": 3.5, "ref_max_male": 5.1, "ref_min_female": 3.5, "ref_max_female": 5.1,
     "aliases": "Potassium,Potassio", "description": "Eletrólito essencial para função cardíaca e muscular."},

    # ===== HORMONAL =====
    {"name": "Testosterona Total", "code": "TESTO", "unit": "ng/dL", "category": "Hormonal",
     "ref_min_male": 249, "ref_max_male": 836, "ref_min_female": 8, "ref_max_female": 60,
     "aliases": "Testosterone,Testosterona", "description": "Principal hormônio sexual masculino."},
    {"name": "Testosterona Livre", "code": "TESTOL", "unit": "pg/mL", "category": "Hormonal",
     "ref_min_male": 4.5, "ref_max_male": 42, "ref_min_female": 0.3, "ref_max_female": 4.1,
     "aliases": "Free Testosterone", "description": "Fração ativa da testosterona."},
    {"name": "Estradiol", "code": "E2", "unit": "pg/mL", "category": "Hormonal",
     "ref_min_male": 11, "ref_max_male": 44, "ref_min_female": 19, "ref_max_female": 357,
     "aliases": "Estradiol,E2,Estrogênio", "description": "Principal estrogênio."},
    {"name": "DHEA-S", "code": "DHEAS", "unit": "µg/dL", "category": "Hormonal",
     "ref_min_male": 80, "ref_max_male": 560, "ref_min_female": 35, "ref_max_female": 430,
     "aliases": "DHEA Sulfato,DHEA-SO4", "description": "Precursor hormonal produzido pelas adrenais."},
    {"name": "Cortisol", "code": "CORT", "unit": "µg/dL", "category": "Hormonal",
     "ref_min_male": 6.2, "ref_max_male": 19.4, "ref_min_female": 6.2, "ref_max_female": 19.4,
     "aliases": "Cortisol Matinal,Cortisol Sérico", "description": "Hormônio do estresse produzido pelas adrenais."},
    {"name": "IGF-1", "code": "IGF1", "unit": "ng/mL", "category": "Hormonal",
     "ref_min_male": 115, "ref_max_male": 355, "ref_min_female": 115, "ref_max_female": 355,
     "aliases": "Somatomedina C,Insulin-like Growth Factor 1", "description": "Marcador de hormônio do crescimento."},
    {"name": "PSA Total", "code": "PSA", "unit": "ng/mL", "category": "Hormonal",
     "ref_min_male": None, "ref_max_male": 4.0, "ref_min_female": None, "ref_max_female": None,
     "aliases": "Antígeno Prostático Específico,Prostate Specific Antigen", "description": "Marcador prostático (masculino)."},
    {"name": "Prolactina", "code": "PRL", "unit": "ng/mL", "category": "Hormonal",
     "ref_min_male": 4.0, "ref_max_male": 15.2, "ref_min_female": 4.8, "ref_max_female": 23.3,
     "aliases": "Prolactin", "description": "Hormônio da hipófise."},
    {"name": "LH", "code": "LH", "unit": "mUI/mL", "category": "Hormonal",
     "ref_min_male": 1.7, "ref_max_male": 8.6, "ref_min_female": 2.4, "ref_max_female": 12.6,
     "aliases": "Hormônio Luteinizante,Luteinizing Hormone", "description": "Hormônio que regula a função gonadal."},
    {"name": "FSH", "code": "FSH", "unit": "mUI/mL", "category": "Hormonal",
     "ref_min_male": 1.5, "ref_max_male": 12.4, "ref_min_female": 3.5, "ref_max_female": 12.5,
     "aliases": "Hormônio Folículo Estimulante,Follicle Stimulating Hormone", "description": "Hormônio que regula a reprodução."},

    # ===== INFLAMAÇÃO =====
    {"name": "PCR (Proteína C Reativa)", "code": "PCR", "unit": "mg/L", "category": "Inflamação",
     "ref_min_male": None, "ref_max_male": 3.0, "ref_min_female": None, "ref_max_female": 3.0,
     "aliases": "Proteína C Reativa,CRP,C-Reactive Protein,PCR Ultrassensível", "description": "Marcador de inflamação sistêmica."},
    {"name": "VHS", "code": "VHS", "unit": "mm/h", "category": "Inflamação",
     "ref_min_male": None, "ref_max_male": 15, "ref_min_female": None, "ref_max_female": 20,
     "aliases": "Velocidade de Hemossedimentação,ESR,VSG", "description": "Velocidade de sedimentação dos eritrócitos."},
    {"name": "Homocisteína", "code": "HOMO", "unit": "µmol/L", "category": "Inflamação",
     "ref_min_male": 5.0, "ref_max_male": 15.0, "ref_min_female": 5.0, "ref_max_female": 12.0,
     "aliases": "Homocysteine,Homocisteina", "description": "Aminoácido associado a risco cardiovascular."},

    # ===== PROTEÍNAS =====
    {"name": "Proteínas Totais", "code": "PT", "unit": "g/dL", "category": "Proteínas",
     "ref_min_male": 6.0, "ref_max_male": 8.0, "ref_min_female": 6.0, "ref_max_female": 8.0,
     "aliases": "Total Protein,Proteinas Totais", "description": "Total de proteínas no sangue."},
    {"name": "Globulinas", "code": "GLOB", "unit": "g/dL", "category": "Proteínas",
     "ref_min_male": 2.0, "ref_max_male": 3.5, "ref_min_female": 2.0, "ref_max_female": 3.5,
     "aliases": "Globulin", "description": "Proteínas imunológicas e de transporte."},
]


class Command(BaseCommand):
    help = 'Seed the Biomarker catalog with common blood test markers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing biomarkers',
        )

    def handle(self, *args, **options):
        force = options['force']
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for data in BIOMARKERS:
            code = data['code']
            existing = Biomarker.objects.filter(code=code).first()

            if existing and not force:
                skipped_count += 1
                continue

            from decimal import Decimal
            fields = {
                'name': data['name'],
                'unit': data['unit'],
                'category': data['category'],
                'aliases': data.get('aliases', ''),
                'description': data.get('description', ''),
            }
            for f in ['ref_min_male', 'ref_max_male', 'ref_min_female', 'ref_max_female']:
                val = data.get(f)
                fields[f] = Decimal(str(val)) if val is not None else None

            _, was_created = Biomarker.objects.update_or_create(
                code=code,
                defaults=fields,
            )

            if was_created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Biomarkers: {created_count} created, {updated_count} updated, {skipped_count} skipped. '
                f'Total in DB: {Biomarker.objects.count()}'
            )
        )
