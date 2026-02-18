"""
OpenAI GPT-4 Vision integration for blood exam processing.

Step 1: Extract biomarker data from uploaded exam (PDF/image) using GPT-4 Vision.
Step 2: Generate AI analysis comparing current results with historical data.
"""

import base64
import json
import logging
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.conf import settings

logger = logging.getLogger('core')

EXTRACTION_PROMPT = """Você é um especialista em exames de sangue. Analise esta imagem de um exame de sangue e extraia TODOS os biomarcadores encontrados.

Retorne APENAS um JSON válido no seguinte formato (sem markdown, sem texto extra):
{
    "lab_name": "Nome do laboratório (se visível)",
    "exam_date": "YYYY-MM-DD (se visível, senão null)",
    "biomarkers": [
        {
            "name": "Nome do biomarcador exatamente como aparece",
            "value": 12.5,
            "unit": "g/dL",
            "ref_min": 12.0,
            "ref_max": 16.0
        }
    ]
}

Regras importantes:
- Extraia TODOS os biomarcadores visíveis, não apenas os principais
- O campo "value" deve ser um número (float), não string
- ref_min e ref_max devem ser números ou null se não disponíveis
- Se o valor for "<0.1" ou ">1000", use o número (0.1 ou 1000)
- Mantenha os nomes dos biomarcadores em português como aparecem no exame
- Não invente valores. Se não conseguir ler, omita o biomarcador"""

ANALYSIS_PROMPT_TEMPLATE = """Você é um médico especialista em medicina laboratorial. Analise os resultados de exames de sangue abaixo e forneça uma análise completa.

**Dados do Paciente:**
- Sexo: {gender}
- Idade: {age}

**Resultados Atuais ({exam_date}):**
{current_results}

{historical_section}

Retorne APENAS um JSON válido (sem markdown, sem texto extra):
{{
    "summary": "Resumo geral da saúde do paciente em 3-5 frases. Mencione aspectos positivos e pontos de atenção.",
    "alerts": [
        {{
            "biomarker": "Nome do biomarcador",
            "value": "valor atual com unidade",
            "status": "alto" ou "baixo",
            "message": "Explicação breve do significado clínico"
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
    "recommendations": "Recomendações gerais em formato de texto (3-5 pontos). Inclua recomendações de estilo de vida, alimentação e acompanhamento médico.",
    "comparison_text": "Texto comparativo com exames anteriores. Se não houver histórico, deixe vazio."
}}

IMPORTANTE: Esta análise é apenas informativa e não substitui a consulta com um médico."""


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
                    {"type": "text", "text": EXTRACTION_PROMPT},
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


def match_biomarker(name, biomarker_catalog):
    """
    Match an extracted biomarker name to the catalog using fuzzy matching.

    Args:
        name: extracted name from GPT-4
        biomarker_catalog: QuerySet of Biomarker objects

    Returns:
        Biomarker instance or None
    """
    name_lower = name.lower().strip()

    # Exact match on name or code
    for bm in biomarker_catalog:
        if bm.name.lower() == name_lower or bm.code.lower() == name_lower:
            return bm

    # Match on aliases
    for bm in biomarker_catalog:
        if bm.aliases:
            aliases = [a.strip().lower() for a in bm.aliases.split(',')]
            if name_lower in aliases:
                return bm

    # Partial match
    for bm in biomarker_catalog:
        if name_lower in bm.name.lower() or bm.name.lower() in name_lower:
            return bm
        if bm.aliases:
            aliases = [a.strip().lower() for a in bm.aliases.split(',')]
            for alias in aliases:
                if name_lower in alias or alias in name_lower:
                    return bm

    return None


def process_exam(exam):
    """
    Process an uploaded exam: extract biomarkers and generate AI analysis.

    Args:
        exam: Exam model instance

    Returns:
        True if successful, False otherwise
    """
    from .models import AIAnalysis, Biomarker, ExamResult

    exam.status = 'processing'
    exam.save(update_fields=['status'])

    try:
        # Step 1: Extract biomarkers from file
        exam.file.seek(0)
        extracted = extract_biomarkers_from_file(exam.file, exam.file_type)
        exam.ai_raw_response = json.dumps(extracted, ensure_ascii=False, indent=2)

        # Update lab name if extracted and not provided
        if extracted.get('lab_name') and not exam.lab_name:
            exam.lab_name = extracted['lab_name']

        # Step 2: Match and save biomarker results
        catalog = list(Biomarker.objects.all())
        saved_count = 0

        for item in extracted.get('biomarkers', []):
            biomarker = match_biomarker(item['name'], catalog)
            if not biomarker:
                logger.info(f"No catalog match for: {item['name']}")
                continue

            try:
                value = Decimal(str(item['value']))
            except (InvalidOperation, ValueError, TypeError):
                logger.warning(f"Invalid value for {item['name']}: {item['value']}")
                continue

            ref_min = None
            ref_max = None
            try:
                if item.get('ref_min') is not None:
                    ref_min = Decimal(str(item['ref_min']))
                if item.get('ref_max') is not None:
                    ref_max = Decimal(str(item['ref_max']))
            except (InvalidOperation, ValueError, TypeError):
                pass

            ExamResult.objects.update_or_create(
                exam=exam,
                biomarker=biomarker,
                defaults={
                    'value': value,
                    'ref_min': ref_min,
                    'ref_max': ref_max,
                }
            )
            saved_count += 1

        logger.info(f"Exam {exam.id}: saved {saved_count}/{len(extracted.get('biomarkers', []))} results")

        # Step 3: Generate AI analysis
        generate_ai_analysis(exam)

        exam.status = 'completed'
        exam.save(update_fields=['status', 'ai_raw_response', 'lab_name'])
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
        historical_section = "**Histórico de Exames Anteriores:**\n"
        for prev_exam in previous_exams:
            historical_section += f"\n*Exame de {prev_exam.exam_date}:*\n"
            prev_results = ExamResult.objects.filter(exam=prev_exam).select_related('biomarker')
            for r in prev_results:
                historical_section += f"- {r.biomarker.name}: {r.value} {r.biomarker.unit}\n"
    else:
        historical_section = "**Histórico:** Este é o primeiro exame registrado do paciente."

    # Patient data
    gender_display = 'Não informado'
    age_display = 'Não informada'
    if hasattr(exam.user, 'profile'):
        if exam.user.profile.gender:
            gender_display = exam.user.profile.get_gender_display()
        if exam.user.profile.age:
            age_display = f'{exam.user.profile.age} anos'

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        gender=gender_display,
        age=age_display,
        exam_date=exam.exam_date.isoformat(),
        current_results=current_text,
        historical_section=historical_section,
    )

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
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
                'summary': content if 'content' in dir() else 'Erro ao processar análise',
                'alerts': [],
                'improvements': [],
                'deteriorations': [],
                'recommendations': 'Não foi possível gerar recomendações automaticamente.',
                'model_used': settings.OPENAI_MODEL,
            }
        )
    except Exception as e:
        logger.error(f"AI analysis failed for exam {exam.id}: {e}")
