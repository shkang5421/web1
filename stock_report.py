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
    
    # [가격 데이터 추출]
    prices = [int(item['data'].split('|')[4]) for item in items]
    
    # [전일 대비 등락률 계산]
    current_price = prices[-1]
    prev_price = prices[-2]
    change_rate = round(((current_price - prev_price) / prev_price) * 100, 2)
    
    return name, prices, change_rate

def send_discord_embed_pro(group_name, results):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url: return

    avg_rsi = sum([r[2] for r in results]) / len(results)
    if avg_rsi >= 70:
        color = 0xff4757 # Red
        group_desc = "🚨 시장 과열 구간입니다. 익절을 고려해보세요!"
    elif avg_rsi <= 35:
        color = 0x2e86de # Blue
        group_desc = "💎 과매도 구간입니다. 반등 여부를 체크하세요!"
    else:
        color = 0x2ed573 # Green
        group_desc = "✅ 정상 범위 내에서 움직이고 있습니다."

    fields = []
    for name, price, rsi_val, change_rate in results:
        # 등락률 이모지 설정
        if change_rate > 0:
            change_str = f"🔺 +{change_rate}%"
        elif change_rate < 0:
            change_str = f"🔻 {change_rate}%"
        else:
            change_str = f"➖ 0.00%"

        # RSI 상태 태그
        if rsi_val >= 70: indicator = "🔴 **[과매수]**"
        elif rsi_val <= 35: indicator = "🔵 **[과매도]**"
        else: indicator = "⚪ **[보통]**"

        fields.append({
            "name": f"📍 {name}",
            "value": f"└ **변동: {change_str}**\n└ RSI: `{rsi_val}` {indicator}\n└ 가격: `{price}`",
            "inline": True
        })

    payload = {
        "embeds": [{
            "title": f"━━━━━━━━━━━━━━━━━━━━\n{group_name}",
            "description": f"{group_desc}\n━━━━━━━━━━━━━━━━━━━━",
            "color": color,
            "fields": fields,
            "footer": {"text": f"📅 분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
        }]
    }
    requests.post(webhook_url, json=payload)

# --- 종목 그룹 설정 (원하는대로 수정하세요) ---
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
            name, prices, change_rate = get_naver_data(code)
            if len(prices) > 20:
                rsi_val = calculate_rsi(prices)
                group_results.append([name, f"{prices[-1]:,}원", rsi_val, change_rate])
        except: continue
    
    if group_results:
        send_discord_embed_pro(group_name, group_results)
