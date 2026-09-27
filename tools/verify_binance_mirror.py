"""
Sonda de verificacion, no forma parte del pipeline (Capa 1.0 / 1.1 / 1.2, ver seccion 8.0/9.5).

Confirma que `data-api.binance.vision` sirve la misma serie que
`api.binance.com` (seccion 1.2, hallazgo 2): compara, vela a vela y con
los 12 campos de `/klines`, tres tramos:

  1. La primera vela de la serie (17/08/2017 04:00 UTC).
  2. 1000 velas desde el origen hasta el 01/01/2020.
  3. Las 1000 velas cerradas mas recientes.

IMPORTANTE: solo tiene sentido correr esto desde una red donde
`api.binance.com` responda (maquina local). Desde GitHub Actions o Railway
`api.binance.com` devuelve 451 (bloqueo por region, ver T8 /
probe_binance_hosts.py) y esta sonda va a fallar por eso, no porque las
series difieran.

Uso:
    python tools/verify_binance_mirror.py
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone

import requests

REFERENCE_HOST = "api.binance.com"
MIRROR_HOST = "data-api.binance.vision"

PATH = "/api/v3/klines"
SYMBOL = "BTCUSDT"
INTERVAL = "1h"

# 17/08/2017 04:00:00 UTC, primera vela confirmada de BTCUSDT (seccion 1).
ORIGIN_OPEN_TIME_MS = 1502942400000
# 01/01/2020 00:00:00 UTC.
JAN_2020_MS = 1577836800000

CONNECT_TIMEOUT_S = 5
READ_TIMEOUT_S = 15

# Los 12 campos que devuelve /klines, en orden (seccion 1, bajo Binance).
FIELDS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "num_trades",
    "taker_buy_base_vol",
    "taker_buy_quote_vol",
    "ignore",
]


def fetch_klines(host: str, **params) -> list[list]:
    url = f"https://{host}{PATH}"
    query = {"symbol": SYMBOL, "interval": INTERVAL, **params}
    resp = requests.get(url, params=query, timeout=(CONNECT_TIMEOUT_S, READ_TIMEOUT_S))
    resp.raise_for_status()
    return resp.json()


def floor_hour_minus_1h_ms(now: datetime) -> int:
    """Ultima vela cerrada: la hora actual redondeada hacia abajo, menos 1h."""
    floored = now.replace(minute=0, second=0, microsecond=0)
    closed = floored - timedelta(hours=1)
    return int(closed.timestamp() * 1000)


def diff_candles(label: str, ref: list[list], mirror: list[list]) -> list[str]:
    problems = []
    if len(ref) != len(mirror):
        problems.append(
            f"[{label}] cantidad de velas distinta: "
            f"{REFERENCE_HOST}={len(ref)} vs {MIRROR_HOST}={len(mirror)}"
        )
    for i, (a, b) in enumerate(zip(ref, mirror)):
        if a != b:
            for field, va, vb in zip(FIELDS, a, b):
                if va != vb:
                    problems.append(
                        f"[{label}] vela #{i} (open_time={a[0]}) difiere en '{field}': "
                        f"{REFERENCE_HOST}={va!r} vs {MIRROR_HOST}={vb!r}"
                    )
    return problems


def compare(label: str, **params) -> list[str]:
    print(f"Comparando: {label} ...")
    try:
        ref = fetch_klines(REFERENCE_HOST, **params)
        time.sleep(0.2)  # cortesia, no forma parte del rate-limit policy de 1.2
        mirror = fetch_klines(MIRROR_HOST, **params)
    except requests.exceptions.RequestException as exc:
        msg = (
            f"[{label}] no se pudo comparar: {type(exc).__name__}: {exc}. "
            f"Si esto corre desde GitHub Actions o Railway, es esperable: "
            f"{REFERENCE_HOST} esta bloqueado por region ahi (ver T8 / "
            f"probe_binance_hosts.py). Correr esta sonda solo desde la "
            f"maquina local."
        )
        print(f"  {msg}")
        return [msg]
    problems = diff_candles(label, ref, mirror)
    if not problems:
        print(f"  OK: {len(ref)} velas identicas en los {len(FIELDS)} campos.")
    else:
        for p in problems:
            print(f"  DIFERENCIA: {p}")
    return problems


def main() -> int:
    all_problems: list[str] = []

    all_problems += compare(
        "primera vela de la serie",
        startTime=ORIGIN_OPEN_TIME_MS,
        limit=1,
    )

    all_problems += compare(
        "1000 velas desde el origen hasta 01/01/2020",
        startTime=ORIGIN_OPEN_TIME_MS,
        endTime=JAN_2020_MS,
        limit=1000,
    )

    now = datetime.now(timezone.utc)
    last_closed_ms = floor_hour_minus_1h_ms(now)
    all_problems += compare(
        "1000 velas cerradas mas recientes",
        endTime=last_closed_ms,
        limit=1000,
    )

    print()
    if not all_problems:
        print(f"RESULTADO: {MIRROR_HOST} es un espejo exacto de {REFERENCE_HOST} en los tres tramos.")
        return 0

    print(f"RESULTADO: {len(all_problems)} diferencia(s) encontradas. Ver detalle arriba.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
