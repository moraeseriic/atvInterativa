"""
Sobe servidor + cliente, tira prints do dashboard, salva em docs/screenshots/.
Uso: python scripts/screenshot.py
"""
import asyncio
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "docs", "screenshots")
os.makedirs(OUT, exist_ok=True)


async def main():
    from playwright.async_api import async_playwright

    print("[1] iniciando servidor...")
    srv = subprocess.Popen(
        [sys.executable, "http_server.py"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(2)

    print("[2] enviando dados (20 mensagens, 3 sensores)...")
    cli = subprocess.Popen(
        [sys.executable, "http_client.py", "--n", "20", "--sensores", "3", "--intervalo", "0.15"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(4)  # espera dados chegarem

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page.wait_for_timeout(1500)

        # 1 — visao geral (topo)
        await page.screenshot(path=os.path.join(OUT, "01_visao_geral.png"), full_page=False)
        print("  ok 01_visao_geral.png")

        # 2 — pagina completa
        await page.screenshot(path=os.path.join(OUT, "02_pagina_completa.png"), full_page=True)
        print("  ok 02_pagina_completa.png")

        # 3 — anatomia da mensagem — aba requisicao
        await page.evaluate("document.querySelector('.bars-grid')?.scrollIntoView({block:'center'})")
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(OUT, "03_anatomia_requisicao.png"), full_page=False)
        print("  ok 03_anatomia_requisicao.png")

        # 4 — anatomia — aba resposta
        await page.click("#tab-resp")
        await page.wait_for_timeout(300)
        await page.screenshot(path=os.path.join(OUT, "04_anatomia_resposta.png"), full_page=False)
        print("  ok 04_anatomia_resposta.png")

        # 5 — simulador de overhead (payload padrao 68 B)
        sim = await page.query_selector("#sim-slider")
        await sim.scroll_into_view_if_needed()
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(OUT, "05_simulador_overhead.png"), full_page=False)
        print("  ok 05_simulador_overhead.png")

        # 6 — simulador com payload grande (1500 B, 50 msgs/sessao)
        await page.fill("#sim-sessao", "50")
        await page.evaluate("document.getElementById('sim-slider').value = 1500; updateSim()")
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(OUT, "06_simulador_payload_grande.png"), full_page=False)
        print("  ok 06_simulador_payload_grande.png")

        # 7 — grafico RTT
        await page.click("#m-rtt")
        chart = await page.query_selector("#chart-svg")
        await chart.scroll_into_view_if_needed()
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(OUT, "07_grafico_rtt.png"), full_page=False)
        print("  ok 07_grafico_rtt.png")

        # 8 — cards dos sensores ativos
        await page.evaluate("document.getElementById('sensor-cards')?.scrollIntoView({block:'center'})")
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(OUT, "08_cards_sensores.png"), full_page=False)
        print("  ok 08_cards_sensores.png")

        await browser.close()

    cli.wait()
    srv.terminate()
    print("\nscreenshots salvas em docs/screenshots/")


if __name__ == "__main__":
    asyncio.run(main())
