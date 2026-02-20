"""
OpenAI GPT-4 Vision integration for blood exam processing.

Step 1: Extract biomarker data from uploaded exam (PDF/image) using GPT-4 Vision.
        Catalog-aware: the prompt includes the biomarker catalog so GPT-4 returns codes directly.
Step 2: Validate extracted data (physiological limits, cross-biomarker formulas, etc.)
Step 3: Apply auto-corrections (WBC differential %, BASO estimation).
Step 4: Generate AI analysis comparing current results with historical data.
"""

import base64
import json
import logging
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.conf import settings

logger = logging.getLogger('core')


# =============================================================================
# Prompt template - catalog is injected dynamically at runtime
# =============================================================================

EXTRACTION_PROMPT_TEMPLATE = """Voce e um especialista em exames de sangue. Analise esta imagem de um exame de sangue e extraia TODOS os biomarcadores encontrados.

CATALOGO DE BIOMARCADORES DISPONIVEIS (use o campo "code" para identificar):
{catalog}

Retorne APENAS um JSON valido no seguinte formato (sem markdown, sem texto extra):
{{
    "lab_name": "Nome do laboratorio (se visivel)",
    "exam_date": "YYYY-MM-DD (se visivel, senao null)",
    "biomarkers": [
        {{
            "raw_name": "Nome exatamente como aparece no exame",
            "code": "CODIGO_DO_CATALOGO ou null se nao encontrado",
            "confidence": "high ou low ou none",
            "value": 12.5,
            "unit": "g/dL",
            "ref_min": 12.0,
            "ref_max": 16.0,
            "is_percentage": false
        }}
    ]
}}

REGRAS IMPORTANTES:
- Extraia TODOS os biomarcadores visiveis, nao apenas os principais
- O campo "value" deve ser um numero (float), nao string
- ref_min e ref_max devem ser numeros ou null se nao disponiveis
- Se o valor for "<0.1" ou ">1000", use o numero (0.1 ou 1000)
- Nao invente valores. Se nao conseguir ler, omita o biomarcador

PADRONIZACAO DE UNIDADES (CRITICO - use SEMPRE a unidade do catalogo):
- Se o exame usa unidade diferente da do catalogo, CONVERTA o valor para a unidade do catalogo
- mg/L -> mg/dL: dividir por 10 (ex: Vitamina C 5.3 mg/L = 0.53 mg/dL)
- ug/L -> ng/mL: mesmo valor (1 ug/L = 1 ng/mL)
- nmol/L -> ng/dL (Testosterona): multiplicar por 0.02884
- pmol/L -> pg/mL (T4 Livre, T3 Livre): multiplicar por 0.0777 (T4L) ou 0.651 (T3L)
- umol/L -> mg/dL (Creatinina): dividir por 88.4
- umol/L -> mg/dL (Acido Urico): dividir por 59.48
- mmol/L -> mg/dL (Glicose): multiplicar por 18.02
- mmol/L -> mg/dL (Colesterol): multiplicar por 38.67
- mmol/L -> mg/dL (Triglicerides): multiplicar por 88.57
- O campo "unit" deve ser SEMPRE a unidade do catalogo, nao a do exame original

REGRAS DE CONFIANCA:
- confidence="high": voce tem certeza do match com o catalogo
- confidence="low": o match e ambiguo ou incerto
- confidence="none": nao encontrou no catalogo (code=null)

REGRAS DE CONFUSAO (LEIA COM ATENCAO - erros reais ja ocorridos):
- "DHT" ou "Di-hidrotestosterona" ou "Dihidrotestosterona" -> code="DHT" (pg/mL). NAO confundir com HCT (Hematocrito, %)
- "SHBG" ou "Globulina Ligadora de Hormonios Sexuais" -> code="SHBG" (nmol/L). NAO confundir com GLOB (Globulinas, g/dL) nem com HGB (Hemoglobina, g/dL)
- "Colesterol Nao-HDL" ou "Col. Nao-HDL" ou "Colesterol Nao HDL" -> code="CNHDL" (mg/dL). NAO confundir com CT (Colesterol Total)
- "Glicose Media Estimada" ou "eAG" ou "Glicemia Media Estimada" -> code="EAG" (mg/dL). NAO confundir com GLI (Glicose em Jejum)
- "Calcio Ionico" ou "Ca Ionico" ou "Calcio Ioniado" -> code="CAI" (mmol/L). NAO confundir com CA (Calcio Total, mg/dL). ATENCAO: unidades diferentes!

LEUCOGRAMA DIFERENCIAL (Neutrofilos, Linfocitos, Monocitos, Eosinofilos, Basofilos):
- Se o exame mostra APENAS percentuais (ex: Neutrofilos 58%, Linfocitos 30%), informe is_percentage=true e extraia o valor percentual (58, 30)
- Se mostra valores absolutos (ex: Neutrofilos 4263/mm3), informe is_percentage=false
- Se mostra ambos, prefira o valor absoluto e informe is_percentage=false
- IMPORTANTE: nunca misture. Se extrair percentual, TODOS os componentes do diferencial devem ter is_percentage=true"""


