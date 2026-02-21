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
        # 메시지가 너무 길면 디스코드에서 잘릴 수 있으므로 나눠서 보냅니다.
        if len(content) > 2000:
            parts = [content[i:i+1900] for i in range(0, len(content), 1900)]
            for part in parts:
                requests.post(webhook_url, json={"content": part})
        else:
            requests.post(webhook_url, json={"content": content})

# --- 종목 그룹 설정 구간 ---
# 원하시는 그룹명과 종목 코드를 아래 형식으로 추가하세요.
groups = {
    "🛡️ 방산 그룹": ["0080G0", "012450", "066910", "079550", "272210"],  
    "🔋 배당/지수 그룹": ["452360", "449190", "069500", "229200"],
    "💻 반도체 그룹": ["396500", "005930", "000660", "042700"],
    "⚡ 변압기 그룹": ["0117V0", "267260", "010120", "298040"],
    "🚢 조선 그룹": ["0115D0", "042660", "329180", "010140"]
}

total_message = f"## 📊 그룹별 RSI 리포트 ({datetime.now().strftime('%Y-%m-%d')})\n"

for group_name, tickers in groups.items():
    results = []
    for code in tickers:
        try:
            name, prices = get_naver_data(code)
            if len(prices) > 20:
                rsi_val = calculate_rsi(prices)
                status = "🔥" if rsi_val >= 70 else ("❄️" if rsi_val <= 30 else "✅")
                results.append([name, f"{prices[-1]:,}원", f"{rsi_val} {status}"])
        except:
            continue
    
    if results:
        table_str = tabulate(results, headers=["종목명", "현재가", "RSI"], tablefmt="simple")
        total_message += f"\n### {group_name}\n```\n{table_str}\n```\n"

send_discord(total_message)
