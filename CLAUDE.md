# Blood Lab - CLAUDE.md

## Visao Geral

Aplicacao web Django para upload e analise de exames de sangue com IA (GPT-4 Vision). Extrai biomarcadores de PDFs/imagens, valida resultados, gera analise comparativa e exibe dashboards com graficos interativos.

**Idioma do conteudo:** Portugues (pt-BR)
**Publico-alvo:** Usuarios finais acompanhando sua saude
**URL:** https://mlt.com.br/blood/
**Admin Django:** https://mlt.com.br/blood/admin/ (admin / admin123)

---

## Stack Tecnologico

- **Backend:** Django 4.2+ / Django 5.2 + Gunicorn + WhiteNoise 6
- **Auth:** django-allauth (Google OAuth + username/password)
- **Database:** PostgreSQL 16 (prod) / SQLite (dev/testes)
- **AI:** OpenAI GPT-4o (Vision para extracao, chat para analise)
- **Frontend:** HTML/CSS/JS puro (sem frameworks), Chart.js 4.4.1
- **Deploy:** Docker multi-stage + docker-compose
- **Testes:** pytest + pytest-django (179 testes)
- **Servidor:** VPS 45.63.90.69, path /var/www/blood-exams/
- **Dominio:** mlt.com.br (Cloudflare DNS + CDN proxy) → /blood/
- **DNS:** Cloudflare (nameservers: rafe.ns.cloudflare.com, trace.ns.cloudflare.com)
- **SSL:** Cloudflare Flexible (HTTPS no browser, HTTP no origin)

---

## Estrutura de Arquivos

```
_BloodExams/
  manage.py
  requirements.txt
  pytest.ini                    # Config pytest (DJANGO_SETTINGS_MODULE)
  Dockerfile                    # Multi-stage: builder + runtime
  docker-compose.yml            # PostgreSQL + web (porta 3006:8000)
  entrypoint.sh                 # Auto-migrate + Site config + gunicorn start
  .gitignore

  blood_exams/                  # Projeto Django
    settings.py                 # Config com env vars, WhiteNoise, FORCE_SCRIPT_NAME, allauth, CSRF_TRUSTED_ORIGINS
    urls.py                     # URLs raiz: admin, auth, allauth, include core
    wsgi.py

  core/                         # App principal
    models.py                   # UserProfile, Biomarker, Exam, ExamResult, AIAnalysis, ExamValidation, BiomarkerTrendAnalysis
    views.py                    # 17 views: dashboard, upload, exam detail, biomarker chart, trend API, admin CRUD, complete_profile, health
    urls.py                     # 18 rotas da app
    forms.py                    # ExamUploadForm, ProfileForm, RegistrationForm, CompleteProfileForm, AdminUserForm
    middleware.py               # ProfileCompletionMiddleware (usa request.path_info para compatibilidade com FORCE_SCRIPT_NAME)
    admin.py                    # Django admin config (7 modelos registrados)
    ai_service.py               # GPT-4 Vision: extracao, matching, analise, trend analysis
    validation.py               # Validacao de resultados (6 regras: fisiologica, cruzada, WBC %, duplicatas, historica, unidade)
    tests.py                    # Suite completa de testes (179 testes)
    templatetags/
      blood_extras.py           # Filtros: get_item, abs_value, status_color, trend_icon
    management/commands/
      seed_biomarkers.py        # Popula catalogo de biomarcadores
    templates/core/
      base.html                 # Template base (Chart.js CDN, app.js, style.css, theme toggle)
      dashboard.html            # Dashboard principal com stats, graficos, AI panel, comparativo
      biomarker_chart.html      # Grafico individual + trend analysis async
      exam_detail.html          # Detalhes de um exame
      exam_history.html         # Historico de exames
      upload.html               # Upload de exame
      profile.html              # Perfil do usuario
      login.html                # Login com botao Google OAuth + deteccao tema OS
      register.html             # Registro de usuario + deteccao tema OS
      complete_profile.html     # Formulario obrigatorio DOB + sexo + deteccao tema OS
      admin_users.html          # Painel admin (lista usuarios)
      admin_user_form.html      # Formulario criar/editar usuario (admin)

  static/core/
    app.js                      # Logica frontend: Chart.js, dashboard charts, comparativo de biomarcadores
    style.css                   # Todos os estilos (dark/light theme, responsivo)
```

---

## Arquitetura de Deploy

