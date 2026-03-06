"""
Biomarker Correlation Analysis - rule-based clinical correlations.

Computes clinically meaningful ratios, consistency checks, and pattern
detection from a single exam's results. Pure computation, no DB access,
no AI API calls.
"""

STATUS_NORMAL = 'normal'
STATUS_WARNING = 'warning'
STATUS_ALERT = 'alert'
STATUS_INFO = 'info'


def compute_ratios(values, gender='M'):
    """Compute clinically meaningful ratios from biomarker values.

    Args:
        values: dict {biomarker_code: float_value}
        gender: 'M' or 'F'

    Returns:
        list of ratio dicts (only for pairs where both biomarkers present)
    """
    ratios = []

    # TG/HDL - Insulin resistance marker
    if 'TG' in values and 'HDL' in values and values['HDL'] > 0:
        val = round(values['TG'] / values['HDL'], 2)
        if val <= 2.0:
            status, interp = STATUS_NORMAL, 'Baixo risco de resist\u00eancia insul\u00ednica.'
        elif val <= 3.5:
            status, interp = STATUS_WARNING, 'Risco moderado de resist\u00eancia insul\u00ednica. Considerar avalia\u00e7\u00e3o metab\u00f3lica.'
        else:
            status, interp = STATUS_ALERT, 'Risco elevado de resist\u00eancia insul\u00ednica e s\u00edndrome metab\u00f3lica.'
        ratios.append({
            'id': 'tg-hdl',
            'label': 'Raz\u00e3o TG/HDL',
            'value': val,
            'formula': 'TG \u00f7 HDL',
            'interpretation': interp,
            'status': status,
            'codes': ['TG', 'HDL'],
            'ranges': 'Normal: \u22642.0 | Lim\u00edtrofe: 2.0-3.5 | Alto: >3.5',
        })

    # De Ritis ratio (AST/ALT = TGO/TGP) - Liver health
    if 'TGO' in values and 'TGP' in values and values['TGP'] > 0:
        val = round(values['TGO'] / values['TGP'], 2)
        if 0.7 <= val <= 1.3:
            status, interp = STATUS_NORMAL, 'Rela\u00e7\u00e3o normal entre transaminases.'
        elif val < 0.7:
            status, interp = STATUS_WARNING, 'TGP proporcionalmente elevada. Poss\u00edvel esteatose hep\u00e1tica n\u00e3o alco\u00f3lica (NAFLD).'
        elif val <= 2.0:
            status, interp = STATUS_WARNING, 'TGO proporcionalmente elevada. Monitorar fun\u00e7\u00e3o hep\u00e1tica.'
        else:
            status, interp = STATUS_ALERT, 'TGO muito elevada em rela\u00e7\u00e3o a TGP. Poss\u00edvel hepatopatia alco\u00f3lica ou les\u00e3o hep\u00e1tica avan\u00e7ada.'
        ratios.append({
            'id': 'de-ritis',
            'label': '\u00cdndice de De Ritis (TGO/TGP)',
            'value': val,
            'formula': 'TGO \u00f7 TGP',
            'interpretation': interp,
            'status': status,
            'codes': ['TGO', 'TGP'],
            'ranges': 'Normal: 0.7-1.3 | <0.7: NAFLD | >2.0: hepatopatia',
        })

    # NLR - Neutrophil/Lymphocyte ratio - Inflammation
    if 'NEUT' in values and 'LYMPH' in values and values['LYMPH'] > 0:
        val = round(values['NEUT'] / values['LYMPH'], 2)
        if val < 1.0:
            status, interp = STATUS_INFO, 'Linf\u00f3citos predominantes. Poss\u00edvel infec\u00e7\u00e3o viral ou condi\u00e7\u00e3o autoimune.'
        elif val <= 3.0:
            status, interp = STATUS_NORMAL, 'Equil\u00edbrio normal entre neutr\u00f3filos e linf\u00f3citos.'
        elif val <= 6.0:
            status, interp = STATUS_WARNING, 'Inflama\u00e7\u00e3o sist\u00eamica moderada. Pode indicar estresse fisiol\u00f3gico ou infec\u00e7\u00e3o.'
        else:
            status, interp = STATUS_ALERT, 'Inflama\u00e7\u00e3o sist\u00eamica significativa. Investigar causa infecciosa ou inflamat\u00f3ria.'
        ratios.append({
            'id': 'nlr',
            'label': 'Rela\u00e7\u00e3o Neutr\u00f3filo/Linf\u00f3cito (NLR)',
            'value': val,
            'formula': 'NEUT \u00f7 LYMPH',
            'interpretation': interp,
            'status': status,
            'codes': ['NEUT', 'LYMPH'],
            'ranges': 'Normal: 1-3 | Moderado: 3-6 | Alto: >6 | <1: viral',
        })

    # Urea/Creatinine ratio
    if 'UREA' in values and 'CREA' in values and values['CREA'] > 0:
        val = round(values['UREA'] / values['CREA'], 1)
        if 10 <= val <= 20:
            status, interp = STATUS_NORMAL, 'Rela\u00e7\u00e3o ureia/creatinina dentro do esperado.'
        elif val > 20:
            status, interp = STATUS_WARNING, 'Rela\u00e7\u00e3o elevada. Poss\u00edvel desidrata\u00e7\u00e3o, sangramento GI ou dieta hiperproteica.'
        else:
            status, interp = STATUS_WARNING, 'Rela\u00e7\u00e3o baixa. Poss\u00edvel insufici\u00eancia hep\u00e1tica ou desnutri\u00e7\u00e3o proteica.'
        ratios.append({
            'id': 'urea-crea',
            'label': 'Rela\u00e7\u00e3o Ureia/Creatinina',
            'value': val,
            'formula': 'UREA \u00f7 CREA',
            'interpretation': interp,
            'status': status,
            'codes': ['UREA', 'CREA'],
            'ranges': 'Normal: 10-20 | >20: pr\u00e9-renal | <10: hep\u00e1tico',
        })

    # HOMA-IR - Insulin resistance index
    if 'INS' in values and 'GLI' in values and values['GLI'] > 0:
        val = round((values['INS'] * values['GLI']) / 405, 2)
        if val < 2.5:
            status, interp = STATUS_NORMAL, 'Sensibilidade insul\u00ednica normal.'
        elif val <= 3.5:
            status, interp = STATUS_WARNING, 'Resist\u00eancia insul\u00ednica lim\u00edtrofe. Aten\u00e7\u00e3o a dieta e atividade f\u00edsica.'
        else:
            status, interp = STATUS_ALERT, 'Resist\u00eancia insul\u00ednica significativa. Risco aumentado de diabetes tipo 2.'
        ratios.append({
            'id': 'homa-ir',
            'label': 'HOMA-IR',
            'value': val,
            'formula': '(INS \u00d7 GLI) \u00f7 405',
            'interpretation': interp,
            'status': status,
            'codes': ['INS', 'GLI'],
            'ranges': 'Normal: <2.5 | Lim\u00edtrofe: 2.5-3.5 | Alto: >3.5',
        })

    return ratios


