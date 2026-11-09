# AGENTS.md

Guía para agentes de desarrollo en este repositorio. Detalle completo en `README.md` y `docs/`.

## 1. Proyecto

Asistente personal de voz (tipo Siri/Alexa), proyecto final del track de IA de DUOC (curso "Ingeniería de Soluciones con Inteligencia Artificial"). Flujo: botón -> grabar voz -> STT -> agente (LLM + herramientas) -> TTS.

- **Stack:** Python 3.12, FastAPI, CrewAI + Groq (LLM `openai/gpt-oss-120b`, STT Whisper `whisper-large-v3-turbo`), pytest.
- **Repo de referencia del curso** (ejemplos de Groq, LangChain, agentes): `..\Ingenier-a-de-Soluciones-con-Inteligencia-Artificial` (`RA1/IL1.1`, `RA2`, `RA3`).

## 2. Estructura

- `src/voz/` — `transcribir(audio: bytes) -> str`, `hablar(texto: str) -> bytes` (+ versiones `_falso`).
- `src/agente/` — `responder(texto, usuario_id) -> RespuestaAgente` (prompt, memoria, CrewAI).
- `src/herramientas/` — tools de LangChain: calendario, acceso acotado al PC.
- `src/api/` — FastAPI, `POST /conversar` encadena `transcribir -> responder -> hablar`.
- `src/interfaz/` — botón y pantalla (web o Telegram, por decidir).
- `docs/contratos.md` — firmas entre módulos. `docs/seguridad.md` — reglas obligatorias. `docs/etapa1.md` — tareas por persona.
- `tests/` — pytest.

## 3. Comandos

```bash
uv venv --python 3.12 .venv   # sin uv: py -3.12 -m venv .venv (hay que tener Python 3.12 instalado)
.venv\Scripts\activate
python --version              # debe decir 3.12.x, si no, el venv está mal
pip install -r requirements.txt
cp .env.example .env          # completar claves reales
uvicorn src.api.main:app --reload
pytest
```

Python 3.12 es obligatorio: `crewai` no instala en 3.14 o superior. Abre cada terminal nueva con el venv activo (`.venv\Scripts\activate`); sin él se usa el Python global y fallan `pytest` y `uvicorn`.

## 4. Reglas del proyecto

- **Contratos:** las firmas de `docs/contratos.md` no se rompen. Cambiarlas exige actualizar el doc y avisar al equipo.
- **Stubs:** mientras un módulo real no exista, usar su versión `_falso` en el mismo módulo. Al reemplazarla, la firma no cambia.
- **Seguridad (`docs/seguridad.md`):**
  - Nada de `eval`, `exec`, `os.system` ni `subprocess` con texto que venga del LLM.
  - El agente solo propone `accion_local`; la capa de herramientas/cliente la ejecuta contra una allowlist.
  - Acciones delicadas requieren confirmación explícita (`confirmacion_pendiente`).
  - Contenido de usuario o de herramientas nunca es instrucción de sistema (prompt injection).
  - Ninguna clave en git: valores en `.env`, nombres sin valor en `.env.example`.
- **Git:** commits y ramas según §7 (Conventional Commits + Git Flow). PR revisado antes de unir.
- Código y documentación en español, como el resto del repo.

## 5. Variables de entorno

