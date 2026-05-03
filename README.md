# Professor Copilot — Database Migrations

Proyecto Alembic para gestionar las migraciones de la base de datos PostgreSQL del EdTech MVP.

## Requisitos

- Python 3.11+
- PostgreSQL 13+ (se usa `gen_random_uuid()` nativo)
- pip / venv

---

## Setup inicial

```bash
# 1. Crear entorno virtual
python -m venv .venv

# 2. Activarlo
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# 3. Instalar dependencias
pip install -e .

# 4. Configurar variables de entorno
cp .env.example .env
# Edita .env con tu DATABASE_URL real
```

---

## Uso diario

### Aplicar todas las migraciones pendientes
```bash
alembic upgrade head
```

### Ver el estado actual
```bash
alembic current
```

### Ver el historial de migraciones
```bash
alembic history --verbose
```

### Aplicar N migraciones hacia adelante
```bash
alembic upgrade +1
alembic upgrade +3
```

### Revertir la última migración
```bash
alembic downgrade -1
```

### Revertir hasta el inicio (sin datos, sin tablas)
```bash
alembic downgrade base
```

---

## Inicialización completa (desarrollo)

El script `db_init.py` crea la BD si no existe y aplica todas las migraciones:

```bash
python scripts/db_init.py
```

## Reset de desarrollo

⚠️ **Solo para desarrollo local.** Revierte todas las migraciones y las vuelve a aplicar:

```bash
# Reset suave (downgrade base → upgrade head)
python scripts/db_reset.py

# Reset duro (DROP DATABASE + CREATE DATABASE + upgrade head)
python scripts/db_reset.py --hard

# Sin confirmación interactiva
python scripts/db_reset.py --yes
python scripts/db_reset.py --hard --yes
```

---

## Crear una nueva migración

```bash
# Formato: alembic revision --rev-id <id_4_digitos> -m "descripcion"
alembic revision --rev-id 0014 -m "add_assignment_tags"
```

Esto crea `migrations/versions/0014_add_assignment_tags.py` listo para editar.

### Convenciones para nuevas migraciones

1. **ID secuencial de 4 dígitos**: `0014`, `0015`, etc.
2. **`upgrade()` y `downgrade()` siempre implementados** — nunca dejar `pass`.
3. **SQL puro via `op.execute()`** — no usar helpers de SQLAlchemy que no soporten features de PG.
4. **Atómico**: una migración = un cambio lógico (no mezclar tabla + trigger + vista).
5. **Comentarios**: explicar el `WHY`, no el `WHAT`.

---

## Generar SQL sin ejecutar (modo offline)

Útil para auditoría o despliegue controlado en producción:

```bash
# Generar SQL de upgrade desde el estado actual hasta head
alembic upgrade head --sql > upgrade_to_head.sql

# Generar SQL de un paso específico
alembic upgrade 0013:0014 --sql
```

---

## Estructura del proyecto

```
professor-copilot-database/
├── alembic.ini                     # Config principal de Alembic
├── pyproject.toml                  # Dependencias Python
├── .env.example                    # Plantilla de variables de entorno
├── .gitignore
│
├── migrations/
│   ├── env.py                      # Entorno de Alembic (carga .env, config multi-schema)
│   ├── script.py.mako              # Template para nuevas revisiones
│   └── versions/
│       ├── 0001_create_schemas_and_enums.py
│       ├── 0002_auth_tables.py
│       ├── 0003_billing_plans_and_packages.py
│       ├── 0004_billing_wallet_and_transactions.py
│       ├── 0005_billing_subscriptions_and_quotas.py
│       ├── 0006_core_api_keys_and_ai_configs.py
│       ├── 0007_pedagogy_assignments.py
│       ├── 0008_pedagogy_submissions_and_grades.py
│       ├── 0009_ops_export_and_audit_logs.py
│       ├── 0010_functions_and_triggers.py
│       ├── 0011_row_level_security.py
│       ├── 0012_views.py
│       └── 0013_seeds.py
│
└── scripts/
    ├── db_init.py                  # Crear BD + upgrade head
    └── db_reset.py                 # Reset para desarrollo
```

---

## Schemas y tablas

| Schema | Tablas |
|--------|--------|
| `auth` | `users`, `user_sessions` |
| `billing` | `plans`, `token_packages`, `token_wallet`, `token_transactions`, `subscriptions`, `usage_quotas` |
| `core` | `api_keys`, `ai_model_configs`, `user_ai_preferences` |
| `pedagogy` | `assignments`, `submissions`, `grades` |
| `ops` | `export_logs`, `audit_logs` |

### Vistas
- `pedagogy.v_grades_export` — exportación CSV plana de calificaciones
- `billing.v_usage_summary` — resumen de uso para panel admin

### Triggers automáticos
| Trigger | Tabla | Evento | Efecto |
|---------|-------|--------|--------|
| `trg_updated_at` | Todas con `updated_at` | BEFORE UPDATE | Sincroniza `updated_at = NOW()` |
| `trg_wallet_on_signup` | `auth.users` | AFTER INSERT | Crea `token_wallet` con saldo 0 |
| `trg_grant_tokens_on_subscription` | `billing.subscriptions` | AFTER UPDATE status | Acredita tokens iniciales del plan |
| `trg_deduct_tokens_on_grade` | `pedagogy.grades` | AFTER INSERT | Descuenta wallet si `token_source = 'platform'` |

---

## Despliegue en producción

```bash
# 1. Verificar qué migraciones están pendientes
alembic history -v

# 2. Generar el SQL completo para revisión (dry run)
alembic upgrade head --sql > pending_upgrade.sql
# Revisar pending_upgrade.sql antes de aplicar

# 3. Aplicar
alembic upgrade head
```

> **Nunca uses `db_reset.py` en producción.** El script tiene una protección
> que revisa `APP_ENV` y se niega a correr si no es un entorno de desarrollo.

---

## Variables de entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | URL de conexión PostgreSQL | `postgresql://user:pass@host:5432/dbname` |
| `APP_ENV` | Entorno de la aplicación (protege db_reset) | `development` \| `production` |