def compute_consistency_checks(values):
    """Check for inconsistencies between related biomarkers.

    Args:
        values: dict {biomarker_code: float_value}

    Returns:
        list of inconsistency dicts (empty if all checks pass)
    """
    checks = []

    # HCT should be ~3x HGB
    if 'HCT' in values and 'HGB' in values and values['HGB'] > 0:
        ratio = values['HCT'] / values['HGB']
        if ratio < 2.7 or ratio > 3.3:
            checks.append({
                'id': 'hct-hgb-ratio',
                'label': 'Propor\u00e7\u00e3o HCT/HGB',
                'message': 'A rela\u00e7\u00e3o entre hemat\u00f3crito e hemoglobina est\u00e1 fora do esperado. '
                           'Pode indicar erro de coleta, interfer\u00eancia anal\u00edtica ou condi\u00e7\u00e3o cl\u00ednica espec\u00edfica.',
                'status': STATUS_WARNING,
                'codes': ['HCT', 'HGB'],
                'details': 'HCT/HGB = {:.1f} (esperado: 2.7-3.3)'.format(ratio),
            })

    # Direct bilirubin should be less than total
    if 'BILD' in values and 'BILT' in values:
        if values['BILD'] >= values['BILT'] and values['BILT'] > 0:
            checks.append({
                'id': 'bild-bilt',
                'label': 'Bilirrubina Direta \u2265 Total',
                'message': 'A bilirrubina direta n\u00e3o pode ser maior ou igual \u00e0 total. '
                           'Prov\u00e1vel erro anal\u00edtico ou troca de valores.',
                'status': STATUS_ALERT,
                'codes': ['BILD', 'BILT'],
                'details': 'BILD = {:.2f} | BILT = {:.2f}'.format(values['BILD'], values['BILT']),
            })

    # CT ~= HDL + LDL + VLDL (Friedewald)
    if all(c in values for c in ('CT', 'HDL', 'LDL', 'VLDL')):
        expected = values['HDL'] + values['LDL'] + values['VLDL']
        if expected > 0:
            deviation = abs(values['CT'] - expected) / expected * 100
            if deviation > 15:
                checks.append({
                    'id': 'lipid-sum',
                    'label': 'Consist\u00eancia do Lipidograma',
                    'message': 'A soma HDL + LDL + VLDL diverge significativamente do colesterol total. '
                               'Verificar se os valores foram extra\u00eddos corretamente.',
                    'status': STATUS_WARNING,
                    'codes': ['CT', 'HDL', 'LDL', 'VLDL'],
                    'details': 'CT = {:.0f} | HDL+LDL+VLDL = {:.0f} (desvio: {:.1f}%)'.format(
                        values['CT'], expected, deviation),
                })

    # VLDL ~= TG/5 (Friedewald estimate)
    if 'VLDL' in values and 'TG' in values and values['TG'] > 0:
        expected_vldl = values['TG'] / 5
        if expected_vldl > 0:
            deviation = abs(values['VLDL'] - expected_vldl) / expected_vldl * 100
            if deviation > 30:
                checks.append({
                    'id': 'vldl-tg',
                    'label': 'VLDL vs TG/5 (Friedewald)',
                    'message': 'O VLDL medido diverge da estimativa de Friedewald (TG/5). '
                               'Pode indicar hipertrigliceridemia severa ou erro anal\u00edtico.',
                    'status': STATUS_WARNING,
                    'codes': ['VLDL', 'TG'],
                    'details': 'VLDL = {:.0f} | TG/5 = {:.0f} (desvio: {:.1f}%)'.format(
                        values['VLDL'], expected_vldl, deviation),
                })

    # PT ~= ALB + GLOB
    if all(c in values for c in ('PT', 'ALB', 'GLOB')):
        expected_pt = values['ALB'] + values['GLOB']
        if expected_pt > 0:
            deviation = abs(values['PT'] - expected_pt) / expected_pt * 100
            if deviation > 10:
                checks.append({
                    'id': 'pt-alb-glob',
                    'label': 'Prote\u00edna Total vs ALB + GLOB',
                    'message': 'A prote\u00edna total diverge da soma albumina + globulinas. '
                               'Verificar valores extra\u00eddos.',
                    'status': STATUS_WARNING,
                    'codes': ['PT', 'ALB', 'GLOB'],
                    'details': 'PT = {:.1f} | ALB+GLOB = {:.1f} (desvio: {:.1f}%)'.format(
                        values['PT'], expected_pt, deviation),
                })

    # FE low + FERR high = inflammation masking iron deficiency
    if 'FE' in values and 'FERR' in values:
        # Use approximate normal ranges: FE > 60 normal, FERR < 300 normal
        if values['FE'] < 60 and values['FERR'] > 300:
            checks.append({
                'id': 'fe-ferr-discordance',
                'label': 'Ferro Baixo + Ferritina Alta',
                'message': 'Ferro s\u00e9rico baixo com ferritina elevada sugere inflama\u00e7\u00e3o '
                           'mascarando defici\u00eancia de ferro (anemia de doen\u00e7a cr\u00f4nica).',
                'status': STATUS_ALERT,
                'codes': ['FE', 'FERR'],
                'details': 'FE = {:.0f} (baixo) | FERR = {:.0f} (alto)'.format(
                    values['FE'], values['FERR']),
            })

    return checks