### Docker Compose
- **blood-db**: PostgreSQL 16 Alpine
- **blood-exams**: Django + Gunicorn (2 workers, timeout 300s para processamento IA)
- Porta mapeada: 3006 (host) -> 8000 (container)

### Proxy Reverso (nginx-proxy)
- Container separado na rede `docker-infra_app-network`
- Rota: `/blood/` -> rewrite `^/blood/(.*)$ /$1 break` -> proxy_pass blood_backend
- Django usa `FORCE_SCRIPT_NAME=/blood` para gerar URLs corretas
- Config: `/var/www/docker-infra/nginx/conf.d/default.conf` (server block principal)
- **X-Forwarded-Proto: https** (hardcoded no nginx, nao `$scheme` — necessario para Cloudflare Flexible SSL)

### Cloudflare
- SSL mode: **Flexible** (HTTPS entre browser e Cloudflare, HTTP entre Cloudflare e origin)
- nginx recebe HTTP mas Django ve HTTPS via `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`
- `CSRF_TRUSTED_ORIGINS` inclui `https://mlt.com.br` para cross-scheme CSRF

### Entrypoint (entrypoint.sh)
- Roda `migrate --noinput` automaticamente no startup
- Configura `django.contrib.sites` Site (id=1, domain=mlt.com.br, name=Blood Lab)
- Inicia Gunicorn (2 workers, timeout 300s, max-requests 500)

### WhiteNoise (CRITICO)
- `CompressedManifestStaticFilesStorage` indexa arquivos estaticos na memoria no startup
- **SEMPRE reiniciar container apos collectstatic**: `docker restart blood-exams`
- Se nao reiniciar, WhiteNoise retorna 404 para arquivos com hash novo
- Apos restart, reconectar a rede: `docker network connect docker-infra_app-network blood-exams`

### Fluxo de Deploy
```bash
# 1. Upload dos arquivos alterados para o servidor (via paramiko ou pscp)
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

## Modelo de Dados (7 modelos)

### UserProfile (OneToOne com User)
- Campos: `date_of_birth`, `gender` (M/F), `is_active_subscriber`
- Auto-criado via signal `post_save` do User
- Property `age` calculado a partir de `date_of_birth`

### Biomarker (Catalogo de Referencia)
- ~54 biomarcadores cadastrados via `seed_biomarkers` management command
- Faixas de referencia separadas por sexo (ref_min_male, ref_max_male, ref_min_female, ref_max_female)
- **IMPORTANTE**: Alguns biomarcadores tem apenas um limite:
  - Apenas ref_max: CT (Colesterol Total), LDL, TG (Triglicerides), VLDL
  - Apenas ref_min: HDL
  - Ambos: Hemoglobina, Glicose, etc.
- Campo `aliases` para matching com nomes alternativos
- Metodo `get_ref_range(gender)` retorna (ref_min, ref_max) por genero

### Exam
- FK para User (CASCADE)
- Status: pending → processing → completed | error
- Properties: `result_count`, `abnormal_count`, `validation_status`, `unresolved_flag_count`

### ExamResult
- `save()` SEMPRE sobrescreve ref_min/ref_max com valores do catalogo Biomarker (gender-aware)
- Auto-detecta `is_abnormal` comparando valor com referencia
- `unique_together = ['exam', 'biomarker']`

### AIAnalysis (OneToOne com Exam)
- Analise por exame: summary, alerts (JSON), improvements (JSON), deteriorations (JSON), recommendations
- Alertas passam por pos-processamento: filtra alertas falsos (biomarcadores dentro da faixa)

### ExamValidation
- Flags de validacao geradas durante processamento do exame
- Severidades: info, warning, error, auto_corrected
- Categorias: physiological, cross_biomarker, wbc_percentage, duplicate_exam, historical, low_confidence, unmatched, unit_mismatch

### BiomarkerTrendAnalysis
- Cache de analise de tendencia por (user, biomarker)
- `unique_together = ['user', 'biomarker']`
- Invalidado quando `result_count` muda (novo exame adicionado)

---

## Autenticacao e Perfil

### Metodos de Login
- **Username/password**: Django auth padrao (login.html)
- **Google OAuth**: django-allauth com provider Google (botao na pagina de login)
- Allauth URLs: `/accounts/` (inclui callback Google em `/accounts/google/login/callback/`)

### ProfileCompletionMiddleware
- Middleware customizado em `core/middleware.py`
- Redireciona usuarios autenticados sem `date_of_birth` ou `gender` para `/complete-profile/`
- **Usa `request.path_info`** (nao `request.path`) para ignorar o prefixo FORCE_SCRIPT_NAME
- URLs isentas: `/complete-profile/`, `/logout/`, `/health/`, `/admin/`, `/accounts/`, `/static/`, `/media/`
- Motivo: faixas de referencia dos biomarcadores dependem de sexo e idade

### Google OAuth Setup
- Credenciais via env vars: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- Google Cloud Console: OAuth 2.0 Client ID (Web application)
- Redirect URI no Google Console: `https://mlt.com.br/blood/accounts/google/login/callback/`
- `SOCIALACCOUNT_AUTO_SIGNUP = True` (cria conta automaticamente)
- Site framework: domain=mlt.com.br (configurado automaticamente pelo entrypoint.sh)

