import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

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
    name = soup.find("title").get_text().split(':')[0].strip()
    
    url_price = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count=500&requestType=0"
    res_price = requests.get(url_price)
    soup_price = BeautifulSoup(res_price.text, 'xml')
    items = soup_price.find_all("item")
    prices = [int(item['data'].split('|')[4]) for item in items]
    return name, prices

def send_discord_embed(group_name, results):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url: return

    # 그룹 내 평균 RSI를 계산해 임베드 색상 결정
    avg_rsi = sum([r[2] for r in results]) / len(results)
    color = 0x2ecc71  # 기본 초록색
    if avg_rsi >= 70: color = 0xe74c3c  # 빨간색 (과매수)
    elif avg_rsi <= 35: color = 0x3498db # 파란색 (과매도)

    fields = []
    for name, price, rsi_val in results:
        status = "🔥" if rsi_val >= 70 else ("❄️" if rsi_val <= 35 else "✅")
        fields.append({
            "name": name,
            "value": f"**가격:** `{price}`\n**RSI:** `{rsi_val}` {status}",
            "inline": True
        })

    payload = {
        "embeds": [{
            "title": f"{group_name}",
            "color": color,
            "fields": fields,
            "footer": {"text": f"조회 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
        }]
    }
    requests.post(webhook_url, json=payload)

# --- 종목 그룹 설정 ---
groups = {
    "🛡️ 방산 그룹": ["0080G0", "012450", "064350", "047810", "011070"],
    "🔋 배당/지수 그룹": ["452360", "449150", "069500", "232080"],
    "💻 반도체 그룹": ["305540", "005930", "000660", "042700"],
    "⚡ 변압기 그룹": ["0117V0", "267260", "010120", "000880"]
}

for group_name, tickers in groups.items():
    group_results = []
    for code in tickers:
        try:
            name, prices = get_naver_data(code)
            if len(prices) > 20:
                rsi_val = calculate_rsi(prices)
                group_results.append([name, f"{prices[-1]:,}원", rsi_val])
        except: continue
    
    if group_results:
        send_discord_embed(group_name, group_results)
