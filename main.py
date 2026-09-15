import os
import requests
import pandas as pd
import yfinance as yf

# 從 GitHub Secrets 讀取 Telegram 設定
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 欲掃描的台股清單 (可自行增減標的，台股加上 .TW 或 .TWO)
STOCK_LIST = [
    "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW",
    "3231.TW", "2356.TW", "3037.TW", "2379.TW", "6669.TW",
    "3035.TW", "3661.TW", "2408.TW", "3008.TW", "2303.TW"
]

def send_telegram_msg(message):
    """發送訊息至 Telegram Bot"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("缺少 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID 設定！")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
        print("Telegram 發送成功！")
    except Exception as e:
        print(f"Telegram 發送失敗: {e}")

def check_vcp(ticker):
    """檢查單一股票是否符合 VCP 型態基本條件"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        
        if len(df) < 200:
            return None

        # 計算移動平均線
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA50'] = df['Close'].rolling(window=50).mean()
        df['MA200'] = df['Close'].rolling(window=200).mean()

        latest = df.iloc[-1]
        close = latest['Close']
        ma20 = latest['MA20']
        ma50 = latest['MA50']
        ma200 = latest['MA200']

        # 1. 趨勢條件：股價高於 50MA 與 200MA，且 50MA > 200MA
        if not (close > ma50 and close > ma200 and ma50 > ma200):
            return None

        # 2. 距離 52 週高點 25% 以內 (處於高檔整理)
        high_52w = df['High'].tail(252).max()
        if close < high_52w * 0.75:
            return None

        # 3. 近期 20 日波動度收縮 (計算高低價差比例)
        recent_20 = df.tail(20)
        volatility_20 = (recent_20['High'].max() - recent_20['Low'].min()) / recent_20['Low'].min()

        # 近 10 日波動度要小於近 20 日波動度 (波動持續收縮)
        recent_10 = df.tail(10)
        volatility_10 = (recent_10['High'].max() - recent_10['Low'].min()) / recent_10['Low'].min()

        if volatility_10 < volatility_20 and volatility_10 < 0.12:  # 10日波幅在 12% 以內
            return {
                "ticker": ticker.replace(".TW", "").replace(".TWO", ""),
                "close": round(close, 2),
                "volatility": round(volatility_10 * 100, 1),
                "high_52w": round(high_52w, 2)
            }
    except Exception as e:
        print(f"掃描 {ticker} 時發生錯誤: {e}")
    
    return None

if __name__ == "__main__":
    print("開始執行台股 VCP 掃描...")
    matched_stocks = []

    for ticker in STOCK_LIST:
        result = check_vcp(ticker)
        if result:
            matched_stocks.append(
                f"📈 *{result['ticker']}* - 現價: `${result['close']}` | 近10日波幅: `{result['volatility']}%`"
            )

    if matched_stocks:
        msg = "🚀 **今日台股 VCP 篩選結果**\n\n" + "\n".join(matched_stocks)
    else:
        msg = "📊 **台股 VCP 每日掃描完成**\n今日追蹤清單中未發現符合 VCP 收縮型態之個股。"

    send_telegram_msg(msg)
