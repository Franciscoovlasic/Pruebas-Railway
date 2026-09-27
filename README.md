# Pipeline-ELT

Bloque 1 del sistema de analisis y prediccion de mercado cripto: ELT sobre
velas horarias (OHLC) de Binance, OKX y Coinbase (Python + Pandas), dbt
sobre PostgreSQL (Neon), motor de prediccion, y orquestacion via el
scheduler de contenedores de Railway.

## Estructura

- `src/` — adaptadores por exchange, extraccion, carga, backfill,
  orquestacion, alertas, narrador, backups, seeders y el job de ML.
- `tools/` — sondas de verificacion, no forman parte del pipeline.
- `sql/` — DDL de tablas de aplicacion y consultas de soporte.
- `dbt/` — proyecto dbt (staging / intermediate / marts).
- `.github/workflows/` — CI, entrenamiento semanal de ML, backfill puntual,
  monitoreo de Binance y sondas manuales. El cron horario de produccion
  corre en Railway (`railway.toml`), no aca (ver 9.5).
- `railway.toml` — config del servicio cron de Railway.

## Setup local

```bash
python -m venv env
source env/bin/activate        # Windows: env\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # completar con las credenciales reales
docker compose up -d           # Postgres local, si no se usa el hosteado
```

## Estado

Capa 0 — Scaffolding. Todavia no hay logica implementada; solo la
estructura del repo y los archivos de configuracion base.
