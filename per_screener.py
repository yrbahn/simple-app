from pykrx import stock
import pandas as pd
from datetime import datetime
import os

def get_low_per_stocks(limit=30):
    """
    최근 확정 실적(보통 직전 연도) 기준 PER이 낮은 종목 TOP 30 추출
    """
    try:
        # 삼성전자(005930)의 최근 10일 OHLCV를 가져와서 가장 최근 날짜 확인
        ohlcv = stock.get_market_ohlcv((datetime.now() - timedelta(days=10)).strftime("%Y%m%d"), 
                                     datetime.now().strftime("%Y%m%d"), 
                                     "005930")
        if ohlcv.empty:
            print("최근 영업일 정보를 가져올 수 없습니다.")
            return None
            
        latest_date = ohlcv.index[-1].strftime("%Y%m%d")
        print(f"조회 기준일: {latest_date}")
        
        df_kospi = stock.get_market_fundamental(latest_date, market="KOSPI")
        df_kosdaq = stock.get_market_fundamental(latest_date, market="KOSDAQ")
        df = pd.concat([df_kospi, df_kosdaq])
    except Exception as e:
        print(f"데이터 조회 실패: {e}")
        return None

    # PER이 0인 것은 제외 (영업이익 적자거나 데이터 없는 경우)
    # 또한 PER이 지나치게 낮은(예: 0.5 미만) 데이터 오류 가능성 종목 필터링
    df = df[df['PER'] > 0.5]
    
    # PER 기준 오름차순 정렬
    df_sorted = df.sort_values(by='PER', ascending=True)
    
    # 종목명 추가
    top_df = df_sorted.head(limit).copy()
    top_df['종목명'] = [stock.get_market_ticker_name(ticker) for ticker in top_df.index]
    
    # 컬럼 정리
    top_df = top_df[['종목명', 'PER', 'PBR', '배당수익률', 'EPS', 'BPS']]
    top_df.index.name = '티커'
    
    return top_df

def main():
    print("저PER 종목 스크리닝 중...")
    top_30 = get_low_per_stocks(30)
    
    if top_30 is None or top_30.empty:
        print("데이터를 불러오는 데 실패했습니다.")
        return

    today_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"reports/per_screener_{today_str}.md"
    os.makedirs("reports", exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 저PER 종목 스크리닝 리포트 ({today_str})\n\n")
        f.write("## 한국 증시(KOSPI/KOSDAQ) PER 하위 30개 종목\n\n")
        f.write("- 기준: 최근 확정 영업이익 기반 PER\n")
        f.write("- 필터: PER 0.5 미만 및 적자 종목 제외\n\n")
        f.write(top_30.reset_index().to_markdown(index=False))
        f.write("\n\n*이 리포트는 자동 생성되었습니다.*")

    print(f"스크리너 리포트 생성 완료: {filename}")

if __name__ == "__main__":
    main()
