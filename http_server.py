"""
Servidor HTTP — FastAPI porta 8000.
Recebe leituras de sensores IoT via POST /sensor e serve o dashboard.

Rodar: python http_server.py
"""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core import estado
from core.tamanhos import resumo_por_tamanho, tamanho_http

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="IoT HTTP Server — Atividade Interativa")

_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC = os.path.join(_DIR, "static")

_ultimas_leituras: dict[str, dict] = {}
_contador = {"posts": 0}


@app.post("/sensor", status_code=201)
async def receber_leitura(request: Request):
    """Recebe leitura JSON de um sensor IoT via HTTP POST."""
    corpo = await request.body()
    dados = await request.json()
    sensor_id = dados.get("id", "desconhecido")
    _ultimas_leituras[sensor_id] = dados
    _contador["posts"] += 1
    logger.info("POST #%d de %s → %d B total", _contador["posts"], sensor_id, tamanho_http(corpo))
    estado.gravar(
        "http",
        leitura=dados,
        total_bytes=tamanho_http(corpo),
        payload_bytes=len(corpo),
        contador=_contador["posts"],
    )
    return {"status": "ok", "recebido": dados}


@app.get("/sensor/{sensor_id}")
async def consultar_leitura(sensor_id: str):
    """Retorna a última leitura de um sensor específico."""
    if sensor_id not in _ultimas_leituras:
        return JSONResponse(status_code=404, content={"erro": "sensor não encontrado"})
    return _ultimas_leituras[sensor_id]


@app.get("/sensor")
async def listar_sensores():
    """Lista todos os sensores e suas últimas leituras."""
    return {"sensores": list(_ultimas_leituras.keys()), "total": len(_ultimas_leituras)}


@app.get("/health")
async def health():
    """Verificação de saúde do servidor."""
    return {"status": "vivo", "posts_recebidos": _contador["posts"]}


@app.get("/api/stats")
async def stats():
    """Retorna estatísticas HTTP em tempo real (leitura atual + overhead)."""
    try:
        http_estado = estado.ler("http")
        n_payload = 68
        if http_estado and http_estado.get("payload_bytes", 0) > 0:
            n_payload = http_estado["payload_bytes"]
        return {
            "http": http_estado,
            "overhead": resumo_por_tamanho(n_payload),
        }
    except Exception as exc:
        logger.error("erro em /api/stats: %s", exc)
        return JSONResponse(status_code=500, content={"erro": str(exc)})


@app.get("/")
async def dashboard():
    """Serve o dashboard HTTP em tempo real."""
    return FileResponse(os.path.join(_STATIC, "dashboard.html"))


if os.path.isdir(_STATIC):
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")


if __name__ == "__main__":
    import uvicorn
    print("=" * 54)
    print("  Servidor HTTP IoT — Atividade Interativa")
    print("  Dashboard: http://127.0.0.1:8000/")
    print("  Docs:      http://127.0.0.1:8000/docs")
    print("=" * 54)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
