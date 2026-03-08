import requests
from bs4 import BeautifulSoup
import json
import re
import asyncio
from telegram import Bot
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
import yfinance as yf
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# =======================
# Configurações
# =======================
TOKEN = "7549385934:AAFH5fx6j7qdx0H1v6VHpz0tjG8NAKu9zRw"
CHAT_ID = -1002336238340
BASE_URL = "https://investidor10.com.br/fiis/"
FIIS = ["gare11", "hglg11", "visc11", "xpml11", "knca11", "mxrf11", "vgia11"]
ACOES = ["BBAS3.SA", "BBSE3.SA", "ISAE4.SA", "KLBN4.SA", "SAPR4.SA"]

# =======================
# Funções de extração
# =======================

def extrair_json_ld(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    scripts_ld_json = soup.find_all("script", type="application/ld+json")

    for script in scripts_ld_json:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get("@type") == "FAQPage":
                return data
        except Exception:
            continue
    return None

def extrair_cotacao_ppvp(url):
    data = extrair_json_ld(url)
    if not data:
        return "N/A", "N/A"

    cotacao = "N/A"
    ppvp = "N/A"

    for item in data.get("mainEntity", []):
        pergunta = item.get("name", "").lower()
        resposta = item.get("acceptedAnswer", {}).get("text", "")

        if "quanto custa uma cota" in pergunta:
            m = re.search(r"R\$ ([\d,\.]+)", resposta)
            if m:
                cotacao = m.group(1).replace(",", ".")
        elif "p/vp" in pergunta or "p/vp" in resposta.lower():
            m = re.search(r"P\/VP de ([\d,\.%]+)", resposta)
            if m:
                ppvp = m.group(1).replace(",", ".")
    return cotacao, ppvp

# =======================
# Envio de mensagens
# =======================

async def enviar_fii(bot, fii):
    url = BASE_URL + fii + "/"
    cotacao, pvp = extrair_cotacao_ppvp(url)
    mensagem = (
        f"🏢 {fii.upper()}\n"
        f"💵 Cotação: R$ {cotacao}\n"
        f"📊 P/VP: {pvp}"
    )
    mensagem_escapada = escape_markdown(mensagem, version=2)
    await bot.send_message(chat_id=CHAT_ID, text=mensagem_escapada, parse_mode=ParseMode.MARKDOWN_V2)

async def enviar_acao(bot, ticker_str):
    ticker = yf.Ticker(ticker_str)
    info = ticker.info

    cotacao = info.get("currentPrice")
    pl = info.get("trailingPE")
    pvp = info.get("priceToBook")

    nome_acao = ticker_str.replace(".SA", "").upper()

    cotacao_str = f"R$ {cotacao:.2f}" if cotacao else "N/A"
    pl_str = f"{pl:.2f}" if pl else "N/A"
    pvp_str = f"{pvp:.2f}" if pvp else "N/A"

    mensagem = (
        f"📈 {nome_acao}\n"
        f"💵 Cotação: {cotacao_str}\n"
        f"📊 P/L: {pl_str}\n"
        f"📉 P/VP: {pvp_str}"
    )
    mensagem_escapada = escape_markdown(mensagem, version=2)
    await bot.send_message(chat_id=CHAT_ID, text=mensagem_escapada, parse_mode=ParseMode.MARKDOWN_V2)

async def enviar_relatorio():
    bot = Bot(token=TOKEN)
    for acao in ACOES:
        await enviar_acao(bot, acao)
        await asyncio.sleep(3)

    for fii in FIIS:
        await enviar_fii(bot, fii)
        await asyncio.sleep(3)

# =======================
# Agendamento
# =======================

def agendar(scheduler):
    # Agenda principal (segunda e sexta às 10h30)
    scheduler.add_job(
        enviar_relatorio,
        trigger=CronTrigger(day_of_week='mon,fri', hour=10, minute=30),
        name="Relatório seg/sex 10h30"
    )

  

    scheduler.start()
    print("✅ Agendamentos iniciados.")

# =======================
# Loop principal
# =======================

async def main():
    scheduler = AsyncIOScheduler()
    agendar(scheduler)
    try:
        await asyncio.Event().wait()  # Mantém o script rodando
    except (KeyboardInterrupt, SystemExit):
        print("⛔ Encerrando...")
        scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
