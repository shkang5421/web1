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
    current_price = prices[-1]
    prev_price = prices[-2]
    change_rate = round(((current_price - prev_price) / prev_price) * 100, 2)
    
    return name, prices, change_rate

# --- 통합 메시지 전송 함수 ---
def send_combined_report(all_embeds):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url: return

    # 오늘 날짜 헤더 메시지
    today_str = datetime.now().strftime('%Y년 %m월 %d일')
    header_content = f"## 🗓️ {today_str} 주식 시장 리포트"

    payload = {
        "content": header_content,
        "embeds": all_embeds
    }
    
    # 디스코드는 한 번에 최대 10개의 임베드를 보낼 수 있습니다.
    requests.post(webhook_url, json=payload)

# --- 종목 그룹 설정 ---
groups = {
    "🛡️ 방산 섹터": ["0080G0", "012450", "066910", "047810"],
    "🇺🇸 미국 지수(H)": ["449150", "452360", "441680"],
    "💻 반도체/AI": ["305540", "005930", "000660"],
    "⚡ 전력기기": ["0117V0", "267260", "010120"]
}

all_embeds = []

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
        # 임베드 데이터 생성
        avg_rsi = sum([r[2] for r in group_results]) / len(group_results)
        if avg_rsi >= 70: color = 0xff4757
        elif avg_rsi <= 35: color = 0x2e86de
        else: color = 0x2ed573

        fields = []
        for name, price, rsi_val, change_rate in group_results:
            change_str = f"🔺 +{change_rate}%" if change_rate > 0 else (f"🔻 {change_rate}%" if change_rate < 0 else "➖ 0.00%")
            indicator = "🔴 **[과열]**" if rsi_val >= 70 else ("🔵 **[침체]**" if rsi_val <= 35 else "⚪ **[보통]**")
            
            fields.append({
                "name": f"📍 {name}",
                "value": f"└ **변동: {change_str}**\n└ RSI: `{rsi_val}` {indicator}\n└ 가격: `{price}`",
                "inline": True
            })

        # 리스트에 임베드 추가
        all_embeds.append({
            "title": f"━━━━━━━━━━━━━━━━━━━━\n{group_name}",
            "color": color,
            "fields": fields
        })

# 모든 그룹 처리가 끝나면 한 번에 전송
if all_embeds:
    send_combined_report(all_embeds)
