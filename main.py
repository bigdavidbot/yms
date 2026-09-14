import os
import requests
import pandas as pd
import yfinance as yf

# 從 GitHub Secrets 讀取 Telegram 設定
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_msg(message):
    """發送訊息至 Telegram Bot"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("未設定 Telegram Token 或 Chat ID，跳過推播。")
        print(message)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Telegram 推播失敗: {e}")

def check_vcp(ticker_symbol):
    """檢查單一股票是否符合 VCP 趨勢與波幅收縮條件"""
    try:
        df = yf.download(ticker_symbol, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 200:
            return None

        # 處理多層索引欄位 (yfinance 升級後特有結構)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        ma50 = close.rolling(50).mean()
        ma200 = close.rolling(200).mean()

        curr_price = close.iloc[-1]
        curr_ma50 = ma50.iloc[-1]
        curr_ma200 = ma200.iloc[-1]

        # 1. 趨勢過濾：股價高於 50MA 與 200MA，且 50MA 高於 200MA
        if not (curr_price > curr_ma50 > curr_ma200):
            return None

        # 2. 波動收縮 (VCP) 簡化判定：近期 20 日波幅小於前 60 日波幅
        high20, low20 = df['High'].iloc[-20:].max(), df['Low'].iloc[-20:].min()
        high60, low60 = df['High'].iloc[-60:].max(), df['Low'].iloc[-60:].min()

        volatility_20 = (high20 - low20) / low20
        volatility_60 = (high60 - low60) / low60

        if volatility_20 < (volatility_60 * 0.6):  # 收縮幅度顯著降低
            return {
                "ticker": ticker_symbol.replace(".TW", "").replace(".TWO", ""),
                "price": round(curr_price, 2),
                "volatility_20": f"{round(volatility_20 * 100, 1)}%"
            }
    except Exception as e:
        pass
    return None

def main():
    # 觀察標的清單（台股上市櫃熱門股範例，可依需求自行擴充）
    watch_list = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2308.TW", "3037.TW"]
    
    selected_stocks = []
    for ticker in watch_list:
        res = check_vcp(ticker)
        if res:
            selected_stocks.append(res)

    # 彙整推播報告
    report = "📈 *每日台股 VCP 自動掃描報告*\n\n"
    if selected_stocks:
        report += "符合 200MA 趨勢 + 波動收縮條件之標的：\n"
        for s in selected_stocks:
            report += f"• *{s['ticker']}* | 收盤價: ${s['price']} | 近20日波幅: {s['volatility_20']}\n"
    else:
        report += "今日無符合 VCP 狹幅收縮條件之觀察標的。"

    send_telegram_msg(report)

if __name__ == "__main__":
    main()