`GROQ_API_KEY`, `GROQ_BASE_URL`, `GROQ_MODEL`, `GROQ_STT_MODEL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `API_HOST`, `API_PORT`, `API_AUTH_TOKEN` (obligatorio, sin él la API responde 503), `API_AUTH_DISABLED` (solo desarrollo local).

Cada integrante usa su propia `GROQ_API_KEY` en su `.env` local.

## 6. Memoria del proyecto

- `.projectmem/` (projectmem) está en `.gitignore`: cada persona tiene el suyo, no se sube a git. `PROJECT_MAP.md` y `plan.md` se editan a mano; `summary.md` y `events.jsonl` no se editan.
- Registrar bugs, fixes, decisiones y gotchas con las herramientas de projectmem.
- Notas personales de tareas por persona: `NOTES.md`.

## 7. Commits y PR

Conventional Commits v1.0.0 (spec estricta, sin desviaciones). Formato:

```text
<tipo>(<alcance>)?(!)?: <sujeto>
<línea en blanco>
<cuerpo>
<línea en blanco>
<footer>
```

PR debe indicar qué cambia y por qué, no solo qué archivos.

### 7.0 Reglas de la spec (MUST, no negociables)

Directo de conventionalcommits.org v1.0.0 — violar cualquiera de estas invalida el commit como Conventional Commit, no es cuestión de estilo:

- Header: `tipo` + alcance opcional entre paréntesis + `!` opcional + `:` + espacio único + sujeto. Sin espacio antes de los dos puntos, sujeto arranca justo tras `:`.
- `feat` únicamente para funcionalidad nueva (MINOR en semver). `fix` únicamente para corrección de bug (PATCH en semver).
- Cuerpo, si existe, separado del header por exactamente una línea en blanco.
- Footer, si existe, separado del cuerpo por una línea en blanco. Formato git trailer: `Token: valor` o `Token #valor`. El token usa guiones en vez de espacios (`Reviewed-by`, `Refs`, no "Reviewed by"). El valor de un footer puede extenderse en varias líneas hasta que aparece el siguiente token válido.
- Breaking change — dos formas, no excluyentes, con una alcanza:
  1. Footer `BREAKING CHANGE: <descripción>` (el token va siempre en mayúsculas — única unidad de la spec que es case-sensitive; `BREAKING-CHANGE` es sinónimo válido de `BREAKING CHANGE`).
  2. `!` inmediatamente antes de los dos puntos del header: `feat(scope)!: ...`.
  3. Un breaking change en cualquier tipo (no solo `feat`/`fix`) fuerza MAJOR en semver.
- `revert`: sujeto describe el commit revertido; footer obligatorio `This reverts commit <hash-completo>.`
- Tipos fuera de `feat`/`fix`/breaking (`docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`) son permitidos por la spec pero no aportan bump de semver por sí solos.

### 7.1 Reglas del proyecto (completar/ajustar, no borrar sin reemplazo)

- Idioma: sujeto/cuerpo/footer en español. Tipo siempre en inglés (estándar commitlint config-conventional).
- Sujeto: imperativo presente, minúsculas, sin punto final, ≤72 chars (ideal ≤50). Detalle en el cuerpo, nunca en el sujeto.
- Alcance opcional, kebab-case, lista cerrada del área tocada: `voz`, `agente`, `herramientas`, `api`, `interfaz`, `docs` — agregar alcance nuevo a la lista si el área es real y recurrente, no inventar uno de un solo uso; omitir si el cambio es transversal.
- Cuerpo: qué y por qué, nunca cómo (el diff ya dice cómo). Un commit = un cambio lógico.
- Footer: `Closes #N`/`Fixes #N` para issues; breaking change siempre documentado en footer aunque ya lleve `!` en el header.
- Enforcement mecánico (opcional, recomendado): `commitlint` + hook de `husky`/`lefthook` en `commit-msg` — si no está instalado, decirlo explícito, no asumir que un agente valida esto solo.

Nunca agregar trailers/firmas de autoría de agente/IA a un commit ni a un PR (líneas tipo `Co-Authored-By: <agente>`, `<Agente>-Session: <url>`, "Generated with…", enlaces de sesión, o equivalentes de cualquier herramienta, no solo una en particular), salvo que el usuario lo pida explícitamente para ese commit o PR puntual. Por defecto, mensaje de commit y descripción de PR limpios, sin firma de agente, sin importar cuál se esté usando.

**Alcance ampliado (no solo commits/PR):** sin comentarios tipo "generado por IA/agente", sin headers de archivo con firma de autoría de agente, sin menciones en README/CHANGELOG/licencias, sin watermarks en código o docs generados — salvo pedido explícito del usuario puntual para ese artefacto.

### 7.2 Gitmoji (opcional — solo si el proyecto adopta emoji por tipo de commit; si no, borrar y usar Conventional Commits plano de 7.0/7.1)

Formato con Gitmoji: `:emoji: <tipo>(<alcance>)?(!)?: <sujeto>`.

- Emoji obligatorio al inicio de todo commit, prioridad de menor a mayor:
  1. Gitmoji por defecto según tipo (gitmoji.dev), con el significado oficial de cada uno — el mapeo funciona porque coincide con la semántica del catálogo, no por convención local: `feat`→✨ (*introduce new features*), `fix`→🐛 (*fix a bug*), `docs`→📝 (*add or update documentation*), `style`→🎨 (*improve structure/format of the code*), `refactor`→♻️ (*refactor code*), `perf`→⚡️ (*improve performance*), `test`→✅ (*add, update or pass tests*), `build`→📦️ (*update compiled files or packages*), `ci`→👷 (*add or update CI build system*), `chore`→🔧 (*config/tooling change*), `revert`→⏪️ (*revert changes*).
  2. Gitmoji específico del catálogo si encaja mejor: 💥 breaking, 🎉 inicio proyecto, 🔥 quitar código, 💄 UI, 🔒 seguridad, 🚀 deploy — [agregar los que use el proyecto].
  3. Emoji personalizado para dominio del proyecto (ej. 🐋 al tocar Docker) — libre si el significado no es ambiguo.
