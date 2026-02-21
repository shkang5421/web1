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

def send_discord_embed_pro(group_name, results):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url: return

    # 그룹 상태 요약 및 색상 결정
    avg_rsi = sum([r[2] for r in results]) / len(results)
    if avg_rsi >= 70:
        color = 0xff4757  # 강한 빨강 (과열)
        group_desc = "🚨 현재 시장이 매우 뜨겁습니다! (과매수 주의)"
    elif avg_rsi <= 35:
        color = 0x2e86de  # 시원한 파랑 (기회)
        group_desc = "💎 바닥권 신호가 포착되었습니다. (분할매수 검토)"
    else:
        color = 0x2ed573  # 안정적인 초록
        group_desc = "✅ 시장이 안정적인 흐름을 보이고 있습니다."

    fields = []
    for name, price, rsi_val in results:
        # RSI 수치에 따른 이모지 및 한 줄 평
        if rsi_val >= 70:
            indicator = "🔴 **[과매수]**"
        elif rsi_val <= 35:
            indicator = "🔵 **[과매도]**"
        else:
            indicator = "⚪ **[보통]**"

        # 필드 구성 (가로 정렬 최적화)
        fields.append({
            "name": f"📍 {name}",
            "value": f"└ **RSI: {rsi_val}** {indicator}\n└ 현재가: `{price}`",
            "inline": True
        })

    payload = {
        "embeds": [{
            "title": f"━━━━━━━━━━━━━━━━━━━━\n{group_name}",
            "description": f"{group_desc}\n━━━━━━━━━━━━━━━━━━━━",
            "color": color,
            "fields": fields,
            "footer": {
                "text": f"📅 분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "icon_url": "https://i.imgur.com/vHqY7eM.png" # 시계 아이콘 예시
            }
        }]
    }
    requests.post(webhook_url, json=payload)

# --- 종목 그룹 설정 ---
groups = {
    "🔋 배당/지수 그룹": ["452360", "449190", "069500", "229200"],
    "🛡️ 방산 그룹": ["0080G0", "012450", "064350", "079550", "272210"],  
    "💻 반도체 그룹": ["396500", "005930", "000660", "042700"],
    "⚡ 변압기 그룹": ["0117V0", "267260", "010120", "298040"],
    "🚢 조선 그룹": ["0115D0", "042660", "329180", "010140"]
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
        send_discord_embed_pro(group_name, group_results)
