import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from tabulate import tabulate

def calculate_rsi(prices, period=14):
    df = pd.DataFrame(prices, columns=['close'])
    delta = df['close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    rsi = 100 - (100 / (1+rs))
    return round(rsi.iloc[-1], 2)

def get_naver_data(code):
    url_info = f"https://finance.naver.com/item/main.naver?code={code}"
    res = requests.get(url_info, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.text, 'html.parser')
    title = soup.find("title").get_text()
    name = title.split(':')[0].strip()
    
    url_price = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count=500&requestType=0"
    res_price = requests.get(url_price)
    soup_price = BeautifulSoup(res_price.text, 'xml')
    items = soup_price.find_all("item")
    prices = [int(item['data'].split('|')[4]) for item in items]
    return name, prices

def send_discord(content):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if webhook_url:
        requests.post(webhook_url, json={"content": content})

my_tickers = ["452360", "0117V0", "0080G0"]
results = []

for code in my_tickers:
    try:
        name, prices = get_naver_data(code)
        if len(prices) > 20:
            rsi_val = calculate_rsi(prices)
            status = "🔥" if rsi_val >= 70 else ("❄️" if rsi_val <= 30 else "✅")
            results.append([name, f"{prices[-1]:,}원", f"{rsi_val} {status}"])
    except:
        continue

table_str = tabulate(results, headers=["종목명", "현재가", "RSI"], tablefmt="simple")
final_msg = f"## 📊 RSI 리포트 ({datetime.now().strftime('%Y-%m-%d')})\n```\n{table_str}\n```"
send_discord(final_msg)
