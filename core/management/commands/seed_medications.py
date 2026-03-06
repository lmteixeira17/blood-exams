"""
Seed common medications, vitamins, supplements, and hormones.
"""
from django.core.management.base import BaseCommand

from core.models import Medication

MEDICATIONS = [
    # Vitaminas
    {"name": "Vitamina D3 (Colecalciferol)", "type": "vitamin", "common_doses": "1000 UI, 2000 UI, 5000 UI, 10000 UI, 50000 UI", "affects_biomarkers": "Vitamina D (25-OH), C\u00e1lcio"},
    {"name": "Vitamina B12 (Cianocobalamina)", "type": "vitamin", "common_doses": "500 mcg, 1000 mcg, 5000 mcg", "affects_biomarkers": "Vitamina B12, Homociste\u00edna"},
    {"name": "Vitamina C (\u00c1cido Asc\u00f3rbico)", "type": "vitamin", "common_doses": "500 mg, 1000 mg, 2000 mg", "affects_biomarkers": ""},
    {"name": "Vitamina K2 (MK-7)", "type": "vitamin", "common_doses": "100 mcg, 200 mcg", "affects_biomarkers": "Tempo de Protrombina"},
    {"name": "Vitamina E (Tocoferol)", "type": "vitamin", "common_doses": "400 UI, 800 UI", "affects_biomarkers": ""},
    {"name": "Vitamina A (Retinol)", "type": "vitamin", "common_doses": "5000 UI, 10000 UI", "affects_biomarkers": "TGO, TGP"},
    {"name": "Complexo B", "type": "vitamin", "common_doses": "1 comprimido", "affects_biomarkers": "Vitamina B12, \u00c1cido F\u00f3lico"},
    {"name": "\u00c1cido F\u00f3lico (Vitamina B9)", "type": "vitamin", "common_doses": "400 mcg, 5 mg", "affects_biomarkers": "\u00c1cido F\u00f3lico, Homociste\u00edna"},
    {"name": "Biotina (Vitamina B7)", "type": "vitamin", "common_doses": "2500 mcg, 5000 mcg, 10000 mcg", "affects_biomarkers": "TSH, T3, T4 (interfer\u00eancia em imunoensaios)"},

    # Minerais / Suplementos
    {"name": "Zinco", "type": "supplement", "common_doses": "15 mg, 30 mg, 50 mg", "affects_biomarkers": "Zinco"},
    {"name": "Magn\u00e9sio (Quelato/Dimalato)", "type": "supplement", "common_doses": "200 mg, 400 mg, 500 mg", "affects_biomarkers": "Magn\u00e9sio"},
    {"name": "Ferro (Sulfato Ferroso)", "type": "supplement", "common_doses": "40 mg, 60 mg, 300 mg", "affects_biomarkers": "Ferro S\u00e9rico, Ferritina, Transfer\u00edna, Hemoglobina"},
    {"name": "Ferro (Bisglicinato)", "type": "supplement", "common_doses": "14 mg, 28 mg", "affects_biomarkers": "Ferro S\u00e9rico, Ferritina, Transfer\u00edna, Hemoglobina"},
    {"name": "C\u00e1lcio", "type": "supplement", "common_doses": "500 mg, 600 mg, 1000 mg", "affects_biomarkers": "C\u00e1lcio Total, C\u00e1lcio I\u00f4nico"},
    {"name": "Sel\u00eanio", "type": "supplement", "common_doses": "50 mcg, 100 mcg, 200 mcg", "affects_biomarkers": ""},
    {"name": "Creatina", "type": "supplement", "common_doses": "3 g, 5 g", "affects_biomarkers": "Creatinina"},
    {"name": "\u00d4mega 3 (EPA/DHA)", "type": "supplement", "common_doses": "1000 mg, 2000 mg, 3000 mg", "affects_biomarkers": "Triglicer\u00eddeos, Colesterol"},
    {"name": "Coenzima Q10 (CoQ10)", "type": "supplement", "common_doses": "100 mg, 200 mg, 300 mg", "affects_biomarkers": ""},
    {"name": "Probi\u00f3ticos", "type": "supplement", "common_doses": "1 c\u00e1psula", "affects_biomarkers": ""},
    {"name": "Whey Protein", "type": "supplement", "common_doses": "25 g, 30 g", "affects_biomarkers": "Prote\u00ednas Totais, Albumina, Creatinina, Ureia"},
    {"name": "Col\u00e1geno", "type": "supplement", "common_doses": "5 g, 10 g", "affects_biomarkers": ""},
    {"name": "Ashwagandha", "type": "supplement", "common_doses": "300 mg, 600 mg", "affects_biomarkers": "Cortisol, TSH"},
    {"name": "Melatonina", "type": "supplement", "common_doses": "0.5 mg, 1 mg, 3 mg, 5 mg, 10 mg", "affects_biomarkers": ""},
    {"name": "Curcumina", "type": "supplement", "common_doses": "500 mg, 1000 mg", "affects_biomarkers": "PCR"},
    {"name": "NAC (N-Acetilciste\u00edna)", "type": "supplement", "common_doses": "600 mg, 1200 mg", "affects_biomarkers": "TGO, TGP, GGT"},
    {"name": "Resveratrol", "type": "supplement", "common_doses": "250 mg, 500 mg", "affects_biomarkers": ""},
    {"name": "Spirulina", "type": "supplement", "common_doses": "500 mg, 1000 mg, 3000 mg", "affects_biomarkers": ""},

    # Horm\u00f4nios
    {"name": "Testosterona (Cipionato)", "type": "hormone", "common_doses": "100 mg, 150 mg, 200 mg/semana", "affects_biomarkers": "Testosterona Total, Testosterona Livre, DHT, Estradiol, SHBG, Hemat\u00f3crito, Hemoglobina, PSA"},
    {"name": "Testosterona (Enantato)", "type": "hormone", "common_doses": "100 mg, 150 mg, 200 mg/semana", "affects_biomarkers": "Testosterona Total, Testosterona Livre, DHT, Estradiol, SHBG, Hemat\u00f3crito, Hemoglobina, PSA"},
    {"name": "Testosterona (Gel/Creme)", "type": "hormone", "common_doses": "25 mg, 50 mg/dia", "affects_biomarkers": "Testosterona Total, Testosterona Livre, DHT, Estradiol"},
    {"name": "HCG (Gonadotrofina Cori\u00f4nica)", "type": "hormone", "common_doses": "250 UI, 500 UI, 1000 UI", "affects_biomarkers": "LH, FSH, Testosterona, Estradiol"},
    {"name": "Anastrozol", "type": "medication", "common_doses": "0.25 mg, 0.5 mg, 1 mg", "affects_biomarkers": "Estradiol"},
    {"name": "Levotiroxina (T4)", "type": "hormone", "common_doses": "25 mcg, 50 mcg, 75 mcg, 88 mcg, 100 mcg, 112 mcg, 125 mcg, 150 mcg", "affects_biomarkers": "TSH, T4 Livre, T3"},
    {"name": "Liotironina (T3)", "type": "hormone", "common_doses": "5 mcg, 10 mcg, 25 mcg", "affects_biomarkers": "TSH, T3, T4 Livre"},
    {"name": "DHEA", "type": "hormone", "common_doses": "25 mg, 50 mg, 100 mg", "affects_biomarkers": "DHEA-S, Testosterona, Estradiol"},
    {"name": "Pregnenolona", "type": "hormone", "common_doses": "25 mg, 50 mg, 100 mg", "affects_biomarkers": "Progesterona, Cortisol"},
    {"name": "Progesterona", "type": "hormone", "common_doses": "100 mg, 200 mg", "affects_biomarkers": "Progesterona"},
    {"name": "GH (Horm\u00f4nio do Crescimento)", "type": "hormone", "common_doses": "1 UI, 2 UI, 4 UI", "affects_biomarkers": "IGF-1, GH, Glicemia"},
    {"name": "Insulina", "type": "hormone", "common_doses": "Vari\u00e1vel (UI)", "affects_biomarkers": "Glicemia, HbA1c, Insulina"},
    {"name": "Oxitocina", "type": "hormone", "common_doses": "10 UI, 20 UI", "affects_biomarkers": ""},

    # Medicamentos comuns
    {"name": "Metformina", "type": "medication", "common_doses": "500 mg, 850 mg, 1000 mg", "affects_biomarkers": "Glicemia, HbA1c, Vitamina B12"},
    {"name": "Sinvastatina", "type": "medication", "common_doses": "10 mg, 20 mg, 40 mg", "affects_biomarkers": "Colesterol Total, LDL, HDL, TGO, TGP, CPK"},
    {"name": "Atorvastatina", "type": "medication", "common_doses": "10 mg, 20 mg, 40 mg, 80 mg", "affects_biomarkers": "Colesterol Total, LDL, HDL, TGO, TGP, CPK"},
    {"name": "Rosuvastatina", "type": "medication", "common_doses": "5 mg, 10 mg, 20 mg, 40 mg", "affects_biomarkers": "Colesterol Total, LDL, HDL, TGO, TGP, CPK"},
    {"name": "Losartana", "type": "medication", "common_doses": "25 mg, 50 mg, 100 mg", "affects_biomarkers": "Pot\u00e1ssio, Creatinina"},
    {"name": "Enalapril", "type": "medication", "common_doses": "5 mg, 10 mg, 20 mg", "affects_biomarkers": "Pot\u00e1ssio, Creatinina"},
    {"name": "Omeprazol", "type": "medication", "common_doses": "20 mg, 40 mg", "affects_biomarkers": "Vitamina B12, Magn\u00e9sio, Ferro"},
    {"name": "AAS (\u00c1cido Acetilsalic\u00edlico)", "type": "medication", "common_doses": "81 mg, 100 mg, 325 mg", "affects_biomarkers": "Tempo de Sangramento, Plaquetas"},
    {"name": "Finasterida", "type": "medication", "common_doses": "1 mg, 5 mg", "affects_biomarkers": "PSA, DHT, Testosterona"},
    {"name": "Dutasterida", "type": "medication", "common_doses": "0.5 mg", "affects_biomarkers": "PSA, DHT"},
    {"name": "Semaglutida (Ozempic)", "type": "medication", "common_doses": "0.25 mg, 0.5 mg, 1 mg, 2.4 mg/semana", "affects_biomarkers": "Glicemia, HbA1c, Triglicer\u00eddeos, TGO, TGP"},
    {"name": "Tadalafila", "type": "medication", "common_doses": "5 mg, 10 mg, 20 mg", "affects_biomarkers": ""},
    {"name": "Minoxidil (Oral)", "type": "medication", "common_doses": "0.5 mg, 1 mg, 2.5 mg, 5 mg", "affects_biomarkers": ""},
    {"name": "Clomifeno", "type": "medication", "common_doses": "25 mg, 50 mg", "affects_biomarkers": "LH, FSH, Testosterona, Estradiol, SHBG"},
    {"name": "Alopurinol", "type": "medication", "common_doses": "100 mg, 300 mg", "affects_biomarkers": "\u00c1cido \u00darico, TGO, TGP"},
    {"name": "Prednisona", "type": "medication", "common_doses": "5 mg, 10 mg, 20 mg", "affects_biomarkers": "Glicemia, Leuc\u00f3citos, Cortisol"},
]


class Command(BaseCommand):
    help = "Seed the medication catalog with common medications, vitamins, supplements and hormones."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for med_data in MEDICATIONS:
            obj, created = Medication.objects.update_or_create(
                name=med_data["name"],
                defaults={
                    "type": med_data["type"],
                    "common_doses": med_data.get("common_doses", ""),
                    "affects_biomarkers": med_data.get("affects_biomarkers", ""),
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done: {created_count} created, {updated_count} updated. "
            f"Total: {Medication.objects.count()} medications."
        ))