---

## Validacao de Resultados (validation.py)

Motor de validacao pos-extracao com 6 regras:

| Regra | Categoria | Descricao |
|-------|-----------|-----------|
| A | physiological | Valores fora de limites fisiologicos absolutos (~55 biomarcadores) |
| B | cross_biomarker | CT ≈ HDL+LDL+VLDL (15%), WBC ≈ soma diferencial (10%) |
| C | wbc_percentage | Detecta diferencial em % e auto-converte para absoluto |
| D | duplicate_exam | Flags se >80% valores identicos a exame anterior |
| E | historical | Flags variacao >200% vs exame anterior (exceto codigos volateis) |
| F | unit_mismatch | Detecta unidades erradas via fatores de conversao (14 biomarcadores) |

Auto-correcoes: WBC % → absoluto, estimativa BASO se ausente.

---

## Pipeline de Processamento de Exame

1. **Upload** (PDF ou imagem, max 20MB)
2. **Extracao** (GPT-4 Vision): converte PDF em imagens, envia com prompt catalog-aware
3. **Matching**: code-based (do prompt) → exact name/alias match → sem match parcial (evita falsos)
4. **Validacao**: 6 regras (fisiologica, cruzada, WBC, duplicatas, historica, unidade)
5. **Auto-correcao**: WBC % → absoluto (quando tem leucocitos totais), estimativa BASO
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
- Deteccao automatica do tema do SO via `window.matchMedia('(prefers-color-scheme: light)')`
- Preferencia salva via `localStorage('blood-lab-theme')` tem prioridade
- Toggle no header (sol/lua)
- Paginas standalone (login, register, complete_profile) tem script inline no `<head>` para prevenir flash
- CSS variables para cores em `:root` (dark) e `[data-theme="light"]`

---

## Testes Automatizados

### Configuracao
- **Framework:** pytest + pytest-django
- **Arquivo:** `core/tests.py` (179 testes)
- **Config:** `pytest.ini` (DJANGO_SETTINGS_MODULE = blood_exams.settings)
- **Banco de testes:** SQLite in-memory (automatico, sem necessidade de PostgreSQL)

### Como Executar
```bash
# Todos os testes
python -m pytest core/tests.py -v

# Testes por categoria
python -m pytest core/tests.py::TestUserProfileModel -v
python -m pytest core/tests.py::TestExamResultModel -v
python -m pytest core/tests.py::TestDashboardView -v
python -m pytest core/tests.py::TestSecurityAccessControl -v
python -m pytest core/tests.py::TestValidationEngine -v

# Com cobertura
python -m pytest core/tests.py --cov=core -v
```

### Categorias de Testes (179 total)

