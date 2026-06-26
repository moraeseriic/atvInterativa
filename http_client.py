# Cliente HTTP — simula um sensor IoT enviando leituras para o servidor.
# Rodar: python http_client.py --n 10 --intervalo 1

import argparse
import asyncio
import logging

import httpx

from core.sensor import Sensor
from core.tamanhos import tamanho_http

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

URL = "http://127.0.0.1:8000/sensor"
_TENTATIVAS = 3


async def main(n: int, intervalo: float):
    sensor = Sensor("sensor-http")
    async with httpx.AsyncClient(timeout=5.0) as client:
        for i in range(n):
            corpo = sensor.read_json()
            tam = tamanho_http(corpo)
            for t in range(1, _TENTATIVAS + 1):
                try:
                    r = await client.post(URL, content=corpo, headers={"Content-Type": "application/json"})
                    logger.info("envio %d/%d | req~%dB | resp HTTP %d", i + 1, n, tam, r.status_code)
                    break
                except httpx.ConnectError:
                    logger.warning("servidor indisponivel (tentativa %d/%d)", t, _TENTATIVAS)
                    if t < _TENTATIVAS:
                        await asyncio.sleep(1)
                except Exception as exc:
                    logger.error("erro inesperado: %s", exc)
                    break
            if i < n - 1:
                await asyncio.sleep(intervalo)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--intervalo", type=float, default=1.0)
    args = p.parse_args()
    asyncio.run(main(args.n, args.intervalo))
