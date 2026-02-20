# Blood Lab - CLAUDE.md

## Visao Geral

Aplicacao web Django para upload e analise de exames de sangue com IA (GPT-4 Vision). Extrai biomarcadores de PDFs/imagens, valida resultados, gera analise comparativa e exibe dashboards com graficos interativos.

**Idioma do conteudo:** Portugues (pt-BR)
**Publico-alvo:** Usuarios finais acompanhando sua saude

---

## Stack Tecnologico

- **Backend:** Django 4.2 + Gunicorn + WhiteNoise 6
- **Database:** PostgreSQL 16 (prod) / SQLite (dev)
- **AI:** OpenAI GPT-4o (Vision para extracao, chat para analise)
- **Frontend:** HTML/CSS/JS puro (sem frameworks), Chart.js 4.4.1
- **Deploy:** Docker multi-stage + docker-compose
- **Servidor:** VPS 45.63.90.69, path /var/www/blood-exams/

---

## Estrutura de Arquivos

```
_BloodExams/
  manage.py
  requirements.txt
  Dockerfile                  # Multi-stage: builder + runtime
  docker-compose.yml          # PostgreSQL + web (porta 3006:8000)
  .gitignore

  blood_exams/                # Projeto Django
    settings.py               # Config com env vars, WhiteNoise, FORCE_SCRIPT_NAME
    urls.py                   # URLs raiz: admin, auth, include core
    wsgi.py

  core/                       # App principal
    models.py                 # UserProfile, Biomarker, Exam, ExamResult, AIAnalysis, ExamValidation, BiomarkerTrendAnalysis
    views.py                  # Dashboard, upload, exam detail, biomarker chart, trend API, admin
    urls.py                   # Todas as rotas da app
    forms.py                  # ExamUploadForm, ProfileForm, RegistrationForm
    admin.py                  # Django admin config
    ai_service.py             # GPT-4 Vision: extracao, analise, trend analysis
    validation.py             # Validacao de resultados (fisiologica, cruzada, WBC %, historica)
    templatetags/
      blood_extras.py         # Template tag widthratio etc.
    management/commands/
      seed_biomarkers.py      # Popula catalogo de biomarcadores
    templates/core/
      base.html               # Template base (Chart.js CDN, app.js, style.css)
      dashboard.html           # Dashboard principal com stats, graficos, AI panel, comparativo
      biomarker_chart.html     # Grafico individual + trend analysis async
      exam_detail.html         # Detalhes de um exame
      exam_history.html        # Historico de exames
      upload.html              # Upload de exame
      profile.html             # Perfil do usuario
      login.html / register.html
      admin_users.html         # Painel admin

  static/core/
    app.js                    # Logica frontend: Chart.js, dashboard charts, comparativo de biomarcadores
    style.css                 # Todos os estilos (dark/light theme, responsivo)
```

---

## Arquitetura de Deploy

### Docker Compose
- **blood-db**: PostgreSQL 16 Alpine
- **blood-exams**: Django + Gunicorn (2 workers, timeout 300s para processamento IA)
- Porta mapeada: 3006 (host) -> 8000 (container)

### Proxy Reverso
- **nginx-proxy** (container separado na rede `docker-infra_app-network`)
- Rota: `/blood/` -> rewrite `^/blood/(.*)$ /$1 break` -> proxy_pass blood_backend
- Django usa `FORCE_SCRIPT_NAME=/blood` para gerar URLs corretas

### WhiteNoise (CRITICO)
- `CompressedManifestStaticFilesStorage` indexa arquivos estaticos na memoria no startup
- **SEMPRE reiniciar container apos collectstatic**: `docker restart blood-exams`
- Se nao reiniciar, WhiteNoise retorna 404 para arquivos com hash novo
- Apos restart, reconectar a rede: `docker network connect docker-infra_app-network blood-exams`

