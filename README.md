# HTTP IoT — Atividade Interativa
### Redes de Computadores

Aplicação que **simula um sensor IoT** enviando leituras de temperatura e umidade via **HTTP/1.1** para um servidor FastAPI. Foco na análise do protocolo: estrutura das mensagens, overhead de headers e funcionamento do modelo cliente-servidor.

---

## Estrutura

```
atvInterativa/
├── core/
│   ├── sensor.py       # Gerador de leituras (temperatura + umidade)
│   ├── estado.py       # Estado compartilhado entre processos (JSON/IPC)
│   └── tamanhos.py     # Cálculo de overhead HTTP
├── static/
│   └── dashboard.html  # Dashboard em tempo real (servido pelo FastAPI)
├── http_server.py      # Servidor HTTP — FastAPI, porta 8000 TCP
├── http_client.py      # Cliente HTTP — httpx assíncrono, simula sensor
└── requirements.txt    # fastapi · uvicorn · httpx
```

---

## O protocolo HTTP nesta atividade

### Modelo cliente-servidor

O sensor atua como **cliente** e inicia sempre a comunicação. O servidor processa e devolve uma resposta. Esse é o modelo **requisição-resposta** do HTTP — sem estado (*stateless*): cada troca é independente.

```
   ┌─────────────┐   POST /sensor (JSON)   ┌─────────────┐
   │  sensor     │ ──────────────────────► │  servidor   │
   │ (http_      │ ◄────────────────────── │  FastAPI    │
   │  client.py) │   HTTP/1.1 201 Created  │  porta 8000 │
   └─────────────┘                         └─────────────┘
         TCP — 3-way handshake antes do primeiro dado
```

### Transporte: TCP

HTTP/1.1 roda sobre **TCP**. Antes de qualquer dado, TCP abre uma conexão com o **3-way handshake**:

```
Cliente          Servidor
  |── SYN ──────►|     (1) pede conexão
  |◄── SYN-ACK ──|     (2) aceita
  |── ACK ──────►|     (3) confirma
  |                |
  |══ dados HTTP ═►|     só agora os dados fluem
```

O cliente usa `keep-alive` — o handshake acontece uma vez; as requisições seguintes reutilizam a mesma conexão TCP.

### Estrutura de uma requisição HTTP

Cada leitura enviada pelo sensor gera esta requisição:

```
POST /sensor HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json
Content-Length: 70
Accept: */*
Connection: keep-alive

{"id":"sensor-http","temperatura":25.3,"umidade":61.2,"ts":1719000000}
```

| Parte | Bytes | Função |
|---|---|---|
| Linha de status (`POST /sensor HTTP/1.1`) | 23 B | Método + recurso + versão |
| Headers (`Host`, `Content-Type`, etc.) | ~113 B | Metadados da requisição |
| Separador (`\r\n`) | 2 B | Delimita headers do corpo |
| Corpo JSON | ~70 B | **Dado útil** (temperatura, umidade, ts) |
| **Total** | **~208 B** | — |

Os headers sozinhos consomem **~136 B** — quase o dobro do dado útil.

### Resposta do servidor

```
HTTP/1.1 201 Created
Content-Type: application/json

{"status":"ok","recebido":{"id":"sensor-http","temperatura":25.3,...}}
```

**201 Created** confirma que a leitura foi recebida e registrada.

### Como o overhead é medido (`core/tamanhos.py`)

A função `tamanho_http()` recalcula o tamanho exato da requisição linha a linha:

```python
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
```

Esse valor é exibido no dashboard e atualizado a cada leitura.

### Endpoints do servidor (`http_server.py`)

| Método | Endpoint | Descrição | Status |
|---|---|---|---|
| `POST` | `/sensor` | Recebe leitura JSON do sensor | **201 Created** |
| `GET` | `/sensor/{id}` | Consulta última leitura de um sensor | 200 / 404 |
| `GET` | `/sensor` | Lista todos os sensores | 200 |
| `GET` | `/api/stats` | Overhead HTTP em tempo real | 200 |
| `GET` | `/health` | Saúde do servidor | 200 |
| `GET` | `/` | Dashboard em tempo real | 200 |

O dashboard (`GET /`) é servido via HTTP pelo próprio FastAPI. O browser faz polling a cada 1s via `GET /api/stats` para atualizar os dados sem recarregar a página.

---

## Instalação

Requer **Python 3.10+**.

```bash
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Como rodar

**Terminal 1 — servidor:**
```bash
python http_server.py
```

**Terminal 2 — sensor (cliente):**
```bash
python http_client.py --n 20 --intervalo 1
```

Dashboard abre em **http://127.0.0.1:8000/**

Parâmetros do cliente:
```bash
python http_client.py --n 10       # 10 envios
python http_client.py --intervalo 0.5  # envio a cada 0.5s
```

A documentação automática da API fica em **http://127.0.0.1:8000/docs** (Swagger UI gerado pelo FastAPI).
