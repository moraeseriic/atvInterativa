# HTTP IoT — Atividade Interativa
### Redes de Computadores

Aplicação que **simula sensores IoT** enviando leituras de temperatura e umidade via **HTTP/1.1** para um servidor FastAPI. Foco na análise do protocolo: estrutura das mensagens, overhead de headers, latência (RTT), throughput e modelo cliente-servidor.

---

## Funcionalidades

| Feature | Descrição |
|---|---|
| 📡 **Sensor simulado** | Gera temperatura e umidade com variação realista |
| 🌐 **Servidor HTTP** | FastAPI + uvicorn, porta 8000 |
| 📊 **Dashboard ao vivo** | Atualiza a cada 1s via polling HTTP |
| ⏱️ **RTT medido** | Cliente mede latência real de cada requisição |
| ⚡ **Throughput** | Servidor calcula msgs/s e kB/s em tempo real |
| 🔢 **Múltiplos sensores** | N sensores simultâneos com `--sensores N` |
| 🔁 **Modo contínuo** | Loop infinito com `--continuo` |
| 📐 **Simulador de overhead** | Slider interativo no dashboard — veja como o overhead % muda com o tamanho do payload |
| 🔎 **Overhead bidirecional** | Mede headers da requisição **e** da resposta separadamente |

---

## Estrutura

```
atvInterativa/
├── core/
│   ├── sensor.py       # Gerador de leituras (temperatura + umidade)
│   ├── estado.py       # Estado compartilhado entre processos (JSON atômico)
│   └── tamanhos.py     # Cálculo de overhead HTTP (req + resp + roundtrip)
├── static/
│   └── dashboard.html  # Dashboard em tempo real
├── http_server.py      # Servidor FastAPI — porta 8000 TCP
├── http_client.py      # Cliente httpx assíncrono — simula sensor(es)
└── requirements.txt    # fastapi · uvicorn · httpx
```

---

## O protocolo HTTP nesta atividade

### Modelo cliente-servidor

O sensor atua como **cliente** e inicia sempre a comunicação. O servidor processa e devolve uma resposta — modelo **requisição-resposta** (*stateless*): cada troca é independente.

```
   ┌──────────────┐   POST /sensor (JSON)    ┌──────────────┐
   │  sensor IoT  │ ───────────────────────► │  servidor    │
   │ http_client  │ ◄─────────────────────── │  FastAPI     │
   │   .py        │   HTTP/1.1 201 Created   │  porta 8000  │
   └──────────────┘                          └──────────────┘
              TCP — 3-way handshake antes do primeiro dado
```

Com múltiplos sensores, N conexões paralelas acontecem simultaneamente:

```
   sensor-http-1 ──► POST /sensor ──► servidor
   sensor-http-2 ──► POST /sensor ──► servidor   (paralelo)
   sensor-http-3 ──► POST /sensor ──► servidor
```

### Transporte: TCP

HTTP/1.1 roda sobre **TCP**. Antes de qualquer dado, TCP abre a conexão com o **3-way handshake**:

```
Cliente           Servidor
  │── SYN ───────►│     (1) pede conexão
  │◄── SYN-ACK ───│     (2) aceita
  │── ACK ───────►│     (3) confirma
  │                │
  │══ dados HTTP ══►│   só agora os dados fluem
```

O cliente usa `Connection: keep-alive` — handshake acontece **uma vez** por sessão; requisições seguintes reutilizam a conexão TCP.

### Estrutura de uma requisição HTTP

Cada leitura do sensor gera esta mensagem:

```
POST /sensor HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json
Content-Length: 70
Accept: */*
Connection: keep-alive

{"id":"sensor-http","temperatura":25.3,"umidade":61.2,"ts":1719000000}
```

| Parte | Tamanho | Função |
|---|---|---|
| Linha de requisição | 23 B | Método + recurso + versão HTTP |
| Headers | ~113 B | Metadados (tipo, tamanho, host…) |
| Separador `\r\n` | 2 B | Delimita headers do corpo |
| Corpo JSON | ~70 B | **Dado útil** |
| **Total** | **~208 B** | — |

> Os headers sozinhos consomem ~136 B — quase o dobro do dado útil.

### Resposta do servidor

```
HTTP/1.1 201 Created
date: Sun, 06 Jul 2025 00:00:00 GMT
server: uvicorn
content-length: 97
content-type: application/json

{"status":"ok","recebido":{"id":"sensor-http","temperatura":25.3,...}}
```