TREND_ANALYSIS_PROMPT = """Voce e um medico especialista em medicina laboratorial. Analise a evolucao historica do biomarcador abaixo e escreva uma analise narrativa da tendencia ao longo do tempo.

**Biomarcador:** {biomarker_name} ({biomarker_code})
**Unidade:** {unit}
**Categoria:** {category}
**Descricao:** {description}
**Faixa de referencia:** {ref_range}

**Dados do Paciente:**
- Sexo: {gender}
- Idade: {age}

**Historico de valores (do mais antigo ao mais recente):**
{history}

Escreva uma analise em texto corrido (2-4 paragrafos) em portugues, cobrindo:
1. Tendencia geral: o valor esta subindo, descendo ou estavel ao longo do periodo?
2. Relacao com a faixa de referencia: os valores estao dentro da normalidade? Houve periodos fora?
3. Mudancas significativas: destaque saltos ou quedas relevantes entre exames consecutivos.
4. Significado clinico: o que essa tendencia pode indicar para a saude do paciente.
5. Se aplicavel, mencione fatores que podem influenciar esse biomarcador (alimentacao, exercicio, medicamentos comuns).

IMPORTANTE:
- Escreva em portugues brasileiro, de forma clara e acessivel.
- Use um tom informativo e educacional, nao alarmista.
- Nao faca diagnosticos. Use expressoes como "pode indicar", "sugere", "vale acompanhar".
- Inclua o disclaimer que a analise e informativa e nao substitui consulta medica.
- Retorne APENAS o texto da analise, sem JSON, sem markdown headers.
- Use paragrafos separados por linha em branco."""


ANALYSIS_PROMPT_TEMPLATE = """Voce e um medico especialista em medicina laboratorial. Analise os resultados de exames de sangue abaixo e forneca uma analise completa.

**Dados do Paciente:**
- Sexo: {gender}
- Idade: {age}

**Resultados Atuais ({exam_date}):**
{current_results}

{historical_section}

Retorne APENAS um JSON valido (sem markdown, sem texto extra):
{{
    "summary": "Resumo geral da saude do paciente em 3-5 frases. Mencione aspectos positivos e pontos de atencao.",
    "alerts": [
        {{
            "biomarker": "Nome do biomarcador",
            "value": "valor atual com unidade",
            "status": "alto" ou "baixo",
            "message": "Explicacao breve do significado clinico"
        }}
    ],
    "improvements": [
        {{
            "biomarker": "Nome do biomarcador",
            "previous": "valor anterior",
            "current": "valor atual",
            "message": "O que melhorou"
        }}
    ],
    "deteriorations": [
        {{
            "biomarker": "Nome do biomarcador",
            "previous": "valor anterior",
            "current": "valor atual",
            "message": "O que piorou"
        }}
    ],
    "recommendations": "Recomendacoes gerais em formato de texto (3-5 pontos). Inclua recomendacoes de estilo de vida, alimentacao e acompanhamento medico.",
    "comparison_text": "Texto comparativo com exames anteriores. Se nao houver historico, deixe vazio."
}}

IMPORTANTE: Esta analise e apenas informativa e nao substitui a consulta com um medico."""


