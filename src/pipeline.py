"""
Orquestacion (Capa 1.1 / 1.6).
1.1: extraccion -> carga.
1.6: suma dbt run / dbt test / pronostico / alertas, registrando cada paso
en pipeline_runs. Lo ejecuta el scheduler de contenedores de Railway
(cronSchedule en railway.toml), no un workflow de GitHub Actions.
Valida no-solapamiento contra pipeline_runs (o advisory lock de Postgres)
antes de arrancar (ver 9.5).
TODO: implementar.
"""
