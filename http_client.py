# Cliente HTTP — simula sensores IoT enviando leituras para o servidor.
# Rodar: python http_client.py --n 10 --intervalo 1
# Demo:  python http_client.py --continuo --sensores 3

import argparse
import asyncio
import logging
import time as _time

import httpx

from core.sensor import Sensor
from core.tamanhos import tamanho_http

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

URL = "http://127.0.0.1:8000/sensor"
URL_METRICAS = "http://127.0.0.1:8000/api/metricas"
_TENTATIVAS = 3


async def run_sensor(client: httpx.AsyncClient, sensor: Sensor, n: int, intervalo: float, continuo: bool):
    i = 0
    while True:
        if not continuo and i >= n:
            break
        corpo = sensor.read_json()
        tam = tamanho_http(corpo)
        label = f"{sensor.sensor_id} #{i + 1}" + (" (∞)" if continuo else f"/{n}")
        t_start = _time.monotonic()
        for t in range(1, _TENTATIVAS + 1):
            try:
                r = await client.post(URL, content=corpo, headers={"Content-Type": "application/json"})
                rtt_ms = round((_time.monotonic() - t_start) * 1000, 2)
                logger.info("envio %s | req~%dB | HTTP %d | RTT %.1fms", label, tam, r.status_code, rtt_ms)
                try:
                    await client.post(URL_METRICAS, json={"rtt_ms": rtt_ms, "sensor_id": sensor.sensor_id}, timeout=1.0)
                except Exception:
                    pass
                break
            except httpx.ConnectError:
                logger.warning("servidor indisponivel (tentativa %d/%d)", t, _TENTATIVAS)
                if t < _TENTATIVAS:
                    await asyncio.sleep(1)
            except Exception as exc:
                logger.error("erro inesperado: %s", exc)
                break
        i += 1
        if continuo or i < n:
            await asyncio.sleep(intervalo)


async def main(n: int, intervalo: float, continuo: bool, sensores: int):
    ids = [f"sensor-http-{i + 1}" if sensores > 1 else "sensor-http" for i in range(sensores)]
    sensor_list = [Sensor(sid) for sid in ids]
    async with httpx.AsyncClient(timeout=5.0) as client:
        await asyncio.gather(*[run_sensor(client, s, n, intervalo, continuo) for s in sensor_list])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--intervalo", type=float, default=1.0)
    p.add_argument("--continuo", action="store_true", help="loop infinito até Ctrl+C")
    p.add_argument("--sensores", type=int, default=1, metavar="N", help="número de sensores simultâneos")
    args = p.parse_args()
    try:
        asyncio.run(main(args.n, args.intervalo, args.continuo, args.sensores))
    except KeyboardInterrupt:
        logger.info("encerrado pelo usuário")