def build_catalog_table():
    """Build compact catalog string for GPT-4 prompt injection."""
    from .models import Biomarker
    lines = []
    for bm in Biomarker.objects.all().order_by('category', 'code'):
        aliases_str = ''
        if bm.aliases:
            aliases_str = f' | aliases: {bm.aliases}'
        lines.append(f'  {bm.code} | {bm.name} | {bm.unit}{aliases_str}')
    return '\n'.join(lines)


def get_openai_client():
    """Get OpenAI client instance."""
    try:
        import openai
        return openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    except ImportError:
        logger.error("openai package not installed")
        raise
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {e}")
        raise


def image_to_base64(image_bytes):
    """Convert image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode('utf-8')


def pdf_to_images(file_bytes):
    """Convert PDF bytes to list of image bytes (PNG)."""
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes, dpi=200, fmt='png')
        result = []
        for img in images:
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            result.append(buffer.getvalue())
        return result
    except ImportError:
        logger.error("pdf2image package not installed")
        raise
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        raise


def extract_biomarkers_from_file(file_obj, file_type):
    """
    Extract biomarker data from an uploaded file using GPT-4 Vision.
    Catalog-aware: includes the biomarker catalog in the prompt so GPT-4
    returns catalog codes directly.

    Args:
        file_obj: Django UploadedFile or file-like object
        file_type: 'pdf' or 'image'

    Returns:
        dict with keys: lab_name, exam_date, biomarkers
    """
    client = get_openai_client()
    file_bytes = file_obj.read()

    if file_type == 'pdf':
        images = pdf_to_images(file_bytes)
    else:
        images = [file_bytes]

    # Build catalog-aware prompt
    catalog_table = build_catalog_table()
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(catalog=catalog_table)

    all_biomarkers = []
    lab_name = ''
    exam_date = None

    for i, img_bytes in enumerate(images):
        b64 = image_to_base64(img_bytes)

        # Detect mime type
        if file_type == 'pdf' or img_bytes[:4] == b'\x89PNG':
            mime = 'image/png'
        elif img_bytes[:2] == b'\xff\xd8':
            mime = 'image/jpeg'
        else:
            mime = 'image/png'

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{b64}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ]

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                max_tokens=4096,
                temperature=0.1,
            )

            content = response.choices[0].message.content.strip()
            # Clean markdown code blocks if present
            if content.startswith('```'):
                content = content.split('\n', 1)[1] if '\n' in content else content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()

            data = json.loads(content)

            if data.get('lab_name') and not lab_name:
                lab_name = data['lab_name']
            if data.get('exam_date') and not exam_date:
                exam_date = data['exam_date']

            all_biomarkers.extend(data.get('biomarkers', []))

            logger.info(
                f"Page {i+1}: extracted {len(data.get('biomarkers', []))} biomarkers, "
                f"tokens: {response.usage.prompt_tokens}+{response.usage.completion_tokens}"
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Page {i+1}: failed to parse JSON: {e}")
            continue
        except Exception as e:
            logger.error(f"Page {i+1}: GPT-4 Vision call failed: {e}")
            continue

    return {
        'lab_name': lab_name,
        'exam_date': exam_date,
        'biomarkers': all_biomarkers,
    }


def match_biomarker_safe(name, biomarker_catalog):
    """
    Safe matching without the dangerous partial/substring tier.
    Only exact matches on name, code, or aliases.

    Args:
        name: extracted name from GPT-4
        biomarker_catalog: list of Biomarker objects

    Returns:
        Biomarker instance or None
    """
    name_lower = name.lower().strip()

    # Tier 1: Exact match on name or code
    for bm in biomarker_catalog:
        if bm.name.lower() == name_lower or bm.code.lower() == name_lower:
            return bm

    # Tier 2: Exact match on aliases
    for bm in biomarker_catalog:
        if bm.aliases:
            aliases = [a.strip().lower() for a in bm.aliases.split(',')]
            if name_lower in aliases:
                return bm

    # NO Tier 3 (partial/substring) - this caused DHT->HCT, SHBG->GLOB, etc.
    return None


def process_exam(exam):
    """
    Process an uploaded exam: extract biomarkers, validate, auto-correct,
    and generate AI analysis.

    Args:
        exam: Exam model instance

    Returns:
        True if successful, False otherwise
    """
    from .models import AIAnalysis, Biomarker, ExamResult
    from .validation import (
        FlagCategory, FlagSeverity, ValidationFlag,
        apply_auto_corrections, save_validation_flags, validate_exam,
    )

    exam.status = 'processing'
    exam.save(update_fields=['status'])

    try:
        # Step 1: Extract biomarkers from file (catalog-aware)
        exam.file.seek(0)
        extracted = extract_biomarkers_from_file(exam.file, exam.file_type)
        exam.ai_raw_response = json.dumps(extracted, ensure_ascii=False, indent=2)

        # Update lab name if extracted and not provided
        if extracted.get('lab_name') and not exam.lab_name:
            exam.lab_name = extracted['lab_name']

        # Step 2: Match and save biomarker results
        catalog = list(Biomarker.objects.all())
        catalog_by_code = {bm.code: bm for bm in catalog}
        saved_count = 0
        unmatched_items = []
        low_confidence_items = []

        for item in extracted.get('biomarkers', []):
            code = item.get('code')
            confidence = item.get('confidence', 'none')
            raw_name = item.get('raw_name', item.get('name', ''))

            # Try code-based lookup first (from catalog-aware prompt)
            biomarker = None
            if code and code in catalog_by_code:
                biomarker = catalog_by_code[code]
                if confidence == 'low':
                    low_confidence_items.append((item, biomarker))
            elif code:
                # Code returned but not in catalog - try safe match on raw name
                biomarker = match_biomarker_safe(raw_name, catalog)
                if biomarker:
                    low_confidence_items.append((item, biomarker))
            else:
                # No code returned - fallback to safe matching
                biomarker = match_biomarker_safe(raw_name, catalog)

            if not biomarker:
                unmatched_items.append(item)
                logger.info(f"No catalog match for: {raw_name} (code={code})")
                continue

            try:
                value = Decimal(str(item['value']))
            except (InvalidOperation, ValueError, TypeError):
                logger.warning(f"Invalid value for {raw_name}: {item.get('value')}")
                continue

            ExamResult.objects.update_or_create(
                exam=exam,
                biomarker=biomarker,
                defaults={'value': value}
            )
            saved_count += 1

        logger.info(f"Exam {exam.id}: saved {saved_count}/{len(extracted.get('biomarkers', []))} results")

        # Step 3: Validate
        validation_flags = validate_exam(exam)

        # Add low-confidence flags
        for item, bm in low_confidence_items:
            raw_name = item.get('raw_name', item.get('name', ''))
            validation_flags.append(ValidationFlag(
                exam_result_id=None,
                biomarker_code=bm.code,
                severity=FlagSeverity.WARNING,
                category=FlagCategory.LOW_CONFIDENCE,
                message=(
                    f"IA com baixa confian\u00e7a no match: "
                    f"'{raw_name}' \u2192 {bm.code} ({bm.name})"
                ),
                details={'raw_name': raw_name, 'code': bm.code},
            ))

        # Add unmatched flags
        for item in unmatched_items:
            raw_name = item.get('raw_name', item.get('name', 'N/A'))
            validation_flags.append(ValidationFlag(
                exam_result_id=None,
                biomarker_code='UNKNOWN',
                severity=FlagSeverity.INFO,
                category=FlagCategory.UNMATCHED,
                message=(
                    f"Biomarcador n\u00e3o identificado: '{raw_name}' "
                    f"= {item.get('value', 'N/A')} {item.get('unit', '')}"
                ),
                details={'raw_item': {
                    'raw_name': raw_name,
                    'value': str(item.get('value', '')),
                    'unit': item.get('unit', ''),
                }},
            ))

        # Step 4: Apply auto-corrections (WBC %, BASO estimation)
        apply_auto_corrections(exam, validation_flags)

        # Step 5: Save validation flags to DB
        save_validation_flags(exam, validation_flags)

        # Step 6: Generate AI analysis
        generate_ai_analysis(exam)

        exam.status = 'completed'
        exam.save(update_fields=['status', 'ai_raw_response', 'lab_name'])

        flag_summary = (
            f"{sum(1 for f in validation_flags if f.severity == FlagSeverity.ERROR)} errors, "
            f"{sum(1 for f in validation_flags if f.severity == FlagSeverity.WARNING)} warnings, "
            f"{sum(1 for f in validation_flags if f.severity == FlagSeverity.AUTO_CORRECTED)} auto-corrected, "
            f"{sum(1 for f in validation_flags if f.severity == FlagSeverity.INFO)} info"
        )
        logger.info(f"Exam {exam.id}: processing complete. Validation: {flag_summary}")
        return True

    except Exception as e:
        logger.error(f"Exam {exam.id} processing failed: {e}")
        exam.status = 'error'
        exam.error_message = str(e)
        exam.save(update_fields=['status', 'error_message', 'ai_raw_response'])
        return False


def generate_ai_analysis(exam):
    """
    Generate AI analysis comparing current exam with historical data.

    Args:
        exam: Exam model instance (must have results already saved)
    """
    from .models import AIAnalysis, ExamResult

    client = get_openai_client()

    # Get current results
    current_results = ExamResult.objects.filter(exam=exam).select_related('biomarker')
    if not current_results.exists():
        return

    # Format current results
    current_text = ""
    for r in current_results:
        status = ""
        if r.is_abnormal:
            if r.ref_max and r.value > r.ref_max:
                status = " ⬆️ ALTO"
            elif r.ref_min and r.value < r.ref_min:
                status = " ⬇️ BAIXO"
        ref_range = ""
        if r.ref_min is not None and r.ref_max is not None:
            ref_range = f" (ref: {r.ref_min}-{r.ref_max})"
        current_text += f"- {r.biomarker.name}: {r.value} {r.biomarker.unit}{ref_range}{status}\n"

    # Get historical data (last 3 exams)
    previous_exams = (
        exam.user.exams
        .filter(status='completed', exam_date__lt=exam.exam_date)
        .order_by('-exam_date')[:3]
    )

    historical_section = ""
    if previous_exams.exists():
        historical_section = "**Historico de Exames Anteriores:**\n"
        for prev_exam in previous_exams:
            historical_section += f"\n*Exame de {prev_exam.exam_date}:*\n"
            prev_results = ExamResult.objects.filter(exam=prev_exam).select_related('biomarker')
            for r in prev_results:
                historical_section += f"- {r.biomarker.name}: {r.value} {r.biomarker.unit}\n"
    else:
        historical_section = "**Historico:** Este e o primeiro exame registrado do paciente."

    # Patient data
    gender_display = 'Nao informado'
    age_display = 'Nao informada'
    if hasattr(exam.user, 'profile'):
        if exam.user.profile.gender:
            gender_display = exam.user.profile.get_gender_display()
        if exam.user.profile.age:
            age_display = f'{exam.user.profile.age} anos'

    analysis_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        gender=gender_display,
        age=age_display,
        exam_date=exam.exam_date.isoformat(),
        current_results=current_text,
        historical_section=historical_section,
    )

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": analysis_prompt}],
            max_tokens=4096,
            temperature=0.3,
        )

        content = response.choices[0].message.content.strip()
        # Clean markdown code blocks
        if content.startswith('```'):
            content = content.split('\n', 1)[1] if '\n' in content else content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()

        analysis_data = json.loads(content)

        AIAnalysis.objects.update_or_create(
            exam=exam,
            defaults={
                'summary': analysis_data.get('summary', ''),
                'alerts': analysis_data.get('alerts', []),
                'improvements': analysis_data.get('improvements', []),
                'deteriorations': analysis_data.get('deteriorations', []),
                'recommendations': analysis_data.get('recommendations', ''),
                'comparison_text': analysis_data.get('comparison_text', ''),
                'model_used': settings.OPENAI_MODEL,
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
            }
        )

        logger.info(
            f"Analysis for exam {exam.id}: "
            f"{response.usage.prompt_tokens}+{response.usage.completion_tokens} tokens"
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse analysis JSON: {e}")
        AIAnalysis.objects.update_or_create(
            exam=exam,
            defaults={
                'summary': content if 'content' in dir() else 'Erro ao processar analise',
                'alerts': [],
                'improvements': [],
                'deteriorations': [],
                'recommendations': 'Nao foi possivel gerar recomendacoes automaticamente.',
                'model_used': settings.OPENAI_MODEL,
            }
        )
    except Exception as e:
        logger.error(f"AI analysis failed for exam {exam.id}: {e}")


def generate_trend_analysis(biomarker, results, ref_min, ref_max, user):
    """
    Generate AI analysis of a biomarker's historical trend.

    Uses caching: only calls GPT-4 when data has changed (new results added).

    Args:
        biomarker: Biomarker model instance
        results: QuerySet of ExamResult ordered by exam date
        ref_min: Reference minimum for user's gender
        ref_max: Reference maximum for user's gender
        user: User model instance

    Returns:
        str: Analysis text, or None if not enough data
    """
    from .models import BiomarkerTrendAnalysis

    result_count = results.count()
    if result_count < 2:
        return None

    # Check cache
    try:
        cached = BiomarkerTrendAnalysis.objects.get(user=user, biomarker=biomarker)
        if cached.result_count == result_count:
            return cached.analysis_text
    except BiomarkerTrendAnalysis.DoesNotExist:
        cached = None

    # Build history text
    history_lines = []
    for r in results:
        status = ""
        if r.is_abnormal:
            if r.ref_max and r.value > r.ref_max:
                status = " (ACIMA da referencia)"
            elif r.ref_min and r.value < r.ref_min:
                status = " (ABAIXO da referencia)"
        history_lines.append(
            f"- {r.exam.exam_date.strftime('%d/%m/%Y')}: {r.value} {biomarker.unit}{status}"
        )

    # Reference range text
    if ref_min is not None and ref_max is not None:
        ref_range = f"{ref_min} - {ref_max} {biomarker.unit}"
    elif ref_max is not None:
        ref_range = f"< {ref_max} {biomarker.unit}"
    elif ref_min is not None:
        ref_range = f"> {ref_min} {biomarker.unit}"
    else:
        ref_range = "Nao disponivel"

    # Patient data
    gender_display = 'Nao informado'
    age_display = 'Nao informada'
    if hasattr(user, 'profile'):
        if user.profile.gender:
            gender_display = user.profile.get_gender_display()
        if user.profile.age:
            age_display = f'{user.profile.age} anos'

    prompt = TREND_ANALYSIS_PROMPT.format(
        biomarker_name=biomarker.name,
        biomarker_code=biomarker.code,
        unit=biomarker.unit,
        category=biomarker.category,
        description=biomarker.description or 'Sem descricao disponivel.',
        ref_range=ref_range,
        gender=gender_display,
        age=age_display,
        history='\n'.join(history_lines),
    )

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.3,
        )

        analysis_text = response.choices[0].message.content.strip()

        # Cache the result
        BiomarkerTrendAnalysis.objects.update_or_create(
            user=user,
            biomarker=biomarker,
            defaults={
                'analysis_text': analysis_text,
                'result_count': result_count,
                'model_used': settings.OPENAI_MODEL,
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
            }
        )

        logger.info(
            f"Trend analysis for {biomarker.code} (user {user.username}): "
            f"{response.usage.prompt_tokens}+{response.usage.completion_tokens} tokens"
        )

        return analysis_text

    except Exception as e:
        logger.error(f"Trend analysis failed for {biomarker.code}: {e}")
        # Return cached version if available, even if stale
        if cached:
            return cached.analysis_text
        return None
