# Funções para calcular o overhead HTTP (requisição e resposta).


def tamanho_http(payload: bytes) -> int:
    linha = "POST /sensor HTTP/1.1\r\n"
    headers = (
        "Host: 127.0.0.1:8000\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(payload)}\r\n"
        "Accept: */*\r\n"
        "Connection: keep-alive\r\n"
        "\r\n"
    )
    return len(linha.encode()) + len(headers.encode()) + len(payload)


def tamanho_http_resposta(payload_req: bytes) -> int:
    """Estima tamanho da resposta HTTP 201 retornada pelo servidor FastAPI/uvicorn."""
    body = b'{"status":"ok","recebido":' + payload_req + b'}'
    linha = "HTTP/1.1 201 Created\r\n"
    headers = (
        "date: Tue, 01 Jul 2025 00:00:00 GMT\r\n"
        "server: uvicorn\r\n"
        f"content-length: {len(body)}\r\n"
        "content-type: application/json\r\n"
        "\r\n"
    )
    return len(linha.encode()) + len(headers.encode()) + len(body)


def resumo_por_tamanho(n_payload: int) -> dict:
    return resumo(b"x" * n_payload)


def resumo_completo_por_tamanho(n_payload: int) -> dict:
    return resumo_completo(b"x" * n_payload)


def resumo(payload: bytes) -> dict:
    http_total = tamanho_http(payload)
    p = len(payload)
    return {
        "payload": p,
        "http_total": http_total,
        "http_overhead": http_total - p,
        "overhead_pct": round(100 * (http_total - p) / http_total, 1),
    }


def resumo_completo(payload: bytes) -> dict:
    req = resumo(payload)
    resp_total = tamanho_http_resposta(payload)
    resp_body = len(b'{"status":"ok","recebido":' + payload + b'}')
    resp_overhead = resp_total - resp_body
    roundtrip = req["http_total"] + resp_total
    total_overhead = req["http_overhead"] + resp_overhead
    return {
        **req,
        "resp_total": resp_total,
        "resp_overhead": resp_overhead,
        "resp_payload": resp_body,
        "roundtrip": roundtrip,
        "roundtrip_overhead": total_overhead,
        "roundtrip_overhead_pct": round(100 * total_overhead / roundtrip, 1),
    }
