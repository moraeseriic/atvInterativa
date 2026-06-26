# Estado compartilhado entre processos via arquivos JSON.
# Cada servidor grava o próprio estado; o dashboard lê os dois.
import json
import os
import time

# aponta para a raiz do projeto (pai de core/)
_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _path(proto: str) -> str:
    return os.path.join(_DIR, f"_estado_{proto}.json")


def gravar(protocolo: str, leitura: dict, total_bytes: int, payload_bytes: int, contador: int) -> None:
    dados = {
        "protocolo": protocolo,
        "leitura": leitura,
        "total_bytes": total_bytes,
        "payload_bytes": payload_bytes,
        "mensagens": contador,
        "atualizado_em": time.time(),
    }
    tmp = _path(protocolo) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f)
    os.replace(tmp, _path(protocolo))  # escrita atômica


def ler(protocolo: str) -> dict | None:
    try:
        with open(_path(protocolo), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def limpar() -> None:
    for proto in ("http", "coap"):
        try:
            os.remove(_path(proto))
        except FileNotFoundError:
            pass