def compute_clinical_patterns(values, gender='M', refs=None):
    """Detect clinically meaningful patterns from biomarker combinations.

    Args:
        values: dict {biomarker_code: float_value}
        gender: 'M' or 'F'
        refs: dict {biomarker_code: (ref_min, ref_max)} or None

    Returns:
        list of detected pattern dicts (empty if no patterns found)
    """
    if refs is None:
        refs = {}
    patterns = []

    # Helper: check if value is above ref_max
    def _above_max(code):
        if code not in values or code not in refs:
            return False
        ref_max = refs[code][1]
        return ref_max is not None and values[code] > ref_max

    def _below_min(code):
        if code not in values or code not in refs:
            return False
        ref_min = refs[code][0]
        return ref_min is not None and values[code] < ref_min

    # Metabolic Syndrome: >= 3 criteria
    ms_criteria_met = []
    ms_criteria_total = 0

    if 'TG' in values:
        ms_criteria_total += 1
        if values['TG'] > 150:
            ms_criteria_met.append('Triglicer\u00eddeos > 150 mg/dL (atual: {:.0f})'.format(values['TG']))

    if 'HDL' in values:
        ms_criteria_total += 1
        hdl_threshold = 40 if gender == 'M' else 50
        if values['HDL'] < hdl_threshold:
            ms_criteria_met.append('HDL < {} mg/dL (atual: {:.0f})'.format(hdl_threshold, values['HDL']))

    if 'GLI' in values:
        ms_criteria_total += 1
        if values['GLI'] > 100:
            ms_criteria_met.append('Glicemia > 100 mg/dL (atual: {:.0f})'.format(values['GLI']))

    if 'HBA1C' in values:
        ms_criteria_total += 1
        if values['HBA1C'] > 5.7:
            ms_criteria_met.append('HbA1c > 5.7% (atual: {:.1f})'.format(values['HBA1C']))

    if 'TG' in values and 'HDL' in values and values['HDL'] > 0:
        ms_criteria_total += 1
        tg_hdl = values['TG'] / values['HDL']
        if tg_hdl > 3.5:
            ms_criteria_met.append('Raz\u00e3o TG/HDL > 3.5 (atual: {:.1f})'.format(tg_hdl))

    if ms_criteria_total >= 3:
        if len(ms_criteria_met) >= 3:
            patterns.append({
                'id': 'metabolic-syndrome',
                'label': 'Indicadores de S\u00edndrome Metab\u00f3lica',
                'description': 'M\u00faltiplos marcadores metab\u00f3licos alterados simultaneamente, '
                               'sugerindo risco cardiovascular e de diabetes tipo 2 aumentado.',
                'status': STATUS_ALERT,
                'criteria_met': ms_criteria_met,
                'criteria_total': ms_criteria_total,
                'codes': [c for c in ['TG', 'HDL', 'GLI', 'HBA1C'] if c in values],
            })
        else:
            patterns.append({
                'id': 'metabolic-syndrome',
                'label': 'Indicadores de S\u00edndrome Metab\u00f3lica',
                'description': 'Marcadores metab\u00f3licos avaliados dentro dos par\u00e2metros normais. '
                               'Sem indicadores de s\u00edndrome metab\u00f3lica.',
                'status': STATUS_NORMAL,
                'criteria_met': ['{}/{} crit\u00e9rios alterados'.format(
                    len(ms_criteria_met), ms_criteria_total)],
                'criteria_total': ms_criteria_total,
                'codes': [c for c in ['TG', 'HDL', 'GLI', 'HBA1C'] if c in values],
            })

    # Thyroid function: TSH + T4L
    if 'TSH' in values and 'T4L' in values:
        if _above_max('TSH') and _below_min('T4L'):
            patterns.append({
                'id': 'thyroid',
                'label': 'Fun\u00e7\u00e3o Tireoidiana',
                'description': 'TSH elevado com T4 livre baixo \u00e9 o padr\u00e3o cl\u00e1ssico de '
                               'hipotireoidismo prim\u00e1rio. Recomenda-se avalia\u00e7\u00e3o endocrinol\u00f3gica.',
                'status': STATUS_ALERT,
                'criteria_met': [
                    'TSH elevado: {:.2f} (ref: {})'.format(
                        values['TSH'],
                        '\u2264{:.2f}'.format(refs['TSH'][1]) if refs.get('TSH', (None, None))[1] else '?'),
                    'T4L baixo: {:.2f} (ref: {})'.format(
                        values['T4L'],
                        '\u2265{:.2f}'.format(refs['T4L'][0]) if refs.get('T4L', (None, None))[0] else '?'),
                ],
                'criteria_total': None,
                'codes': ['TSH', 'T4L'],
            })
        elif _below_min('TSH') and _above_max('T4L'):
            patterns.append({
                'id': 'thyroid',
                'label': 'Fun\u00e7\u00e3o Tireoidiana',
                'description': 'TSH suprimido com T4 livre elevado indica hipertireoidismo. '
                               'Investigar doen\u00e7a de Graves ou n\u00f3dulos tireoidianos.',
                'status': STATUS_ALERT,
                'criteria_met': [
                    'TSH suprimido: {:.2f} (ref: {})'.format(
                        values['TSH'],
                        '\u2265{:.2f}'.format(refs['TSH'][0]) if refs.get('TSH', (None, None))[0] else '?'),
                    'T4L elevado: {:.2f} (ref: {})'.format(
                        values['T4L'],
                        '\u2264{:.2f}'.format(refs['T4L'][1]) if refs.get('T4L', (None, None))[1] else '?'),
                ],
                'criteria_total': None,
                'codes': ['TSH', 'T4L'],
            })
        else:
            patterns.append({
                'id': 'thyroid',
                'label': 'Fun\u00e7\u00e3o Tireoidiana',
                'description': 'TSH e T4 livre dentro dos valores de refer\u00eancia. '
                               'Fun\u00e7\u00e3o tireoidiana normal.',
                'status': STATUS_NORMAL,
                'criteria_met': [
                    'TSH: {:.2f}'.format(values['TSH']),
                    'T4L: {:.2f}'.format(values['T4L']),
                ],
                'criteria_total': None,
                'codes': ['TSH', 'T4L'],
            })

    # Iron metabolism: FE + FERR (± HGB, PCR)
    if 'FE' in values and 'FERR' in values:
        if _below_min('FE') and _below_min('FERR'):
            criteria = [
                'Ferro s\u00e9rico baixo: {:.0f}'.format(values['FE']),
                'Ferritina baixa: {:.0f}'.format(values['FERR']),
            ]
            severity = STATUS_WARNING
            desc = 'Ferro e ferritina baixos indicam deple\u00e7\u00e3o dos estoques de ferro.'
            codes = ['FE', 'FERR']

            if 'HGB' in values and _below_min('HGB'):
                criteria.append('Hemoglobina baixa: {:.1f}'.format(values['HGB']))
                severity = STATUS_ALERT
                desc = ('Ferro, ferritina e hemoglobina baixos configuram anemia ferropriva. '
                        'Recomenda-se investiga\u00e7\u00e3o da causa e suplementa\u00e7\u00e3o.')
                codes.append('HGB')

            patterns.append({
                'id': 'iron-metabolism',
                'label': 'Metabolismo do Ferro',
                'description': desc,
                'status': severity,
                'criteria_met': criteria,
                'criteria_total': None,
                'codes': codes,
            })
        elif _below_min('FE') and _above_max('FERR'):
            criteria = [
                'Ferro s\u00e9rico baixo: {:.0f}'.format(values['FE']),
                'Ferritina elevada: {:.0f}'.format(values['FERR']),
            ]
            codes = ['FE', 'FERR']

            if 'PCR' in values and _above_max('PCR'):
                criteria.append('PCR elevada: {:.1f}'.format(values['PCR']))
                codes.append('PCR')

            patterns.append({
                'id': 'iron-metabolism',
                'label': 'Metabolismo do Ferro',
                'description': 'Ferro baixo com ferritina alta \u00e9 caracter\u00edstico de anemia de doen\u00e7a cr\u00f4nica. '
                               'A ferritina sobe como prote\u00edna de fase aguda, mascarando a defici\u00eancia funcional de ferro.',
                'status': STATUS_WARNING,
                'criteria_met': criteria,
                'criteria_total': None,
                'codes': codes,
            })
        else:
            patterns.append({
                'id': 'iron-metabolism',
                'label': 'Metabolismo do Ferro',
                'description': 'Ferro s\u00e9rico e ferritina dentro dos valores esperados. '
                               'Estoques de ferro adequados.',
                'status': STATUS_NORMAL,
                'criteria_met': [
                    'Ferro: {:.0f}'.format(values['FE']),
                    'Ferritina: {:.0f}'.format(values['FERR']),
                ],
                'criteria_total': None,
                'codes': ['FE', 'FERR'],
            })

    return patterns


def analyze_correlations(last_results, gender='M'):
    """Compute all biomarker correlations for a single exam.

    Args:
        last_results: QuerySet/list of ExamResult (with select_related('biomarker'))
        gender: 'M' or 'F'

    Returns:
        dict with 'ratios', 'consistency', 'patterns' keys, or None if no results.
    """
    if not last_results:
        return None

    values_by_code = {}
    refs_by_code = {}
    for r in last_results:
        code = r.biomarker.code
        values_by_code[code] = float(r.value)
        refs_by_code[code] = (
            float(r.ref_min) if r.ref_min is not None else None,
            float(r.ref_max) if r.ref_max is not None else None,
        )

    ratios = compute_ratios(values_by_code, gender)
    consistency = compute_consistency_checks(values_by_code)
    clinical_patterns = compute_clinical_patterns(values_by_code, gender, refs_by_code)

    if not ratios and not consistency and not clinical_patterns:
        return None

    return {
        'ratios': ratios,
        'consistency': consistency,
        'patterns': clinical_patterns,
    }
