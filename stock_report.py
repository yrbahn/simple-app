import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_sector_leaders():
    """
    주요 섹터별 대장주 리스트 (미국 증시 기준)
    """
    return {
        "Technology": "AAPL",
        "Communication Services": "GOOGL",
        "Consumer Cyclical": "AMZN",
        "Financial": "JPM",
        "Healthcare": "UNH",
        "Energy": "XOM",
        "Consumer Defensive": "PG",
        "Utilities": "NEE",
        "Real Estate": "PLD",
        "Industrials": "CAT",
        "Basic Materials": "LIN"
    }

def get_stock_report(ticker):
    """
    특정 티커의 일주일 변동성 리포트 생성
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # 데이터 다운로드
    stock = yf.Ticker(ticker)
    df = stock.history(start=start_date, end=end_date)
    
    if df.empty:
        return None
        
    start_price = df['Close'].iloc[0]
    end_price = df['Close'].iloc[-1]
    change_pct = ((end_price - start_price) / start_price) * 100
    
    # 최고가/최저가
    high_price = df['High'].max()
    low_price = df['Low'].min()
    volatility = ((high_price - low_price) / low_price) * 100
    
    return {
        "Ticker": ticker,
        "Start Price": round(start_price, 2),
        "End Price": round(end_price, 2),
        "Change (%)": round(change_pct, 2),
        "Volatility (%)": round(volatility, 2)
    }

def main():
    print("=" * 60)
    print(f"주요 섹터 대장주 최근 7일 리포트 ({datetime.now().strftime('%Y-%m-%d')})")
    print("=" * 60)
    
    leaders = get_sector_leaders()
    reports = []
    
    for sector, ticker in leaders.items():
        try:
            report = get_stock_report(ticker)
            if report:
                report['Sector'] = sector
                reports.append(report)
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            
    if reports:
        report_df = pd.DataFrame(reports)
        # 컬럼 순서 조정
        cols = ['Sector', 'Ticker', 'Start Price', 'End Price', 'Change (%)', 'Volatility (%)']
        report_df = report_df[cols]
        
        print(report_df.to_string(index=False))
    else:
        print("데이터를 가져오지 못했습니다.")
        
    print("=" * 60)

if __name__ == "__main__":
    main()
