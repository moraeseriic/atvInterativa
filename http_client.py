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


async def main(n: int, intervalo: float, continuo: bool):
    sensor = Sensor("sensor-http")
    async with httpx.AsyncClient(timeout=5.0) as client:
        i = 0
        while True:
            if not continuo and i >= n:
                break
            corpo = sensor.read_json()
            tam = tamanho_http(corpo)
            label = f"#{i + 1} (∞)" if continuo else f"{i + 1}/{n}"
            for t in range(1, _TENTATIVAS + 1):
                try:
                    r = await client.post(URL, content=corpo, headers={"Content-Type": "application/json"})
                    logger.info("envio %s | req~%dB | resp HTTP %d", label, tam, r.status_code)
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


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--intervalo", type=float, default=1.0)
    p.add_argument("--continuo", action="store_true", help="loop infinito até Ctrl+C")
    args = p.parse_args()
    try:
        asyncio.run(main(args.n, args.intervalo, args.continuo))
    except KeyboardInterrupt:
        logger.info("encerrado pelo usuário")
