import os
import requests
import pandas as pd
import yfinance as yf
import time
from datetime import datetime

TELEGRAM_TOKEN = os.getenv('TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

ACTIFS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "EURJPY=X"]
INTERVALLE = "1m"
PERIODE = "1d"

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
        print(f"Envoyé: {message[:30]}")
    except Exception as e:
        print(f"Erreur Telegram : {e}")

def calculer_indicateurs_avances(df):
    df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA_21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    exp1 = df["Close"].ewm(span=12, adjust=False).mean()
    exp2 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["SIGNAL_MACD"] = df["MACD"].ewm(span=9, adjust=False).mean()
    return df

def analyser_actif(symbole):
    try:
        df = yf.download(symbole, interval=INTERVALLE, period=PERIODE, progress=False)
        if df.empty or len(df) < 60:
            return
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df = calculer_indicateurs_avances(df)
        dernier = df.iloc[-2]
        rsi = float(dernier["RSI"])
        ema_9 = float(dernier["EMA_9"])
        ema_21 = float(dernier["EMA_21"])
        ema_50 = float(dernier["EMA_50"])
        macd = float(dernier["MACD"])
        sig_macd = float(dernier["SIGNAL_MACD"])
        prix = float(dernier["Close"])

        # MODE TRAINING - FILTRE A 70/100
        if rsi < 40 and ema_9 > ema_21 and prix > ema_50 and macd > sig_macd:
            envoyer_telegram(f"🟢 *CALL TRAINING 75/100*\nPaire: {symbole}\nRSI: {rsi:.1f} - EMA 9>21\nPrix: {prix}\nExpiration: 5 min")
        elif rsi > 60 and ema_9 < ema_21 and prix < ema_50 and macd < sig_macd:
            envoyer_telegram(f"🔴 *PUT TRAINING 75/100*\nPaire: {symbole}\nRSI: {rsi:.1f} - EMA 9<21\nPrix: {prix}\nExpiration: 5 min")
        else:
            print(f"Pas de signal {symbole} (RSI: {rsi:.1f})")
    except Exception as e:
        print(f"Erreur {symbole}: {e}")

if __name__ == "__main__":
    print("Bot demarre - Mode training 70/100")
    while True:
        for actif in ACTIFS:
            analyser_actif(actif)
        print("Scan fini, pause 90s")
        time.sleep(90)
