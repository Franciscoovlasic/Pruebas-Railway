"""
Sonda de verificacion, no forma parte del pipeline (Capa 1.0 / 1.1 / 1.2, ver seccion 8.0/9.5).

Ticket T8 (8.0): confirmar si Binance bloquea por region desde la IP que
esta corriendo el script. Pega contra `api.binance.com`, sus alias
`api1`-`api4` y `data-api.binance.vision`, y registra el status HTTP y la
latencia de cada uno.

Criterio de cierre de T8 (9.5, punto 3): `data-api.binance.vision` responde
200 con velas. Si ademas `api.binance.com` devuelve 451 desde esa misma IP,
confirma el mismo bloqueo por region que ya se vio desde GitHub Actions
(seccion 1.2, hallazgo 1); si devolviera 200, el bloqueo seria especifico
de Actions y no de "cualquier IP fuera de EEUU", lo cual cambiaria el
diagnostico.

Uso:
    python tools/probe_binance_hosts.py
    python tools/probe_binance_hosts.py --log reports/probe_binance_hosts.log

Sale con status 0 si `data-api.binance.vision` respondio 200, y 1 si no
(para que un workflow pueda marcar el paso como fallido).
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

HOSTS = [
    "api.binance.com",
    "api1.binance.com",
    "api2.binance.com",
    "api3.binance.com",
    "api4.binance.com",
    "data-api.binance.vision",
]

# Vela mas liviana posible: 1 resultado, sin paginar. No exige API key
# (lectura publica, ver seccion 1 del documento).
PATH = "/api/v3/klines"
PARAMS = {"symbol": "BTCUSDT", "interval": "1h", "limit": 1}

CONNECT_TIMEOUT_S = 5
READ_TIMEOUT_S = 15

VISION_HOST = "data-api.binance.vision"

# Sin key, uso no comercial: http://ip-api.com/docs/api:json (rate limit
# 45 req/min, de sobra para una corrida cada 2h). Sirve para saber si el
# bloqueo va atado al rango/ASN de salida (AWS, Railway, etc.) y no a una
# IP puntual, comparando corridas con IPs distintas a lo largo del tiempo.
EGRESS_INFO_URL = "http://ip-api.com/json/?fields=query,as,isp,country"


@dataclass
class EgressInfo:
    ip: str
    asn: str
    isp: str
    country: str


def get_egress_info() -> EgressInfo:
    try:
        resp = requests.get(EGRESS_INFO_URL, timeout=(CONNECT_TIMEOUT_S, READ_TIMEOUT_S))
        resp.raise_for_status()
        data = resp.json()
        return EgressInfo(
            ip=data.get("query", ""),
            asn=data.get("as", ""),
            isp=data.get("isp", ""),
            country=data.get("country", ""),
        )
    except requests.exceptions.RequestException:
        return EgressInfo(ip="", asn="", isp="", country="")


@dataclass
class ProbeResult:
    timestamp_utc: str
    host: str
    status_code: "int | None"
    latency_ms: "float | None"
    error: str
    egress_ip: str = ""
    egress_asn: str = ""


def probe_host(host: str) -> ProbeResult:
    url = f"https://{host}{PATH}"
    ts = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    try:
        resp = requests.get(
            url,
            params=PARAMS,
            timeout=(CONNECT_TIMEOUT_S, READ_TIMEOUT_S),
        )
        latency_ms = (time.monotonic() - start) * 1000
        # Un 451/403 trae cuerpo de error, no velas: no hace falta parsear
        # el JSON para el proposito de esta sonda (status alcanza).
        return ProbeResult(ts, host, resp.status_code, round(latency_ms, 1), "")
    except requests.exceptions.RequestException as exc:
        latency_ms = (time.monotonic() - start) * 1000
        return ProbeResult(ts, host, None, round(latency_ms, 1), type(exc).__name__)


def append_log(results: list[ProbeResult], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not log_path.exists()
    with log_path.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(
                ["timestamp_utc", "host", "status_code", "latency_ms", "error", "egress_ip", "egress_asn"]
            )
        for r in results:
            writer.writerow(
                [r.timestamp_utc, r.host, r.status_code, r.latency_ms, r.error, r.egress_ip, r.egress_asn]
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("reports/probe_binance_hosts.log"),
        help="CSV donde se acumula el resultado de cada corrida (append).",
    )
    args = parser.parse_args()

    egress = get_egress_info()
    print(f"IP de salida de esta corrida: {egress.ip or '(desconocida)'}  |  ASN/ISP: {egress.asn or egress.isp or '(desconocido)'}  |  pais: {egress.country}\n")

    results = [probe_host(host) for host in HOSTS]
    for r in results:
        r.egress_ip = egress.ip
        r.egress_asn = egress.asn

    print(f"{'host':<24} {'status':<8} {'latencia_ms':<12} error")
    for r in results:
        status = str(r.status_code) if r.status_code is not None else "SIN RESPUESTA"
        print(f"{r.host:<24} {status:<8} {r.latency_ms:<12} {r.error}")

    append_log(results, args.log)
    print(f"\nLog acumulado en: {args.log}")

    vision_result = next(r for r in results if r.host == VISION_HOST)
    if vision_result.status_code == 200:
        print(f"\nOK: {VISION_HOST} responde 200 desde esta IP.")
        return 0

    print(
        f"\nFALLO: {VISION_HOST} no respondio 200 desde esta IP "
        f"(status={vision_result.status_code}, error={vision_result.error}). "
        "Ver seccion 9.5 punto 3 (riesgo residual / plan B)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
