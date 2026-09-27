"""
Entrena un RandomForestClassifier (Capa 1.5c).
Lee features de fct_prices, fct_market_signals y fct_liquidity_alerts;
predice los tres targets binarios de riesgo a 7 dias.
Escribe con method='random_forest_classifier', sin banda de confianza,
solo en vivo, con INSERT ... ON CONFLICT (6 columnas) DO NOTHING (4.7.3).
Job aparte del cron horario: lo dispara train-ml-forecast.yml (semanal,
GitHub Actions), no el scheduler de Railway.
TODO: implementar.
"""