- Excepción: merge commits y bots (dependabot) no se reescriben a este formato.
- No contradice la regla de firma de agente arriba: el emoji es semántico (tipo de cambio), no atribución de autoría — sigue sin ir `Co-Authored-By` ni equivalentes salvo pedido explícito.

### 7.3 Ramas (Git Flow completo — modelo Driessen)

Dos ramas permanentes + cuatro tipos de rama de soporte con vida limitada.

```text
support/1.x ●───────────────────────────────●  (patch a release vieja, no muere)
             \
main    ●─────●───────────●───────●──────────●───►
              ▲(tag v1.0) ▲(tag v1.0.1)      ▲(tag v1.1.0)
              │  merge    │ merge             │  merge
   release/1.0.0          │        release/1.1.0
        ▲                 │             ▲
        │  merge          │hotfix/1.0.1 │  merge
develop ●──●───●───●──────●─────●───────●───●───►
           \   \   \            \       /
       feature/a  feature/b   feature/c
```

**Ramas permanentes:**

| Rama | Rol |
| --- | --- |
| `main` (o `master`) | Producción. Todo commit en `main` es, por definición, un release, siempre tagueado. Se llega solo por merge desde `release/*` o `hotfix/*`, nunca por commit directo ni merge directo de `feature/*`. |
| `develop` | Integración. Última línea de desarrollo, punto de partida de toda `feature/*`. |

**Ramas de soporte:**

| Tipo | Nace de | Mergea a | Naming | Vive hasta |
| --- | --- | --- | --- | --- |
| `feature/*` | `develop` | `develop` (vía PR) | `feature/descripcion-corta` | PR mergeado a `develop` |
| `release/*` | `develop` | `main` **y** `develop` | `release/x.y.z` | merge + tag |
| `hotfix/*` | `main` | `main` **y** `develop` (o a `release/*` si hay una abierta — ver caso concurrente abajo) | `hotfix/descripcion-corta` | merge + tag |
| `support/*` | tag de una versión `main` vieja | solo a sí misma (parches de esa línea vieja); a `develop` únicamente vía cherry-pick si el fix aplica también a la línea actual | `support/1.x` | mientras esa versión mayor siga en soporte |

`support/*` — incluir solo si el proyecto sostiene releases legacy en simultáneo (ej. cliente enterprise en v1.x mientras develop ya está en v2.x); si no, reemplazar la fila por una línea `(no aplica: sin releases legacy en paralelo)` en vez de borrarla sin rastro. Es el tipo de rama menos estandarizado incluso en la herramienta `git-flow` original — documentar acá el criterio propio del proyecto para abrir una, no asumir default.

Versión de `release/*`/`hotfix/*` sigue semver, determinado por Conventional Commits (§7.0: `feat`→MINOR, `fix`→PATCH, breaking→MAJOR).

**Feature:**

Al terminar una feature, siempre se crea un Pull Request hacia `develop`. Nunca hacer merge directo a `develop`.

```bash
git checkout develop
git checkout -b feature/descripcion-corta
# ... trabajo, commits ...
git push -u origin feature/descripcion-corta
# Crear Pull Request hacia develop (nunca merge local directo a develop)
# Tras revisión, checks en verde y merge del PR en remoto:
git checkout develop
git pull origin develop
git branch -d feature/descripcion-corta
```

**Release** (preparar un release: freeze de features, version bump, últimos fixes menores — nada de feature nueva acá):

```bash
git checkout -b release/1.2.0 develop
# [comando de bump de versión, commit(s)]
git push -u origin release/1.2.0
# Con branch protection (GitHub/GitLab):
# 1. PR de release/1.2.0 a main -> review, CI verde, merge (--no-ff) y tag v1.2.0 en main
# 2. PR de release/1.2.0 (o back-merge) a develop -> merge (--no-ff) para sincronizar
# 3. Limpieza tras ambos merges:
git checkout develop
git pull origin develop
git branch -d release/1.2.0
# (Sin branch protection remota o con bypass administrativo local):
# git checkout main && git merge --no-ff release/1.2.0 && git tag -a v1.2.0 -m "v1.2.0"
# git checkout develop && git merge --no-ff release/1.2.0 && git branch -d release/1.2.0 && git push origin main develop --tags
```

