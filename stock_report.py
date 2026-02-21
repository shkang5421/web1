import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from tabulate import tabulate

def get_naver_data(code):
    # 네이버 증권 데이터 및 종목명 크롤링
    url_info = f"https://finance.naver.com/item/main.naver?code={code}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url_info, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    title = soup.find("title").get_text()
    name = title.split(':')[0].strip()
    
    # RSI 정밀도를 위해 500일치 데이터 확보
    url_price = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count=500&requestType=0"
    res_price = requests.get(url_price)
    soup_price = BeautifulSoup(res_price.text, 'xml')
    items = soup_price.find_all("item")
    prices = [int(item['data'].split('|')[4]) for item in items]
    return name, prices

def send_discord_message(content):
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("Webhook URL이 설정되지 않았습니다.")
        return

    payload = {"content": content}
    requests.post(webhook_url, json=payload)

# 분석 실행
my_tickers = ["452360", "0117V0", "0080G0"]
results = []

for code in my_tickers:
    try:
        name, prices = get_naver_data(code)
        if len(prices) > 30:
            df = pd.DataFrame(prices, columns=['Close'])
            # 네이버 차트와 유사한 계산 방식 적용
            rsi = ta.rsi(df['Close'], length=14)
            val = round(float(rsi.iloc[-1]), 2)
            
            # RSI 수치에 따른 상태 이모지 추가
            status = "🔥" if val >= 70 else ("❄️" if val <= 30 else "✅")
            results.append([name, f"{prices[-1]:,}원", f"{val} {status}"])
    except Exception as e:
        print(f"Error analyzing {code}: {e}")
        continue

# 메시지 조립
header = ["종목명", "현재가", "RSI"]
table_str = tabulate(results, headers=header, tablefmt="simple")

# 디스코드 코드 블록을 사용하여 표 정렬 유지
final_msg = f"## 📊 네이버 증권 RSI 리포트 ({datetime.now().strftime('%Y-%m-%d')})\n"
final_msg += f"```\n{table_str}\n```"

send_discord_message(final_msg)