| Categoria | Classe de Teste | Qtd | O que testa |
|-----------|----------------|-----|-------------|
| **Modelos** | TestUserProfileModel | 7 | Signal auto-create, age, gender, cascade delete |
| | TestBiomarkerModel | 10 | CRUD, ref ranges por genero, unique, ordering, only ref_min/max |
| | TestExamModel | 10 | CRUD, properties, validation_status, ordering, cascade |
| | TestExamResultModel | 11 | Auto-ref overwrite, is_abnormal logic, only ref_min/max, unique |
| | TestAIAnalysisModel | 5 | CRUD, OneToOne, JSON defaults, cascade |
| | TestExamValidationModel | 5 | CRUD, ordering, unit_mismatch category, cascade |
| | TestBiomarkerTrendAnalysisModel | 3 | CRUD, unique_together |
| **Forms** | TestRegistrationForm | 5 | Validacao, save com profile, email obrigatorio, data dd/mm/yyyy |
| | TestCompleteProfileForm | 4 | Campos obrigatorios, data invalida |
| | TestProfileForm | 4 | Update perfil, troca de senha, senha errada, mismatch |
| | TestExamUploadForm | 4 | PDF valido, imagem valida, extensao invalida, tamanho |
| | TestAdminUserForm | 3 | Criar usuario, editar sem senha, username duplicado |
| **Views** | TestHealthView | 3 | 200 OK, JSON, sem auth |
| | TestRegisterView | 3 | GET, POST valido, redirect se autenticado |
| | TestCompleteProfileView | 4 | GET form, POST salva, redirect se completo, requer login |
| | TestDashboardView | 4 | Requer login, vazio, com dados, context keys |
| | TestExamDetailView | 3 | Requer login, proprio exame, exame alheio 404 |
| | TestExamHistoryView | 2 | Requer login, lista exames |
| | TestExamDeleteView | 3 | POST deleta, GET nao deleta, exame alheio 404 |
| | TestBiomarkerChartView | 3 | Requer login, biomarker valido, invalido 404 |
| | TestBiomarkerTrendApi | 2 | Dados insuficientes, com dados (mock) |
| | TestApiBiomarkerData | 2 | JSON response, requer login |
| | TestProfileView | 2 | GET, POST update |
| | TestUploadView | 3 | GET, requer login, upload PDF (mock process_exam) |
| | TestAdminViews | 4 | Requer superuser, lista, criar usuario, delete bloqueado/permitido |
| **Middleware** | TestProfileCompletionMiddleware | 8 | Redirect incompleto, nao redirect completo, URLs isentas, path_info |
| **Template Tags** | TestTemplateTags | 11 | get_item, abs_value, status_color, trend_icon |
| **Validacao** | TestValidationEngine | 5 | Faixa fisiologica, valores normais, lipid cross, historica, dataclass |
| **Seguranca** | TestSecurityCSRF | 2 | CSRF no login e registro |
| | TestSecurityAccessControl | 9 | Auth redirect, data isolation, admin access control |
| | TestSecurityFileUpload | 3 | Rejeita .exe, .html, .svg |
| **Operacional** | TestURLRouting | 18 | Resolve todas as 18 URLs |
| | TestDjangoSettings | 8 | SECRET_KEY, CSRF origins, SITE_ID, allauth, middleware order, session, upload limit |
| | TestDatabaseIntegrity | 5 | unique_together, OneToOne, cascade deletes |

---

## Convencoes de Codigo

### Python
- Django 4.2+ patterns: FBV para views
- Logging via `logger = logging.getLogger('core')`
- Mensagens de usuario via `django.contrib.messages`
- Testes com pytest (nao unittest.TestCase)

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
- Template inheritance: paginas internas extendem `base.html`, paginas auth sao standalone

---

## URLs da Aplicacao

| Path | View | Descricao |
|------|------|-----------|
| `/` | dashboard_view | Dashboard principal |
| `/register/` | register_view | Registro de usuario |
| `/login/` | LoginView | Login (Django auth + Google OAuth) |
| `/logout/` | LogoutView | Logout (POST only no Django 5+) |
| `/complete-profile/` | complete_profile_view | Completar perfil (DOB + sexo, obrigatorio) |
| `/accounts/` | allauth.urls | URLs do django-allauth (Google OAuth callback) |
| `/profile/` | profile_view | Perfil do usuario |
| `/upload/` | upload_view | Upload de exame |
| `/exam/<id>/` | exam_detail_view | Detalhes do exame |
| `/exam/<id>/delete/` | exam_delete_view | Excluir exame (POST) |
| `/exam/<id>/reprocess/` | exam_reprocess_view | Reprocessar exame (POST) |
| `/history/` | exam_history_view | Historico de exames |
| `/biomarker/<code>/` | biomarker_chart_view | Grafico de biomarcador |
| `/biomarker/<code>/trend/` | biomarker_trend_api | API AJAX: trend analysis |
| `/api/biomarker/<code>/` | api_biomarker_data | API JSON: dados do biomarcador |
| `/admin-panel/` | admin_users_view | Painel admin (superuser) |
| `/admin-panel/user/new/` | admin_user_create_view | Criar usuario (admin) |
| `/admin-panel/user/<id>/edit/` | admin_user_edit_view | Editar usuario (admin) |
| `/admin-panel/user/<id>/delete/` | admin_user_delete_view | Excluir usuario (admin, POST) |
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
| `GOOGLE_CLIENT_ID` | Client ID do Google OAuth | vazio |
| `GOOGLE_CLIENT_SECRET` | Client Secret do Google OAuth | vazio |
| `SECURE_SSL_REDIRECT` | Habilitar cookies Secure + HTTPS redirect | `False` |

