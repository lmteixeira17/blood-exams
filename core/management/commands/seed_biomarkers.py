"""
Management command to seed the Biomarker catalog with common blood test markers.
"""

from django.core.management.base import BaseCommand

from core.models import Biomarker

BIOMARKERS = [
    # ===== HEMOGRAMA =====
    {"name": "Hemoglobina", "code": "HGB", "unit": "g/dL", "category": "Hemograma",
     "ref_min_male": 13.0, "ref_max_male": 17.5, "ref_min_female": 12.0, "ref_max_female": 15.5,
     "aliases": "Hemoglobin,Hb",
     "description": "A hemoglobina é a proteína presente nos glóbulos vermelhos responsável pelo transporte de oxigênio dos pulmões para os tecidos e de dióxido de carbono no sentido inverso. Valores baixos indicam anemia (ferropriva, megaloblástica, hemolítica ou de doença crônica), enquanto valores elevados podem ocorrer em policitemia vera, desidratação ou doenças pulmonares crônicas. É um dos exames mais solicitados na prática clínica."},
    {"name": "Hematócrito", "code": "HCT", "unit": "%", "category": "Hemograma",
     "ref_min_male": 38.0, "ref_max_male": 50.0, "ref_min_female": 36.0, "ref_max_female": 44.0,
     "aliases": "Hematocrit,Ht",
     "description": "O hematócrito representa a proporção do volume sanguíneo total ocupada pelos glóbulos vermelhos. Valores reduzidos acompanham quadros de anemia, hemorragia ou hiperidratação. Valores elevados são encontrados na desidratação, policitemia e condições que aumentam a produção de eritrócitos, como DPOC e tabagismo. Sempre interpretado em conjunto com hemoglobina e contagem de hemácias."},
    {"name": "Hemácias", "code": "RBC", "unit": "milhões/mm³", "category": "Hemograma",
     "ref_min_male": 4.5, "ref_max_male": 6.1, "ref_min_female": 4.0, "ref_max_female": 5.4,
     "aliases": "Eritrócitos,Red Blood Cells,Glóbulos Vermelhos",
     "description": "As hemácias (eritrócitos) são as células mais abundantes do sangue, responsáveis pelo transporte de oxigênio através da hemoglobina. Valores diminuídos indicam anemia de diversas etiologias. Valores aumentados (eritrocitose) ocorrem em policitemia vera, desidratação, hipóxia crônica (altitude elevada, tabagismo) e uso de eritropoietina. A contagem é essencial para classificação das anemias."},
    {"name": "Leucócitos", "code": "WBC", "unit": "/mm³", "category": "Hemograma",
     "ref_min_male": 4000, "ref_max_male": 11000, "ref_min_female": 4000, "ref_max_female": 11000,
     "aliases": "Glóbulos Brancos,White Blood Cells,Leucocitos Totais",
     "description": "Os leucócitos são as células de defesa do sistema imunológico. A contagem total inclui neutrófilos, linfócitos, monócitos, eosinófilos e basófilos. Leucocitose (valores elevados) sugere infecção bacteriana, inflamação, estresse ou neoplasia hematológica. Leucopenia (valores baixos) pode indicar infecção viral, uso de medicamentos imunossupressores, deficiência de B12/folato ou doenças da medula óssea."},
    {"name": "Plaquetas", "code": "PLT", "unit": "/mm³", "category": "Hemograma",
     "ref_min_male": 150000, "ref_max_male": 400000, "ref_min_female": 150000, "ref_max_female": 400000,
     "aliases": "Platelets,Trombócitos",
     "description": "As plaquetas são fragmentos celulares produzidos pela medula óssea, essenciais para a hemostasia primária e coagulação sanguínea. Trombocitopenia (<150.000) aumenta o risco de sangramento e pode ser causada por infecções virais, doenças autoimunes, uso de medicamentos ou doenças da medula. Trombocitose (>400.000) pode ser reativa (infecções, inflamação, deficiência de ferro) ou clonal (neoplasias mieloproliferativas)."},
    {"name": "VCM", "code": "VCM", "unit": "fL", "category": "Hemograma",
     "ref_min_male": 80, "ref_max_male": 100, "ref_min_female": 80, "ref_max_female": 100,
     "aliases": "Volume Corpuscular Médio,MCV",
     "description": "O Volume Corpuscular Médio indica o tamanho médio das hemácias. VCM baixo (microcitose) é encontrado na anemia ferropriva e talassemias. VCM elevado (macrocitose) ocorre na deficiência de B12 ou folato, alcoolismo, hepatopatias e uso de alguns medicamentos (metotrexato, zidovudina). VCM normal (normocitose) com anemia sugere doença crônica, hemólise ou sangramento agudo. É fundamental na classificação morfológica das anemias."},
    {"name": "HCM", "code": "HCM", "unit": "pg", "category": "Hemograma",
     "ref_min_male": 27, "ref_max_male": 33, "ref_min_female": 27, "ref_max_female": 33,
     "aliases": "Hemoglobina Corpuscular Média,MCH",
     "description": "A Hemoglobina Corpuscular Média expressa a quantidade média de hemoglobina contida em cada hemácia, medida em picogramas. HCM baixa (hipocromia) acompanha a anemia ferropriva e talassemias, indicando hemácias com menos hemoglobina. HCM elevada ocorre nas anemias megaloblásticas. Avaliada em conjunto com VCM e CHCM, auxilia na classificação das anemias em hipocrômicas, normocrômicas ou hipercrômicas."},
    {"name": "CHCM", "code": "CHCM", "unit": "g/dL", "category": "Hemograma",
     "ref_min_male": 32, "ref_max_male": 36, "ref_min_female": 32, "ref_max_female": 36,
     "aliases": "Concentração de Hemoglobina Corpuscular Média,MCHC",
     "description": "A Concentração de Hemoglobina Corpuscular Média indica a concentração média de hemoglobina dentro dos eritrócitos. CHCM baixa confirma hipocromia na anemia ferropriva. CHCM elevada (>36 g/dL) é característica da esferocitose hereditária e pode ocorrer em anemias hemolíticas autoimunes. É o índice mais estável do hemograma e alterações significativas merecem atenção diagnóstica."},
    {"name": "RDW", "code": "RDW", "unit": "%", "category": "Hemograma",
     "ref_min_male": 11.5, "ref_max_male": 14.5, "ref_min_female": 11.5, "ref_max_female": 14.5,
     "aliases": "Red Cell Distribution Width,Amplitude de Distribuição dos Glóbulos Vermelhos",
     "description": "O RDW mede a variação no tamanho dos glóbulos vermelhos (anisocitose). RDW elevado indica hemácias de tamanhos heterogêneos, sendo característico da anemia ferropriva (RDW alto + VCM baixo), diferenciando-a da talassemia minor (RDW normal + VCM baixo). Também se eleva na deficiência mista de ferro e B12/folato, transfusão recente e reticulocitose. Estudos recentes associam RDW elevado a maior mortalidade cardiovascular e por todas as causas."},
    {"name": "Neutrófilos", "code": "NEUT", "unit": "/mm³", "category": "Hemograma",
     "ref_min_male": 1800, "ref_max_male": 7000, "ref_min_female": 1800, "ref_max_female": 7000,
     "aliases": "Neutrophils,Segmentados",
     "description": "Os neutrófilos são os leucócitos mais abundantes e constituem a primeira linha de defesa contra infecções bacterianas e fúngicas. Neutrofilia (elevação) ocorre em infecções bacterianas, inflamação aguda, estresse fisiológico, uso de corticoides e neoplasias mieloides. Neutropenia (<1.500/mm³) aumenta significativamente o risco de infecções e pode ser causada por quimioterapia, infecções virais, drogas ou doenças autoimunes. Abaixo de 500/mm³ é considerada neutropenia grave."},
    {"name": "Linfócitos", "code": "LYMPH", "unit": "/mm³", "category": "Hemograma",
     "ref_min_male": 1000, "ref_max_male": 4800, "ref_min_female": 1000, "ref_max_female": 4800,
     "aliases": "Lymphocytes",
     "description": "Os linfócitos são células centrais da imunidade adaptativa, incluindo linfócitos T (imunidade celular), B (produção de anticorpos) e NK (células natural killer). Linfocitose ocorre em infecções virais (mononucleose, hepatite, CMV), leucemia linfocítica crônica e reações a medicamentos. Linfopenia pode indicar infecção por HIV, uso de corticoides, quimioterapia ou doenças autoimunes. A relação neutrófilo/linfócito (NLR) é um marcador inflamatório emergente."},

    # ===== LIPIDOGRAMA =====
    {"name": "Colesterol Total", "code": "CT", "unit": "mg/dL", "category": "Lipidograma",
     "ref_min_male": None, "ref_max_male": 190, "ref_min_female": None, "ref_max_female": 190,
     "aliases": "Total Cholesterol,Colesterol",
     "description": "O colesterol total representa a soma do HDL, LDL e VLDL no sangue. É um lipídio essencial para a formação de membranas celulares, hormônios esteroidais e ácidos biliares. Valores acima de 190 mg/dL são considerados elevados e associados a maior risco de doença aterosclerótica cardiovascular. O colesterol total isolado tem utilidade limitada — a avaliação do perfil lipídico completo (HDL, LDL, triglicerídeos) é mais informativa para estratificação de risco."},
    {"name": "HDL Colesterol", "code": "HDL", "unit": "mg/dL", "category": "Lipidograma",
     "ref_min_male": 40, "ref_max_male": None, "ref_min_female": 50, "ref_max_female": None,
     "aliases": "HDL,Colesterol HDL,HDL-C",
     "description": "O HDL (lipoproteína de alta densidade) é conhecido como 'colesterol bom' por sua função de transporte reverso: remove o colesterol excedente das artérias e o leva ao fígado para eliminação. Níveis elevados de HDL são protetores contra doença cardiovascular. Valores baixos (<40 mg/dL em homens, <50 em mulheres) aumentam o risco aterosclerótico. O HDL pode ser elevado por exercício físico regular, consumo moderado de álcool e perda de peso."},
    {"name": "LDL Colesterol", "code": "LDL", "unit": "mg/dL", "category": "Lipidograma",
     "ref_min_male": None, "ref_max_male": 130, "ref_min_female": None, "ref_max_female": 130,
     "aliases": "LDL,Colesterol LDL,LDL-C",
     "description": "O LDL (lipoproteína de baixa densidade) é o principal transportador de colesterol para os tecidos periféricos. Quando em excesso, deposita-se nas paredes arteriais formando placas de ateroma, sendo o principal fator de risco modificável para doenças cardiovasculares. A meta de LDL varia conforme o risco cardiovascular: <130 para baixo risco, <100 para risco intermediário, <70 para alto risco e <50 para risco muito alto. É o principal alvo terapêutico das estatinas."},
    {"name": "VLDL Colesterol", "code": "VLDL", "unit": "mg/dL", "category": "Lipidograma",
     "ref_min_male": None, "ref_max_male": 30, "ref_min_female": None, "ref_max_female": 30,
     "aliases": "VLDL,Colesterol VLDL",
     "description": "O VLDL (lipoproteína de muito baixa densidade) é produzido pelo fígado e transporta triglicerídeos para os tecidos. É calculado como triglicerídeos/5 (fórmula de Friedewald). Valores elevados estão associados a hipertrigliceridemia, resistência insulínica, diabetes tipo 2 e síndrome metabólica. O VLDL é considerado uma partícula aterogênica e contribui para o colesterol não-HDL."},
    {"name": "Triglicerídeos", "code": "TG", "unit": "mg/dL", "category": "Lipidograma",
     "ref_min_male": None, "ref_max_male": 150, "ref_min_female": None, "ref_max_female": 150,
     "aliases": "Triglicérides,Triglycerides,Triglicerides",
     "description": "Os triglicerídeos são a principal forma de armazenamento de gordura no organismo e importante fonte energética. Níveis elevados (>150 mg/dL) estão associados a risco cardiovascular aumentado, resistência insulínica, síndrome metabólica e esteatose hepática. Hipertrigliceridemia grave (>500 mg/dL) aumenta o risco de pancreatite aguda. Valores são influenciados por dieta rica em carboidratos e gorduras, consumo de álcool, obesidade, diabetes descompensado e hipotireoidismo."},

    # ===== GLICEMIA =====
    {"name": "Glicose em Jejum", "code": "GLI", "unit": "mg/dL", "category": "Glicemia",
     "ref_min_male": 70, "ref_max_male": 99, "ref_min_female": 70, "ref_max_female": 99,
     "aliases": "Glicemia de Jejum,Glucose,Glicose,Glicemia",
     "description": "A glicose em jejum mede o nível de açúcar no sangue após pelo menos 8 horas sem alimentação. É o exame de triagem primário para diabetes mellitus. Valores entre 100-125 mg/dL indicam pré-diabetes (glicemia de jejum alterada), enquanto valores ≥126 mg/dL em duas ocasiões confirmam diabetes. Hipoglicemia (<70 mg/dL) pode causar tremores, sudorese, confusão mental e, se grave, convulsões e coma. É influenciada por estresse, medicamentos e atividade física recente."},
    {"name": "Hemoglobina Glicada", "code": "HBA1C", "unit": "%", "category": "Glicemia",
     "ref_min_male": None, "ref_max_male": 5.7, "ref_min_female": None, "ref_max_female": 5.7,
     "aliases": "HbA1c,A1C,Hemoglobina Glicosilada,Glicohemoglobina",
     "description": "A hemoglobina glicada reflete a média dos níveis de glicose no sangue nos últimos 2-3 meses, correspondendo ao tempo de vida das hemácias. HbA1c <5.7% é normal, 5.7-6.4% indica pré-diabetes e ≥6.5% confirma diabetes. Para diabéticos, a meta geralmente é <7.0%. É superior à glicose de jejum por não ser afetada por variações diárias, estresse ou jejum. Pode ser falseada por anemias hemolíticas, hemoglobinopatias e insuficiência renal crônica."},
    {"name": "Insulina", "code": "INS", "unit": "µUI/mL", "category": "Glicemia",
     "ref_min_male": 2.6, "ref_max_male": 24.9, "ref_min_female": 2.6, "ref_max_female": 24.9,
     "aliases": "Insulina Basal,Insulin",
     "description": "A insulina é o hormônio produzido pelas células beta do pâncreas, essencial para o metabolismo da glicose. Valores elevados com glicose normal ou alta indicam resistência insulínica, frequentemente associada a síndrome metabólica, obesidade visceral e pré-diabetes. O índice HOMA-IR (insulina x glicose / 405) é usado para quantificar a resistência. Insulinoma (tumor pancreático) causa hiperinsulinemia com hipoglicemia. A dosagem também é útil no diagnóstico diferencial de diabetes tipo 1 vs tipo 2."},

    # ===== FUNÇÃO HEPÁTICA =====
    {"name": "TGO (AST)", "code": "TGO", "unit": "U/L", "category": "Função Hepática",
     "ref_min_male": None, "ref_max_male": 40, "ref_min_female": None, "ref_max_female": 32,
     "aliases": "AST,Aspartato Aminotransferase,Transaminase Oxalacética",
     "description": "A TGO (AST - Aspartato Aminotransferase) é uma enzima presente no fígado, coração, músculos e rins. Sua elevação indica lesão celular nesses órgãos. No contexto hepático, eleva-se em hepatites virais, alcoólica e medicamentosa, cirrose e esteatose. A relação TGO/TGP (índice de De Ritis) >2 sugere doença hepática alcoólica; <1 sugere hepatite viral ou esteatose não alcoólica. Elevações isoladas de TGO podem indicar lesão muscular ou infarto do miocárdio."},
    {"name": "TGP (ALT)", "code": "TGP", "unit": "U/L", "category": "Função Hepática",
     "ref_min_male": None, "ref_max_male": 41, "ref_min_female": None, "ref_max_female": 33,
     "aliases": "ALT,Alanina Aminotransferase,Transaminase Pirúvica",
     "description": "A TGP (ALT - Alanina Aminotransferase) é a enzima mais específica do fígado, encontrada predominantemente nos hepatócitos. Sua elevação é o melhor indicador de lesão hepatocelular. Causas comuns incluem esteatose hepática não alcoólica (NAFLD), hepatites virais, doença hepática alcoólica, medicamentos hepatotóxicos e hepatite autoimune. Elevações leves e persistentes são frequentes em obesos e diabéticos. Elevações >10x o limite superior sugerem hepatite aguda viral ou isquêmica."},
    {"name": "GGT", "code": "GGT", "unit": "U/L", "category": "Função Hepática",
     "ref_min_male": None, "ref_max_male": 60, "ref_min_female": None, "ref_max_female": 40,
     "aliases": "Gama GT,Gama Glutamil Transferase,Gamma GT",
     "description": "A Gama-GT é uma enzima hepática extremamente sensível, sendo um dos primeiros marcadores a se alterar em doenças hepatobiliares. É particularmente útil como indicador de consumo excessivo de álcool, doenças colestáticas e uso de medicamentos indutores enzimáticos (anticonvulsivantes, barbitúricos). GGT elevada isolada, sem elevação de outras enzimas hepáticas, é frequente em etilistas. Também se eleva em esteatose hepática, obesidade, diabetes e síndrome metabólica. Estudos mostram associação com risco cardiovascular independente."},
    {"name": "Fosfatase Alcalina", "code": "FA", "unit": "U/L", "category": "Função Hepática",
     "ref_min_male": 40, "ref_max_male": 129, "ref_min_female": 35, "ref_max_female": 104,
     "aliases": "Alkaline Phosphatase,ALP",
     "description": "A fosfatase alcalina é uma enzima presente no fígado, ossos, intestino e placenta. Elevações de origem hepática (geralmente acompanhadas de GGT elevada) indicam colestase — obstrução biliar por cálculos, tumores ou hepatopatias colestáticas. Elevações de origem óssea (GGT normal) ocorrem em doenças ósseas como Paget, hiperparatireoidismo, fraturas em consolidação e crescimento na infância/adolescência. Valores muito baixos podem indicar hipofosfatasia ou deficiência de zinco."},
    {"name": "Bilirrubina Total", "code": "BILT", "unit": "mg/dL", "category": "Função Hepática",
     "ref_min_male": None, "ref_max_male": 1.2, "ref_min_female": None, "ref_max_female": 1.2,
     "aliases": "Bilirrubina,Total Bilirubin",
     "description": "A bilirrubina é o produto final da degradação da hemoglobina dos glóbulos vermelhos. A bilirrubina total é a soma das frações direta (conjugada) e indireta (não conjugada). Valores acima de 2-3 mg/dL causam icterícia (coloração amarelada da pele e mucosas). Elevações predominantemente indiretas sugerem hemólise ou Síndrome de Gilbert (condição benigna que afeta ~5% da população). Elevações predominantemente diretas indicam doença hepatocelular ou obstrução biliar."},
    {"name": "Bilirrubina Direta", "code": "BILD", "unit": "mg/dL", "category": "Função Hepática",
     "ref_min_male": None, "ref_max_male": 0.3, "ref_min_female": None, "ref_max_female": 0.3,
     "aliases": "Direct Bilirubin,Bilirrubina Conjugada",
     "description": "A bilirrubina direta (conjugada) é a fração da bilirrubina que já foi processada pelo fígado e tornada hidrossolúvel para excreção na bile. Sua elevação indica dificuldade de excreção biliar, podendo ser causada por hepatite, cirrose, colestase intra-hepática ou obstrução extra-hepática (cálculos biliares, tumores de cabeça de pâncreas ou colangiocarcinoma). Quando elevada, é excretada na urina, causando colúria (urina escura como coca-cola)."},
    {"name": "Albumina", "code": "ALB", "unit": "g/dL", "category": "Função Hepática",
     "ref_min_male": 3.5, "ref_max_male": 5.0, "ref_min_female": 3.5, "ref_max_female": 5.0,
     "aliases": "Albumin",
     "description": "A albumina é a proteína mais abundante do plasma sanguíneo, produzida exclusivamente pelo fígado. Tem funções de transporte (hormônios, medicamentos, bilirrubina) e manutenção da pressão oncótica (evita edema). Hipoalbuminemia (<3.5 g/dL) ocorre em doença hepática crônica (cirrose), síndrome nefrótica, desnutrição, inflamação crônica e queimaduras extensas. É um marcador de função hepática de síntese e indicador prognóstico em pacientes críticos e cirróticos."},

    # ===== FUNÇÃO RENAL =====
    {"name": "Creatinina", "code": "CREA", "unit": "mg/dL", "category": "Função Renal",
     "ref_min_male": 0.7, "ref_max_male": 1.2, "ref_min_female": 0.5, "ref_max_female": 0.9,
     "aliases": "Creatinine",
     "description": "A creatinina é um produto do metabolismo da creatina muscular, filtrada pelos rins e excretada na urina. É o principal marcador de função renal, pois sua concentração sanguínea aumenta quando a capacidade de filtração dos rins diminui. Valores elevados indicam insuficiência renal (aguda ou crônica). É influenciada pela massa muscular, dieta proteica e hidratação. A creatinina é usada para calcular a Taxa de Filtração Glomerular estimada (TFGe), que é o padrão para classificar a doença renal crônica em estágios."},
    {"name": "Ureia", "code": "UREA", "unit": "mg/dL", "category": "Função Renal",
     "ref_min_male": 15, "ref_max_male": 40, "ref_min_female": 15, "ref_max_female": 40,
     "aliases": "Urea,BUN",
     "description": "A ureia é o principal produto final do metabolismo das proteínas, sintetizada pelo fígado e excretada pelos rins. Valores elevados (azotemia) podem indicar insuficiência renal, desidratação, dieta hiperproteica, sangramento gastrointestinal ou catabolismo aumentado (trauma, sepse). Valores baixos ocorrem em insuficiência hepática grave e desnutrição. A relação ureia/creatinina ajuda a diferenciar causas pré-renais (desidratação, IC) de causas renais intrínsecas de insuficiência renal."},
    {"name": "Ácido Úrico", "code": "AU", "unit": "mg/dL", "category": "Função Renal",
     "ref_min_male": 3.5, "ref_max_male": 7.2, "ref_min_female": 2.6, "ref_max_female": 6.0,
     "aliases": "Uric Acid,Acido Urico",
     "description": "O ácido úrico é o produto final do metabolismo das purinas (componentes do DNA/RNA). Hiperuricemia (>7 mg/dL) é o principal fator para gota (artrite por depósito de cristais de urato). Também está associada a doença renal crônica, nefrolitíase (cálculos renais), síndrome metabólica, hipertensão e risco cardiovascular. Causas incluem dieta rica em purinas (carnes vermelhas, frutos do mar, cerveja), obesidade, insuficiência renal e lise tumoral. O tratamento com alopurinol ou febuxostat reduz a produção."},
    {"name": "TFG Estimada", "code": "TFG", "unit": "mL/min/1.73m²", "category": "Função Renal",
     "ref_min_male": 90, "ref_max_male": None, "ref_min_female": 90, "ref_max_female": None,
     "aliases": "Taxa de Filtração Glomerular,eGFR,GFR",
     "description": "A Taxa de Filtração Glomerular estimada (TFGe) é calculada a partir da creatinina sérica, idade, sexo e etnia (fórmulas CKD-EPI ou MDRD). É o melhor indicador global da função renal e base para o estadiamento da Doença Renal Crônica (DRC): estágio 1 (≥90, com outro marcador de lesão), estágio 2 (60-89), estágio 3a (45-59), estágio 3b (30-44), estágio 4 (15-29) e estágio 5 (<15, indicação de diálise). Declínio progressivo requer investigação e acompanhamento nefrológico."},

    # ===== TIREOIDE =====
    {"name": "TSH", "code": "TSH", "unit": "µUI/mL", "category": "Tireoide",
     "ref_min_male": 0.4, "ref_max_male": 4.0, "ref_min_female": 0.4, "ref_max_female": 4.0,
     "aliases": "Hormônio Tireoestimulante,Thyroid Stimulating Hormone",
     "description": "O TSH (Hormônio Tireoestimulante) é produzido pela hipófise e regula a função da tireoide. É o exame mais sensível para rastreamento de disfunção tireoidiana. TSH elevado com T4L baixo confirma hipotireoidismo primário (mais comum: tireoidite de Hashimoto). TSH suprimido (<0.1) com T4L/T3L elevados confirma hipertireoidismo (mais comum: doença de Graves). TSH isoladamente alterado com T4L normal define quadros subclínicos. Na gestação, os valores de referência são mais baixos no primeiro trimestre."},
    {"name": "T4 Livre", "code": "T4L", "unit": "ng/dL", "category": "Tireoide",
     "ref_min_male": 0.8, "ref_max_male": 1.8, "ref_min_female": 0.8, "ref_max_female": 1.8,
     "aliases": "Free T4,Tiroxina Livre,FT4",
     "description": "O T4 Livre (tiroxina livre) é a fração biologicamente ativa do principal hormônio produzido pela tireoide. Representa apenas 0.03% do T4 total, sendo o restante ligado a proteínas transportadoras. T4L baixo com TSH elevado confirma hipotireoidismo. T4L elevado com TSH suprimido confirma hipertireoidismo. É preferível ao T4 total por não ser afetado por variações nas proteínas de ligação (gravidez, uso de anticoncepcionais, doenças hepáticas). O T4 é convertido em T3 (forma mais ativa) nos tecidos periféricos."},
    {"name": "T3 Livre", "code": "T3L", "unit": "pg/mL", "category": "Tireoide",
     "ref_min_male": 2.3, "ref_max_male": 4.2, "ref_min_female": 2.3, "ref_max_female": 4.2,
     "aliases": "Free T3,Triiodotironina Livre,FT3",
     "description": "O T3 Livre (triiodotironina livre) é o hormônio tireoidiano metabolicamente mais ativo, sendo 3-4 vezes mais potente que o T4. Cerca de 80% do T3 circulante é produzido pela conversão periférica do T4, e apenas 20% é secretado diretamente pela tireoide. É especialmente útil no diagnóstico da tireotoxicose por T3 (T3-toxicosis), onde o T4L pode estar normal. Em doenças não tireoidianas graves (síndrome do eutireoideo doente), o T3 pode estar baixo com TSH e T4L normais."},

    # ===== VITAMINAS E MINERAIS =====
    {"name": "Vitamina D (25-OH)", "code": "VITD", "unit": "ng/mL", "category": "Vitaminas e Minerais",
     "ref_min_male": 30, "ref_max_male": 100, "ref_min_female": 30, "ref_max_female": 100,
     "aliases": "25-Hidroxivitamina D,Vitamin D,25(OH)D,Vitamina D",
     "description": "A 25-hidroxivitamina D é a forma circulante da vitamina D e o melhor indicador do status corporal dessa vitamina. Atua na absorção de cálcio e fósforo, saúde óssea, modulação imunológica e função muscular. Deficiência (<20 ng/mL) causa raquitismo em crianças e osteomalácia em adultos, além de aumentar risco de osteoporose e fraturas. Insuficiência (20-29 ng/mL) é muito prevalente. Fontes incluem exposição solar (síntese cutânea), alimentos fortificados e suplementação. Excesso (>100 ng/mL) pode causar hipercalcemia."},
    {"name": "Vitamina B12", "code": "B12", "unit": "pg/mL", "category": "Vitaminas e Minerais",
     "ref_min_male": 200, "ref_max_male": 900, "ref_min_female": 200, "ref_max_female": 900,
     "aliases": "Cobalamina,Vitamin B12,Cianocobalamina",
     "description": "A vitamina B12 (cobalamina) é essencial para a síntese de DNA, mielinização dos nervos e maturação dos eritrócitos. Sua deficiência causa anemia megaloblástica (VCM elevado) e neuropatia periférica (parestesias, ataxia), podendo ser irreversível se não tratada. Causas de deficiência incluem dieta vegetariana/vegana estrita, anemia perniciosa (autoimune), uso crônico de metformina ou inibidores de bomba de prótons, e cirurgia bariátrica. Valores muito elevados (>1000) sem suplementação podem indicar doenças mieloproliferativas ou hepatopatia."},
    {"name": "Ácido Fólico", "code": "FOLATO", "unit": "ng/mL", "category": "Vitaminas e Minerais",
     "ref_min_male": 3.0, "ref_max_male": 17.0, "ref_min_female": 3.0, "ref_max_female": 17.0,
     "aliases": "Folato,Folic Acid,Vitamina B9",
     "description": "O ácido fólico (vitamina B9) é essencial para a síntese de DNA e divisão celular, sendo crítico durante períodos de crescimento rápido. Sua deficiência causa anemia megaloblástica (semelhante à deficiência de B12) e, na gestação, aumenta significativamente o risco de defeitos do tubo neural no feto. Fontes alimentares incluem folhas verdes escuras, leguminosas e grãos fortificados. Deficiência ocorre por dieta inadequada, alcoolismo, doenças intestinais (doença celíaca) e uso de medicamentos antagonistas (metotrexato, fenitoína)."},
    {"name": "Ferro Sérico", "code": "FE", "unit": "µg/dL", "category": "Vitaminas e Minerais",
     "ref_min_male": 65, "ref_max_male": 175, "ref_min_female": 50, "ref_max_female": 170,
     "aliases": "Ferro,Iron,Serum Iron",
     "description": "O ferro sérico mede a concentração de ferro circulante no sangue, ligado à transferrina. Valores baixos são encontrados na anemia ferropriva (causa mais comum de anemia mundialmente), perdas sanguíneas crônicas, dieta inadequada e má absorção. Valores elevados ocorrem na hemocromatose hereditária, hemossiderose transfusional e hepatopatias agudas. O ferro sérico isolado tem utilidade limitada por grande variação diurna e influência da dieta recente — deve ser interpretado junto com ferritina, transferrina e saturação de transferrina."},
    {"name": "Ferritina", "code": "FERR", "unit": "ng/mL", "category": "Vitaminas e Minerais",
     "ref_min_male": 30, "ref_max_male": 400, "ref_min_female": 13, "ref_max_female": 150,
     "aliases": "Ferritin",
     "description": "A ferritina é a principal proteína de armazenamento de ferro no organismo. É o melhor exame isolado para avaliar as reservas corporais de ferro. Ferritina baixa (<30 ng/mL) é virtualmente diagnóstica de deficiência de ferro, mesmo antes da instalação da anemia. Entretanto, a ferritina também é uma proteína de fase aguda — se eleva em inflamação, infecções, hepatopatias, neoplasias e síndrome metabólica, podendo mascarar deficiência de ferro coexistente. Valores muito elevados (>1000) merecem investigação para hemocromatose, doença hepática ou malignidade."},
    {"name": "Zinco", "code": "ZN", "unit": "µg/dL", "category": "Vitaminas e Minerais",
     "ref_min_male": 70, "ref_max_male": 120, "ref_min_female": 70, "ref_max_female": 120,
     "aliases": "Zinc",
     "description": "O zinco é um mineral essencial que participa como cofator de mais de 300 enzimas no organismo, sendo fundamental para imunidade, cicatrização, síntese de DNA, percepção gustativa e olfativa, e função reprodutiva. Deficiência causa alopecia, diarreia, lesões cutâneas, atraso na cicatrização, hipogonadismo e maior susceptibilidade a infecções. Grupos de risco incluem vegetarianos, alcoolistas, pacientes com doença inflamatória intestinal e cirróticos. A dosagem sérica tem limitações, pois apenas 0.1% do zinco corporal está no plasma."},
    {"name": "Magnésio", "code": "MG", "unit": "mg/dL", "category": "Vitaminas e Minerais",
     "ref_min_male": 1.7, "ref_max_male": 2.2, "ref_min_female": 1.7, "ref_max_female": 2.2,
     "aliases": "Magnesium,Magnesio",
     "description": "O magnésio é o quarto mineral mais abundante no corpo e cofator de mais de 600 reações enzimáticas, incluindo produção de energia (ATP), síntese proteica, função muscular e regulação do sistema nervoso. Hipomagnesemia (<1.7 mg/dL) causa cãibras, tremores, arritmias cardíacas e pode levar a hipocalcemia e hipocalemia refratárias. Causas incluem alcoolismo, uso de diuréticos, diarreia crônica e inibidores de bomba de prótons. Apenas 1% do magnésio corporal está no sangue, limitando a sensibilidade da dosagem sérica."},
    {"name": "Cálcio", "code": "CA", "unit": "mg/dL", "category": "Vitaminas e Minerais",
     "ref_min_male": 8.6, "ref_max_male": 10.2, "ref_min_female": 8.6, "ref_max_female": 10.2,
     "aliases": "Calcium,Calcio",
     "description": "O cálcio é o mineral mais abundante do corpo, com 99% nos ossos e dentes. O 1% restante no sangue é essencial para contração muscular, coagulação, transmissão nervosa e secreção hormonal. Hipercalcemia (>10.5 mg/dL) tem como causas principais o hiperparatireoidismo primário e neoplasias malignas, causando fadiga, poliúria, constipação e confusão. Hipocalcemia (<8.5 mg/dL) causa tetania, parestesias e arritmias. O cálcio total deve ser corrigido pela albumina: cálcio corrigido = cálcio total + 0.8 × (4.0 - albumina)."},
    {"name": "Sódio", "code": "NA", "unit": "mEq/L", "category": "Vitaminas e Minerais",
     "ref_min_male": 136, "ref_max_male": 145, "ref_min_female": 136, "ref_max_female": 145,
     "aliases": "Sodium,Sodio",
     "description": "O sódio é o principal cátion do líquido extracelular, fundamental para manutenção do volume sanguíneo, equilíbrio hídrico e transmissão nervosa. Hiponatremia (<136 mEq/L) é o distúrbio eletrolítico mais comum em pacientes hospitalizados, podendo causar cefaleia, náusea, confusão e, em casos graves, edema cerebral e convulsões. Causas incluem SIADH, insuficiência cardíaca, cirrose e uso de diuréticos tiazídicos. Hipernatremia (>145 mEq/L) indica déficit de água livre (desidratação), diabetes insípido ou ingestão excessiva de sódio."},
    {"name": "Potássio", "code": "K", "unit": "mEq/L", "category": "Vitaminas e Minerais",
     "ref_min_male": 3.5, "ref_max_male": 5.1, "ref_min_female": 3.5, "ref_max_female": 5.1,
     "aliases": "Potassium,Potassio",
     "description": "O potássio é o principal cátion intracelular, essencial para a excitabilidade neuromuscular e função cardíaca. Tanto a hipocalemia (<3.5 mEq/L) quanto a hipercalemia (>5.1 mEq/L) são potencialmente fatais por risco de arritmias cardíacas. Hipocalemia ocorre por perdas gastrointestinais (diarreia, vômitos), uso de diuréticos e hiperaldosteronismo. Hipercalemia é comum na insuficiência renal, uso de IECA/BRA, espironolactona e acidose metabólica. Pseudohipercalemia por hemólise da amostra é um artefato frequente."},

    # ===== HORMONAL =====
    {"name": "Testosterona Total", "code": "TESTO", "unit": "ng/dL", "category": "Hormonal",
     "ref_min_male": 249, "ref_max_male": 836, "ref_min_female": 8, "ref_max_female": 60,
     "aliases": "Testosterone,Testosterona",
     "description": "A testosterona é o principal hormônio androgênico, produzido pelos testículos (95%) e adrenais. Em homens, é responsável pelo desenvolvimento sexual, massa muscular, densidade óssea, produção de espermatozoides e libido. Níveis baixos (hipogonadismo) causam fadiga, perda de massa muscular, disfunção erétil, depressão e osteoporose. Decli de ~1-2% ao ano após os 30 anos. A dosagem deve ser realizada pela manhã (pico circadiano). Em mulheres, excesso de testosterona indica SOP, tumores adrenais ou ovarianos."},
    {"name": "Testosterona Livre", "code": "TESTOL", "unit": "pg/mL", "category": "Hormonal",
     "ref_min_male": 4.5, "ref_max_male": 42, "ref_min_female": 0.3, "ref_max_female": 4.1,
     "aliases": "Free Testosterone",
     "description": "A testosterona livre corresponde à fração da testosterona que não está ligada a proteínas (SHBG ou albumina), representando apenas 2-3% do total mas sendo a fração biologicamente ativa nos tecidos. É especialmente útil quando a SHBG está alterada (elevada por envelhecimento, cirrose, hipertireoidismo ou uso de anticonvulsivantes; diminuída por obesidade, hipotireoidismo e uso de androgênios), situações em que a testosterona total pode não refletir adequadamente o status androgênico real."},
    {"name": "Estradiol", "code": "E2", "unit": "pg/mL", "category": "Hormonal",
     "ref_min_male": 11, "ref_max_male": 44, "ref_min_female": 19, "ref_max_female": 357,
     "aliases": "Estradiol,E2,Estrogênio",
     "description": "O estradiol é o principal e mais potente estrogênio, produzido pelos ovários nas mulheres e por aromatização da testosterona em ambos os sexos. Em mulheres, regula o ciclo menstrual, fertilidade, saúde óssea e cardiovascular. Valores variam conforme a fase do ciclo e menopausa. Em homens, o estradiol é essencial para saúde óssea e metabolismo lipídico, mas elevações excessivas (por obesidade ou uso de testosterona) podem causar ginecomastia e retenção hídrica. A relação testosterona/estradiol é clinicamente relevante."},
    {"name": "DHEA-S", "code": "DHEAS", "unit": "µg/dL", "category": "Hormonal",
     "ref_min_male": 80, "ref_max_male": 560, "ref_min_female": 35, "ref_max_female": 430,
     "aliases": "DHEA Sulfato,DHEA-SO4",
     "description": "O DHEA-S (sulfato de deidroepiandrosterona) é o hormônio esteroide mais abundante no corpo, produzido quase exclusivamente pelas glândulas adrenais. É precursor de androgênios e estrogênios. Níveis muito elevados em mulheres sugerem tumor adrenal ou hiperplasia adrenal congênita, sendo útil na investigação de hiperandrogenismo. Seus níveis declinam progressivamente com a idade (declínio de ~2% ao ano após os 30), sendo considerado um marcador de envelhecimento adrenal (adrenopausa). Baixos níveis estão associados a fadiga, perda de libido e depressão."},
    {"name": "Cortisol", "code": "CORT", "unit": "µg/dL", "category": "Hormonal",
     "ref_min_male": 6.2, "ref_max_male": 19.4, "ref_min_female": 6.2, "ref_max_female": 19.4,
     "aliases": "Cortisol Matinal,Cortisol Sérico",
     "description": "O cortisol é o principal glicocorticoide, produzido pelas adrenais sob controle do ACTH hipofisário, com ritmo circadiano (pico matinal 6-8h, nadir à meia-noite). Tem ações no metabolismo da glicose, resposta ao estresse, imunidade e pressão arterial. Excesso crônico (Síndrome de Cushing) causa obesidade central, estrias violáceas, hipertensão, diabetes e osteoporose. Deficiência (Insuficiência Adrenal/Doença de Addison) causa fadiga extrema, hipotensão, hipoglicemia e hiperpigmentação. A coleta matinal é obrigatória para interpretação adequada."},
    {"name": "IGF-1", "code": "IGF1", "unit": "ng/mL", "category": "Hormonal",
     "ref_min_male": 115, "ref_max_male": 355, "ref_min_female": 115, "ref_max_female": 355,
     "aliases": "Somatomedina C,Insulin-like Growth Factor 1",
     "description": "O IGF-1 (Fator de Crescimento Semelhante à Insulina tipo 1) é produzido pelo fígado em resposta ao hormônio do crescimento (GH). Por ter meia-vida mais longa e níveis mais estáveis que o GH, é o melhor marcador para avaliar a secreção de GH. Valores elevados sugerem acromegalia (tumor hipofisário produtor de GH). Valores baixos podem indicar deficiência de GH, desnutrição, hepatopatia ou hipotireoidismo. Os valores de referência variam significativamente com a idade, sendo mais altos na puberdade e declinando progressivamente."},
    {"name": "PSA Total", "code": "PSA", "unit": "ng/mL", "category": "Hormonal",
     "ref_min_male": None, "ref_max_male": 4.0, "ref_min_female": None, "ref_max_female": None,
     "aliases": "Antígeno Prostático Específico,Prostate Specific Antigen",
     "description": "O PSA (Antígeno Prostático Específico) é uma protease produzida pelas células epiteliais da próstata. É usado como marcador de triagem para câncer de próstata, embora não seja específico para câncer — também se eleva em hiperplasia prostática benigna (HPB), prostatite, após ejaculação recente e manipulação prostática. Valores >4.0 ng/mL merecem investigação, mas a decisão de biópsia considera também a relação PSA livre/total (<15% sugere câncer), velocidade de aumento do PSA e densidade (PSA/volume prostático). A triagem é recomendada a partir dos 50 anos (45 anos para alto risco)."},
    {"name": "Prolactina", "code": "PRL", "unit": "ng/mL", "category": "Hormonal",
     "ref_min_male": 4.0, "ref_max_male": 15.2, "ref_min_female": 4.8, "ref_max_female": 23.3,
     "aliases": "Prolactin",
     "description": "A prolactina é um hormônio hipofisário cuja principal função é estimular a produção de leite (lactação). Hiperprolactinemia pode ser fisiológica (gravidez, amamentação), farmacológica (antipsicóticos, metoclopramida, antidepressivos) ou patológica (prolactinoma — tumor hipofisário). Em mulheres causa galactorreia, amenorreia e infertilidade. Em homens causa hipogonadismo, disfunção erétil e ginecomastia. Valores >200 ng/mL são altamente sugestivos de macroprolactinoma. O estresse e a punção venosa podem causar elevação transitória."},
    {"name": "LH", "code": "LH", "unit": "mUI/mL", "category": "Hormonal",
     "ref_min_male": 1.7, "ref_max_male": 8.6, "ref_min_female": 2.4, "ref_max_female": 12.6,
     "aliases": "Hormônio Luteinizante,Luteinizing Hormone",
     "description": "O LH (Hormônio Luteinizante) é produzido pela hipófise e tem papel crucial na função reprodutiva. Em mulheres, o pico de LH no meio do ciclo desencadeia a ovulação e estimula a produção de progesterona pelo corpo lúteo. Em homens, estimula as células de Leydig nos testículos a produzir testosterona. LH elevado com testosterona/estradiol baixos indica hipogonadismo primário (falha gonadal). LH baixo com hormônios sexuais baixos indica hipogonadismo secundário/terciário (falha hipofisária/hipotalâmica). A relação LH/FSH é útil no diagnóstico de SOP."},
    {"name": "FSH", "code": "FSH", "unit": "mUI/mL", "category": "Hormonal",
     "ref_min_male": 1.5, "ref_max_male": 12.4, "ref_min_female": 3.5, "ref_max_female": 12.5,
     "aliases": "Hormônio Folículo Estimulante,Follicle Stimulating Hormone",
     "description": "O FSH (Hormônio Folículo Estimulante) é produzido pela hipófise e essencial para a gametogênese. Em mulheres, estimula o crescimento dos folículos ovarianos e a produção de estradiol. FSH elevado (>25 mUI/mL) na fase folicular indica reserva ovariana diminuída ou menopausa. Em homens, estimula a espermatogênese nas células de Sertoli. FSH elevado com testosterona baixa indica hipogonadismo primário. FSH baixo com esteroides sexuais baixos sugere causa hipofisária. É um marcador chave de reserva ovariana (junto com AMH) na avaliação de fertilidade."},

    # ===== INFLAMAÇÃO =====
    {"name": "PCR (Proteína C Reativa)", "code": "PCR", "unit": "mg/L", "category": "Inflamação",
     "ref_min_male": None, "ref_max_male": 3.0, "ref_min_female": None, "ref_max_female": 3.0,
     "aliases": "Proteína C Reativa,CRP,C-Reactive Protein,PCR Ultrassensível",
     "description": "A Proteína C Reativa é uma proteína de fase aguda produzida pelo fígado em resposta à inflamação. Na forma ultrassensível (PCR-us), é um marcador de inflamação sistêmica de baixo grau e preditor independente de risco cardiovascular: <1.0 mg/L (baixo risco), 1.0-3.0 (risco moderado), >3.0 (alto risco). Valores >10 mg/L geralmente indicam infecção bacteriana aguda, doença autoimune ativa ou trauma significativo. Eleva-se em 6-8 horas após o estímulo inflamatório e tem meia-vida curta (~19h), sendo útil para monitorar resposta ao tratamento."},
    {"name": "VHS", "code": "VHS", "unit": "mm/h", "category": "Inflamação",
     "ref_min_male": None, "ref_max_male": 15, "ref_min_female": None, "ref_max_female": 20,
     "aliases": "Velocidade de Hemossedimentação,ESR,VSG",
     "description": "A Velocidade de Hemossedimentação mede a taxa de sedimentação dos eritrócitos em uma hora, sendo um marcador inespecífico de inflamação. Eleva-se em infecções, doenças autoimunes (artrite reumatoide, LES, polimialgia reumática), neoplasias e anemia. VHS muito elevado (>100 mm/h) sugere mieloma múltiplo, arterite temporal, infecção grave ou malignidade avançada. É mais lenta que a PCR para se alterar e normalizar. Aumenta fisiologicamente com a idade (regra prática: limite = idade/2 para homens, (idade+10)/2 para mulheres)."},
    {"name": "Homocisteína", "code": "HOMO", "unit": "µmol/L", "category": "Inflamação",
     "ref_min_male": 5.0, "ref_max_male": 15.0, "ref_min_female": 5.0, "ref_max_female": 12.0,
     "aliases": "Homocysteine,Homocisteina",
     "description": "A homocisteína é um aminoácido sulfurado intermediário do metabolismo da metionina. Níveis elevados (hiper-homocisteinemia) são fator de risco independente para doença cardiovascular aterosclerótica, tromboembolismo venoso e AVC. As causas mais comuns de elevação são deficiência de vitaminas B6, B12 e ácido fólico, insuficiência renal crônica e polimorfismo MTHFR. Também está associada a declínio cognitivo e demência. A suplementação com B12 e folato reduz os níveis de homocisteína, embora o impacto na redução de eventos cardiovasculares ainda seja debatido."},

    # ===== PROTEÍNAS =====
    {"name": "Proteínas Totais", "code": "PT", "unit": "g/dL", "category": "Proteínas",
     "ref_min_male": 6.0, "ref_max_male": 8.0, "ref_min_female": 6.0, "ref_max_female": 8.0,
     "aliases": "Total Protein,Proteinas Totais",
     "description": "As proteínas totais representam a soma da albumina e das globulinas no soro. Hipoproteinemia ocorre em desnutrição, síndrome nefrótica, hepatopatia crônica, enteropatias perdedoras de proteínas e queimaduras extensas. Hiperproteinemia pode indicar desidratação (causa mais comum), mieloma múltiplo (pico monoclonal de gamaglobulina), infecções crônicas ou doenças autoimunes. A eletroforese de proteínas é indicada quando há alteração das proteínas totais ou inversão da relação albumina/globulina para caracterização diagnóstica."},
    {"name": "Globulinas", "code": "GLOB", "unit": "g/dL", "category": "Proteínas",
     "ref_min_male": 2.0, "ref_max_male": 3.5, "ref_min_female": 2.0, "ref_max_female": 3.5,
     "aliases": "Globulin",
     "description": "As globulinas são um grupo heterogêneo de proteínas plasmáticas que incluem as imunoglobulinas (anticorpos), proteínas de transporte (transferrina, ceruloplasmina), fatores de coagulação e proteínas do complemento. Calculadas por subtração (proteínas totais - albumina). Hiperglobulinemia policlonal ocorre em infecções crônicas, doenças autoimunes e hepatopatias. Hiperglobulinemia monoclonal (pico em gamapatia) sugere mieloma múltiplo ou macroglobulinemia de Waldenström. Hipoglobulinemia pode indicar imunodeficiência (primária ou adquirida)."},

    # ===== BIOMARCADORES ADICIONAIS (previnem mapeamentos errados) =====
    {"name": "Colesterol Não-HDL", "code": "CNHDL", "unit": "mg/dL", "category": "Lipidograma",
     "ref_min_male": None, "ref_max_male": 160, "ref_min_female": None, "ref_max_female": 160,
     "aliases": "Colesterol Nao-HDL,Non-HDL Cholesterol,Col. Não-HDL,Col Nao HDL",
     "description": "O colesterol não-HDL é calculado subtraindo o HDL do colesterol total, representando a soma de todas as lipoproteínas aterogênicas (LDL, VLDL, IDL e Lp(a)). É considerado um preditor de risco cardiovascular superior ao LDL isolado, pois captura todo o colesterol pró-aterogênico. Particularmente útil quando os triglicerídeos estão elevados (>400 mg/dL), situação em que o cálculo do LDL pela fórmula de Friedewald se torna impreciso. A meta de não-HDL é geralmente 30 mg/dL acima da meta de LDL do paciente."},
    {"name": "Glicose Média Estimada", "code": "EAG", "unit": "mg/dL", "category": "Glicemia",
     "ref_min_male": None, "ref_max_male": 117, "ref_min_female": None, "ref_max_female": 117,
     "aliases": "eAG,Estimated Average Glucose,Glicose Media Estimada,Glicemia Média Estimada,Glicemia Media Estimada",
     "description": "A Glicose Média Estimada (eAG) é calculada a partir da hemoglobina glicada pela fórmula: eAG = 28.7 × HbA1c - 46.7. Converte o valor percentual da HbA1c em uma estimativa da glicose média dos últimos 2-3 meses, em mg/dL, facilitando a compreensão pelo paciente. HbA1c de 5.7% corresponde a eAG de ~117 mg/dL (limite de normalidade). HbA1c de 7.0% corresponde a eAG de ~154 mg/dL (meta para maioria dos diabéticos). É uma ferramenta educacional útil para adesão ao tratamento do diabetes."},

    # ===== COAGULAÇÃO =====
    {"name": "Fibrinogênio", "code": "FIBR", "unit": "mg/dL", "category": "Coagulação",
     "ref_min_male": 180, "ref_max_male": 350, "ref_min_female": 180, "ref_max_female": 350,
     "aliases": "Fibrinogênio,Fibrinogenio,Fibrinogen,Fibrinogénio",
     "description": "O fibrinogênio é uma glicoproteína produzida pelo fígado, essencial para a etapa final da cascata de coagulação, sendo convertido em fibrina pela trombina para formar o coágulo. Além de sua função hemostática, é uma importante proteína de fase aguda que se eleva em infecções, inflamações, neoplasias, pós-operatório e tabagismo. Níveis elevados estão associados a maior risco cardiovascular. Hipofibrinogenemia (<150 mg/dL) pode ser hereditária ou adquirida (CIVD, hepatopatia grave, fibrinólise) e causa sangramento. Também é consumido na coagulação intravascular disseminada (CIVD)."},

    # ===== FUNÇÃO PANCREÁTICA =====
    {"name": "Amilase", "code": "AMYL", "unit": "U/L", "category": "Função Pancreática",
     "ref_min_male": 29, "ref_max_male": 103, "ref_min_female": 29, "ref_max_female": 103,
     "aliases": "Amilase,Amylase,Amilase Pancreática,Amilase Total",
     "description": "A amilase é uma enzima digestiva produzida pelo pâncreas (isoforma P) e glândulas salivares (isoforma S), responsável pela digestão do amido. Elevações >3x o limite superior são altamente sugestivas de pancreatite aguda, sendo esse o principal uso clínico. Também se eleva em obstrução biliar, perfuração intestinal, parotidite (caxumba), cetoacidose diabética e insuficiência renal. A macroamilasemia (complexos amilase-imunoglobulina) é uma causa benigna de elevação persistente. A amilase normaliza mais rapidamente que a lipase na pancreatite (2-3 dias vs 7-14 dias)."},
    {"name": "Lipase", "code": "LIPASE", "unit": "U/L", "category": "Função Pancreática",
     "ref_min_male": None, "ref_max_male": 67, "ref_min_female": None, "ref_max_female": 67,
     "aliases": "Lipase,Lipase Pancreática,Pancreatic Lipase",
     "description": "A lipase é uma enzima pancreática que hidrolisa triglicerídeos, sendo mais específica para o pâncreas que a amilase. Elevações >3x o limite superior são diagnósticas de pancreatite aguda quando associadas a quadro clínico compatível. A lipase permanece elevada por mais tempo que a amilase (7-14 dias vs 2-3 dias), sendo mais sensível para pancreatite tardia. Também pode se elevar em insuficiência renal, obstrução intestinal e uso de alguns medicamentos. Atualmente é considerada o marcador preferencial para diagnóstico de pancreatite aguda em relação à amilase."},

    # ===== TIREOIDE (adicional) =====
    {"name": "Anti-TPO", "code": "ATPO", "unit": "UI/mL", "category": "Tireoide",
     "ref_min_male": None, "ref_max_male": 35, "ref_min_female": None, "ref_max_female": 35,
     "aliases": "Anti-TPO,Anticorpo Anti-Tireoperoxidase,Anti-Peroxidase,TPO Antibody,Anticorpos Anti-TPO,Anti TPO",
     "description": "Os anticorpos anti-TPO são dirigidos contra a enzima tireoperoxidase, essencial para a síntese dos hormônios tireoidianos. São o marcador mais sensível de autoimunidade tireoidiana, presentes em >90% dos casos de tireoidite de Hashimoto (causa mais comum de hipotireoidismo) e em 60-80% da doença de Graves. Títulos elevados em pacientes com hipotireoidismo subclínico predizem progressão para hipotireoidismo manifesto. Também são encontrados em 10-15% da população saudável, especialmente mulheres, sem doença tireoidiana clínica. Na gestação, estão associados a maior risco de abortamento e tireoidite pós-parto."},
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