| Parte | Tamanho |
|---|---|
| Linha de status | 22 B |
| Headers de resposta | ~108 B |
| Corpo JSON | ~97 B |
| **Total** | **~227 B** |

### Overhead bidirecional (roundtrip)

Para avaliar o custo **real** do protocolo, a aplicação mede o roundtrip completo:

```
Roundtrip = requisição + resposta
          = ~208 B     + ~227 B
          = ~435 B

Dado útil = ~70 B (o JSON do sensor)
Overhead  = ~365 B (headers dos dois lados + wrapping da resposta)
          ≈ 84% do roundtrip é overhead de protocolo
```

O **simulador de overhead** no dashboard permite variar o tamanho do payload de 10 B até 2 kB e ver essa relação mudar em tempo real — payloads maiores tornam o protocolo proporcionalmente mais eficiente.

### RTT — Round-Trip Time

O cliente mede o tempo entre o envio e o recebimento da resposta para cada POST:

```python
t_start = time.monotonic()
r = await client.post(URL, content=corpo, ...)
rtt_ms = (time.monotonic() - t_start) * 1000   # em milissegundos
```

O RTT é reportado ao servidor via `POST /api/metricas` e exibido no dashboard com:
- Valor atual
- Média, mínimo e máximo das últimas 100 amostras
- Histórico em gráfico

### Como o overhead é calculado (`core/tamanhos.py`)

```python
def tamanho_http(payload: bytes) -> int:
    linha   = "POST /sensor HTTP/1.1\r\n"
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
    body    = b'{"status":"ok","recebido":' + payload_req + b'}'
    linha   = "HTTP/1.1 201 Created\r\n"
    headers = (
        "date: Tue, 01 Jul 2025 00:00:00 GMT\r\n"
        "server: uvicorn\r\n"
        f"content-length: {len(body)}\r\n"
        "content-type: application/json\r\n"
        "\r\n"
    )
    return len(linha.encode()) + len(headers.encode()) + len(body)
```

Os headers são reconstruídos byte a byte — o overhead não é estimado, é **calculado exatamente**.

### Endpoints do servidor

| Método | Endpoint | Descrição | Status |
|---|---|---|---|
| `POST` | `/sensor` | Recebe leitura JSON do sensor | **201 Created** |
| `POST` | `/api/metricas` | Recebe RTT medido pelo cliente | 200 OK |
| `GET` | `/sensor/{id}` | Última leitura de um sensor específico | 200 / 404 |
| `GET` | `/sensor` | Lista todos os sensores ativos | 200 OK |
| `GET` | `/api/stats` | Overhead + RTT + throughput em tempo real | 200 OK |
| `GET` | `/health` | Saúde do servidor | 200 OK |
| `GET` | `/` | Dashboard | 200 OK |

O dashboard faz polling a cada 1s em `GET /api/stats` — sem WebSocket, sem SSE. HTTP puro.

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
# envio simples — 10 mensagens com intervalo de 1s
python http_client.py

# loop infinito até Ctrl+C
python http_client.py --continuo

# 3 sensores em paralelo, loop contínuo
python http_client.py --sensores 3 --continuo

# burst rápido — 50 msgs a cada 0.2s
python http_client.py --n 50 --intervalo 0.2
```

Dashboard: **http://127.0.0.1:8000/**  
Swagger UI: **http://127.0.0.1:8000/docs**

### Parâmetros do cliente

| Flag | Padrão | Descrição |
|---|---|---|
| `--n` | `10` | Número de envios por sensor |
| `--intervalo` | `1.0` | Segundos entre envios |
| `--continuo` | `false` | Loop infinito até Ctrl+C |
| `--sensores` | `1` | Número de sensores simultâneos |

---

## Dashboard

O dashboard exibe em tempo real:

- **6 métricas** — requisições totais, RTT, roundtrip (B), throughput, temperatura, umidade
- **Anatomia da mensagem** — barra visual de payload vs overhead, para requisição e resposta separadamente, com preview dos headers reais
- **Simulador de overhead** — slider interativo de 10 B a 2 kB com curva SVG mostrando a relação assintótica entre tamanho e eficiência
- **Histórico em gráfico** — bytes acumulados, temperatura/umidade ou RTT nos últimos 90s
- **Cards de sensores** — um card por sensor ativo; com múltiplos sensores exibe grid responsivo