---

## Gotchas e Licoes Aprendidas

### WhiteNoise + Docker
**Problema**: Apos `docker compose up -d`, CSS retorna 404 mesmo existindo no disco.
**Causa**: WhiteNoise indexa arquivos estaticos em memoria no startup. O Dockerfile faz `collectstatic` no build, mas se os arquivos mudaram, os hashes no manifesto sao diferentes dos que WhiteNoise conhece.
**Solucao**: SEMPRE `docker restart blood-exams` apos deploy para forcar re-indexacao.

### FORCE_SCRIPT_NAME e Middleware
**Problema**: `ProfileCompletionMiddleware` causava redirect loop infinito em `/blood/complete-profile/`.
**Causa**: `request.path` inclui o prefixo `FORCE_SCRIPT_NAME` (`/blood/complete-profile/`), mas a lista de URLs isentas usa paths sem prefixo (`/complete-profile/`). Nunca bate.
**Solucao**: Usar `request.path_info` em vez de `request.path`. O `path_info` retorna o path sem o SCRIPT_NAME.

### Cloudflare Flexible SSL + X-Forwarded-Proto
**Problema**: Google OAuth gerava redirect_uri com `http://` em vez de `https://`, causando `redirect_uri_mismatch`.
**Causa**: nginx passava `X-Forwarded-Proto $scheme`, mas `$scheme` e `http` porque Cloudflare Flexible SSL envia HTTP para o origin. Django via `SECURE_PROXY_SSL_HEADER` esperava `https`.
**Solucao**: Hardcode `proxy_set_header X-Forwarded-Proto https;` no location block do nginx (nao `$scheme`).

### Cloudflare Flexible SSL + CSRF
**Problema**: Login retornava 403 Forbidden (CSRF verification failed).
**Causa**: Browser envia Origin `https://mlt.com.br` mas Django recebe request HTTP. Django 4.0+ requer `CSRF_TRUSTED_ORIGINS` para cross-scheme requests.
**Solucao**: Adicionar `CSRF_TRUSTED_ORIGINS = ['https://mlt.com.br', 'https://www.mlt.com.br', 'http://45.63.90.69']`

### CSRF Cookie Secure + HTTP
**Problema**: Login retornava 403 Forbidden (CSRF cookie not set).
**Causa**: `SESSION_COOKIE_SECURE = True` e `CSRF_COOKIE_SECURE = True` estavam hardcoded em `if not DEBUG`. Navegadores nao enviam cookies Secure em conexoes HTTP.
**Solucao**: Flags condicionais via env var `SECURE_SSL_REDIRECT`. Quando False (padrao), cookies NAO sao Secure, permitindo HTTP.

### Normalizacao de Biomarcadores com Limite Unico
**Problema**: Grafico comparativo ficava vazio para lipidios.
**Causa**: Funcao `normalizeToRefPercent()` exigia ambos ref_min E ref_max.
**Solucao**: Tratar 3 casos: (1) ambos limites, (2) apenas ref_max, (3) apenas ref_min.

### Alertas Falsos da IA
**Problema**: GPT-4 gerava alertas para biomarcadores dentro da faixa de referencia.
**Causa**: O modelo ignora as faixas do catalogo e alerta baseado em "opiniao medica".
**Solucao**: Pos-processamento em `generate_ai_analysis()` filtra alertas cujo biomarcador nao esta marcado como `is_abnormal`.

### Trend Analysis Bloqueando Pagina
**Problema**: Pagina de biomarcador demorava 1-3s para abrir na primeira vez.
**Causa**: `generate_trend_analysis()` era chamada sincronamente na view.
**Solucao**: Carregamento async via AJAX endpoint `biomarker_trend_api` com loading spinner.

### ExamValidation UNIT_MISMATCH
**Problema**: `validation.py` definia `FlagCategory.UNIT_MISMATCH` mas `ExamValidation.CATEGORY_CHOICES` nao incluia `unit_mismatch`, impedindo salvar flags dessa categoria no banco.
**Solucao**: Adicionado `('unit_mismatch', 'Unidade Incompativel')` aos CATEGORY_CHOICES.

---

## Git

- Branch principal: `master`
- Mensagens de commit em ingles com prefixo convencional: `feat:`, `fix:`, `docs:`, `refactor:`
- Nao commitar `.claude/`, `staticfiles/`, `media/`, `db.sqlite3`