### Fluxo de Deploy
```bash
# 1. Upload dos arquivos alterados para o servidor
# 2. Build e deploy
cd /var/www/blood-exams
docker compose build --no-cache
docker compose up -d
docker network connect docker-infra_app-network blood-exams
# 3. Verificar se CSS carrega corretamente
docker restart blood-exams  # Forca WhiteNoise a re-indexar
docker network connect docker-infra_app-network blood-exams
```

---

## Modelo de Dados

### Biomarker (Catalogo)
- ~54 biomarcadores cadastrados via `seed_biomarkers` management command
- Faixas de referencia separadas por sexo (ref_min_male, ref_max_male, ref_min_female, ref_max_female)
- **IMPORTANTE**: Alguns biomarcadores tem apenas um limite:
  - Apenas ref_max: CT (Colesterol Total), LDL, TG (Triglicerides), VLDL
  - Apenas ref_min: HDL
  - Ambos: Hemoglobina, Glicose, etc.
- Campo `aliases` para matching com nomes alternativos

### ExamResult
- `save()` sobrescreve ref_min/ref_max com valores do catalogo Biomarker (gender-aware)
- Auto-detecta `is_abnormal` comparando valor com referencia

### AIAnalysis
- Analise por exame: summary, alerts (JSON), improvements (JSON), deteriorations (JSON), recommendations
- Alertas passam por pos-processamento: filtra alertas falsos (biomarcadores dentro da faixa)

### BiomarkerTrendAnalysis
- Cache de analise de tendencia por (user, biomarker)
- Invalidado quando `result_count` muda (novo exame adicionado)

---

## Pipeline de Processamento de Exame

1. **Upload** (PDF ou imagem)
2. **Extracao** (GPT-4 Vision): converte PDF em imagens, envia com prompt catalog-aware
3. **Matching**: code-based (do prompt) -> exact name/alias match -> sem match parcial (evita falsos)
4. **Validacao**: faixas fisiologicas, validacao cruzada, WBC diferencial, duplicatas, historica
5. **Auto-correcao**: WBC % -> absoluto (quando tem leucocitos totais), estimativa BASO
6. **Analise IA**: GPT-4 compara com exames anteriores, gera resumo + alertas + recomendacoes

---

## Frontend (app.js)

### Graficos do Dashboard
- **renderDashboardCharts()**: Grid de mini-graficos de evolucao, agrupados por categoria
- **renderRadarChart()**: Saude por categoria (% normais)
- **renderDonutChart()**: Normal vs Alterado
- **renderGaugeCharts()**: Biomarcadores criticos com gauge
- **renderDeviationBars()**: Barras de desvio da referencia

### Comparativo de Biomarcadores
- Modo selecao: checkboxes nos cards de grafico
- **2 biomarcadores**: Eixos Y duais (esquerdo/direito) com unidades originais
- **3+ biomarcadores**: Normalizado para % da faixa de referencia, faixa verde 0-100%
- `normalizeToRefPercent()`: Suporta biomarcadores com apenas ref_min, apenas ref_max, ou ambos
- Alinhamento de datas: uniao de todas as datas, `null` para gaps, `spanGaps: false`

### Trend Analysis (Async)
- Pagina de biomarcador individual carrega o grafico imediatamente
- Analise de tendencia carregada via AJAX (`biomarker_trend_api`)
- Loading spinner com mensagem "A IA esta analisando..."
- Cache no backend (BiomarkerTrendAnalysis model)

### Temas
- Dark theme (padrao) e Light theme
- CSS variables para cores
- Toggle no header

---

## Convencoes de Codigo

### Python
- Django 4.2 patterns: CBV quando simples, FBV quando complexo
- Logging via `logger = logging.getLogger('core')`
- Mensagens de usuario via `django.contrib.messages`

### JavaScript
- ES5: `var` em vez de `let`/`const`, `function(){}` sem arrow functions
- Chart.js 4.4.1 carregado via CDN no base.html
- Variaveis globais injetadas via template Django: `var chartData = {{ chart_data_json|safe }};`
- XMLHttpRequest para AJAX (sem fetch/axios)

### CSS
- Arquivo unico `style.css`
- Dark/light theme via CSS variables
- Responsivo com media queries (768px, 480px breakpoints)
- Sem pre-processadores