**Hotfix** (bug crítico en producción, no puede esperar al próximo release):

```bash
git checkout -b hotfix/descripcion-corta main
# fix + commit(s), version bump de patch
git push -u origin hotfix/descripcion-corta
# Con branch protection (GitHub/GitLab):
# 1. PR de hotfix a main -> review, CI verde, merge (--no-ff) y tag v1.2.1 en main
# 2. PR de hotfix a develop (o a release/* si hay una abierta) -> merge (--no-ff)
# 3. Limpieza tras ambos merges:
git checkout develop
git pull origin develop
git branch -d hotfix/descripcion-corta
# (Sin branch protection remota o con bypass administrativo local):
# git checkout main && git merge --no-ff hotfix/descripcion-corta && git tag -a v1.2.1 -m "v1.2.1"
# git checkout develop && git merge --no-ff hotfix/descripcion-corta && git branch -d hotfix/descripcion-corta && git push origin main develop --tags
```

**Caso concurrente (hotfix mientras hay release abierta):** el hotfix mergea a `main` y se taguea igual, pero el segundo merge va a `release/*` en vez de a `develop` (vía PR si hay branch protection) — la release ya tiene el fix cuando eventualmente mergee a `develop`. Nunca mergear el mismo hotfix dos veces a `develop`.

`--no-ff` siempre (nunca fast-forward) — conserva el commit de merge como marcador de la rama completa, necesario para revertir la feature/release/hotfix entera con un solo `git revert -m 1 <hash-del-merge>`.

**Reglas nunca:**

- Nunca merge directo de `feature/*` a `develop` — al terminar una feature, siempre se crea un Pull Request hacia `develop`, nunca merge directo.
- Nunca commit directo a `main` o `develop` — todo entra por PR o merge de rama de soporte autorizada.
- Nunca force-push a `main`, `develop`, `release/*` o `hotfix/*` una vez publicadas — son ramas compartidas.
- Nunca rebase de una rama ya pusheada que otros puedan tener checkout local (`feature/*` propia sí se puede rebasear antes de publicar).
- Nunca borrar `release/*`/`hotfix/*` sin haber mergeado a ambos destinos — si se aborta, documentarlo en el PR/issue antes de borrar.

**Branch protection / PR (si el remoto es GitHub/GitLab):** `main` y `develop` protegidas, requieren PR + al menos 1 review antes de merge, checks de CI en verde obligatorios. `release/*` y `hotfix/*` heredan la misma exigencia por ser destino de merge a `main`. `feature/*` sin restricción, es la rama de trabajo diario.

**CLI `git-flow` (opcional):** si el equipo prefiere no memorizar los comandos de arriba, la extensión `git-flow` (nvie/AVH) los envuelve 1:1 — `git flow feature start/finish`, `git flow release start/finish`, `git flow hotfix start/finish`. Equivalente funcional, no un modelo distinto; no instalarla si nadie del equipo la va a usar, los comandos crudos de arriba alcanzan.

**Limpieza:** rama de soporte mergeada se borra local y remota en el mismo flujo de finish (comandos de arriba ya lo hacen) — no dejar `feature/*` viejas acumulándose tras el merge.

(Proyecto chico/sin versionado semver real: usar variante lite — solo `main`+`develop`+`feature/*`+`hotfix/*`, sin `release/*` ni `support/*` — pero dejarlo dicho explícito acá, no aplicar full Git Flow a medias sin nombrarlo.)

**Antes de adoptar este modelo, leer la advertencia del propio autor.** En 2020 Driessen agregó una nota de reflexión al artículo original: el modelo se volvió dogma pese a haber sido escrito para un contexto distinto. Su criterio:

| Contexto del proyecto | Qué recomienda |
| --- | --- |
| Software con versionado explícito, varias versiones vivas en producción a la vez (desktop, librerías, on-premise, clientes en versiones distintas) | Git Flow sigue siendo adecuado |
| Aplicación web con entrega continua, una sola versión en producción, sin necesidad de soportar versiones viejas | un flujo mucho más simple, tipo **GitHub Flow** (`main` + ramas de feature de vida corta) |

"No hay panaceas": elegir con el contexto propio a la vista. Si este proyecto es una web con deploy continuo y aun así se copia Git Flow completo, el resultado son `release/*` ceremoniales que no aportan nada y dos ramas permanentes que hay que sincronizar a mano. Decidirlo explícitamente acá — y si se elige GitHub Flow, reemplazar esta subsección entera por ese modelo, no dejar las dos descripciones conviviendo.
