# Funções para calcular o overhead HTTP.


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


def resumo_por_tamanho(n_payload: int) -> dict:
    return resumo(b"x" * n_payload)


def resumo(payload: bytes) -> dict:
    http_total = tamanho_http(payload)
    p = len(payload)
    return {
        "payload": p,
        "http_total": http_total,
        "http_overhead": http_total - p,
        "overhead_pct": round(100 * (http_total - p) / http_total, 1),
    }
