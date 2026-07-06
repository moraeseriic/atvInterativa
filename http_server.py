"""
Servidor HTTP — FastAPI porta 8000.
Recebe leituras de sensores IoT via POST /sensor e serve o dashboard.

Rodar: python http_server.py
"""

import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core import estado
from core.tamanhos import resumo_completo_por_tamanho, tamanho_http

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
_contador = {"posts": 0, "bytes_acumulados": 0}
_primeiro_post_em: float | None = None
_metricas_rtt: list[float] = []
_MAX_RTT = 100


@app.post("/sensor", status_code=201)
async def receber_leitura(request: Request):
    """Recebe leitura JSON de um sensor IoT via HTTP POST."""
    global _primeiro_post_em
    corpo = await request.body()
    dados = await request.json()
    sensor_id = dados.get("id", "desconhecido")
    _ultimas_leituras[sensor_id] = dados
    tam = tamanho_http(corpo)
    _contador["posts"] += 1
    _contador["bytes_acumulados"] += tam
    if _primeiro_post_em is None:
        _primeiro_post_em = time.time()
    logger.info("POST #%d de %s → %d B (acum %d B)", _contador["posts"], sensor_id, tam, _contador["bytes_acumulados"])
    estado.gravar(
        "http",
        leitura=dados,
        total_bytes=tam,
        payload_bytes=len(corpo),
        contador=_contador["posts"],
        bytes_acumulados=_contador["bytes_acumulados"],
    )
    return {"status": "ok", "recebido": dados}


@app.post("/api/metricas")
async def receber_metricas(request: Request):
    """Recebe métricas de desempenho do cliente (RTT medido no cliente)."""
    dados = await request.json()
    rtt = dados.get("rtt_ms")
    if isinstance(rtt, (int, float)) and rtt > 0:
        _metricas_rtt.append(round(rtt, 2))
        if len(_metricas_rtt) > _MAX_RTT:
            _metricas_rtt.pop(0)
    return {"ok": True}


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
    """Retorna estatísticas HTTP em tempo real (overhead + RTT + throughput + sensores)."""
    try:
        http_estado = estado.ler("http")
        n_payload = 68
        if http_estado and http_estado.get("payload_bytes", 0) > 0:
            n_payload = http_estado["payload_bytes"]

        msgs_por_seg = None
        bytes_por_seg = None
        if _primeiro_post_em is not None:
            elapsed = time.time() - _primeiro_post_em
            if elapsed > 0:
                msgs_por_seg = round(_contador["posts"] / elapsed, 2)
                bytes_por_seg = round(_contador["bytes_acumulados"] / elapsed, 1)

        rtt_stats = None
        if _metricas_rtt:
            rtt_stats = {
                "atual": _metricas_rtt[-1],
                "media": round(sum(_metricas_rtt) / len(_metricas_rtt), 2),
                "min": round(min(_metricas_rtt), 2),
                "max": round(max(_metricas_rtt), 2),
                "amostras": len(_metricas_rtt),
            }

        return {
            "http": {
                **(http_estado or {}),
                "msgs_por_seg": msgs_por_seg,
                "bytes_por_seg": bytes_por_seg,
            },
            "overhead": resumo_completo_por_tamanho(n_payload),
            "rtt": rtt_stats,
            "sensores": _ultimas_leituras,
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
