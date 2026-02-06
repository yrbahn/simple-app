import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_sector_leaders():
    """
    주요 섹터별 대장주 리스트 (한국 증시 기준)
    """
    return {
        "반도체": "005930.KS",      # 삼성전자
        "이차전지": "373220.KS",    # LG에너지솔루션
        "자동차": "005380.KS",      # 현대차
        "바이오": "207940.KS",      # 삼성바이오로직스
        "인터넷/플랫폼": "035420.KS", # NAVER
        "금융": "105560.KS",        # KB금융
        "철강": "005490.KS",        # POSCO홀딩스
        "통신": "017670.KS",        # SK텔레콤
        "게임": "259960.KS",        # 크래프톤
        "엔터테인먼트": "352820.KS"  # 하이브
    }

def get_stock_report(ticker):
    """
    특정 티커의 일주일 변동성 리포트 생성
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # 데이터 다운로드 (한국 주식은 보통 종가 기준 단위가 크므로 정수로 표현)
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
    
    # 회사명 가져오기 (옵션)
    info = stock.info
    name = info.get('shortName', ticker)
    
    return {
        "Ticker": ticker,
        "Name": name,
        "Start Price": int(start_price),
        "End Price": int(end_price),
        "Change (%)": round(change_pct, 2),
        "Volatility (%)": round(volatility, 2)
    }

def main():
    print("=" * 75)
    print(f"한국 증시 주요 섹터 대장주 최근 7일 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 75)
    
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
        cols = ['Sector', 'Name', 'Ticker', 'Start Price', 'End Price', 'Change (%)', 'Volatility (%)']
        report_df = report_df[cols]
        
        # 한국어 출력을 위해 컬럼명 변경
        report_df.columns = ['섹터', '종목명', '티커', '시작가', '현재가', '변동률(%)', '변동성(%)']
        
        print(report_df.to_string(index=False))
    else:
        print("데이터를 가져오지 못했습니다.")
        
    print("=" * 75)

if __name__ == "__main__":
    main()