### HTML
- Django template language
- Entidades HTML para acentos (`&atilde;`, `&ccedil;`, etc.)
- Template inheritance: todos extendem `base.html`

---

## URLs da Aplicacao

| Path | View | Descricao |
|------|------|-----------|
| `/` | dashboard_view | Dashboard principal |
| `/register/` | register_view | Registro de usuario |
| `/login/` | LoginView | Login (Django auth) |
| `/logout/` | LogoutView | Logout |
| `/profile/` | profile_view | Perfil do usuario |
| `/upload/` | upload_view | Upload de exame |
| `/exam/<id>/` | exam_detail_view | Detalhes do exame |
| `/exam/<id>/delete/` | exam_delete_view | Excluir exame |
| `/exam/<id>/reprocess/` | exam_reprocess_view | Reprocessar exame |
| `/history/` | exam_history_view | Historico de exames |
| `/biomarker/<code>/` | biomarker_chart_view | Grafico de biomarcador |
| `/biomarker/<code>/trend/` | biomarker_trend_api | API AJAX: trend analysis |
| `/api/biomarker/<code>/` | api_biomarker_data | API JSON: dados do biomarcador |
| `/admin-panel/` | admin_users_view | Painel admin (superuser) |
| `/health/` | health_view | Health check |

---

## Variaveis de Ambiente

| Variavel | Descricao | Default |
|----------|-----------|---------|
| `DEBUG` | Modo debug | `False` |
| `SECRET_KEY` | Chave secreta Django | Obrigatorio em prod |
| `ALLOWED_HOSTS` | Hosts permitidos | `localhost,127.0.0.1,45.63.90.69` |
| `FORCE_SCRIPT_NAME` | Prefixo URL (proxy) | `/blood` em prod |
| `OPENAI_API_KEY` | Chave API OpenAI | Obrigatorio |
| `OPENAI_MODEL` | Modelo GPT | `gpt-4o` |
| `DB_ENGINE` | Engine do banco | SQLite se vazio |
| `DB_NAME/USER/PASSWORD/HOST/PORT` | Config PostgreSQL | - |

---

## Gotchas e Licoes Aprendidas

### WhiteNoise + Docker
**Problema**: Apos `docker compose up -d`, CSS retorna 404 mesmo existindo no disco.
**Causa**: WhiteNoise indexa arquivos estaticos em memoria no startup. O Dockerfile faz `collectstatic` no build, mas se os arquivos mudaram, os hashes no manifesto sao diferentes dos que WhiteNoise conhece.
**Solucao**: SEMPRE `docker restart blood-exams` apos deploy para forcar re-indexacao.

### Normalizacao de Biomarcadores com Limite Unico
**Problema**: Grafico comparativo ficava vazio para lipidios.
**Causa**: Funcao `normalizeToRefPercent()` exigia ambos ref_min E ref_max.
**Solucao**: Tratar 3 casos: (1) ambos limites -> `(val - min) / (max - min) * 100`, (2) apenas ref_max -> `val / max * 100`, (3) apenas ref_min -> `val / min * 100`.

### Alertas Falsos da IA
**Problema**: GPT-4 gerava alertas para biomarcadores dentro da faixa de referencia.
**Causa**: O modelo ignora as faixas do catalogo e alerta baseado em "opiniao medica".
**Solucao**: Pos-processamento em `generate_ai_analysis()` filtra alertas cujo biomarcador nao esta marcado como `is_abnormal`.

### Trend Analysis Bloqueando Pagina
**Problema**: Pagina de biomarcador demorava 1-3s para abrir na primeira vez.
**Causa**: `generate_trend_analysis()` era chamada sincronamente na view.
**Solucao**: Carregamento async via AJAX endpoint `biomarker_trend_api` com loading spinner.

---

## Git

- Branch principal: `master`
- Mensagens de commit em ingles com prefixo convencional: `feat:`, `fix:`, `docs:`, `refactor:`
- Nao commitar `.claude/`, `staticfiles/`, `media/`, `db.sqlite3`
