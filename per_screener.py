import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta
import os
import requests
from bs4 import BeautifulSoup

def get_low_per_stocks_crawling(limit=30):
    """
    Naver Finance의 '배당' 랭킹 등을 활용하거나 직접 종목 리스트를 순회하며 
    Fundamental 지표가 유효한 종목 중 PER이 낮은 순으로 추출합니다.
    (pykrx의 bulk API가 현재 환경에서 불안정하여 개별 조회를 병행하는 안전한 방식을 사용)
    """
    try:
        # 최근 영업일 구하기
        ohlcv = stock.get_market_ohlcv((datetime.now() - timedelta(days=10)).strftime("%Y%m%d"), 
                                     datetime.now().strftime("%Y%m%d"), 
                                     "005930")
        if ohlcv.empty: return None
        latest_date = ohlcv.index[-1].strftime("%Y%m%d")
        print(f"조회 기준일: {latest_date}")

        # 1. KOSPI, KOSDAQ 상위 종목 리스트 확보
        tickers = stock.get_market_ticker_list(latest_date, market="ALL")
        
        # 2. 전체 종목의 Fundamental 지표 가져오기 시도
        # (bulk API가 에러 날 경우를 대비해 try-except)
        try:
            df = stock.get_market_fundamental_by_ticker(latest_date, market="ALL")
        except:
            # 벌크 조회가 실패할 경우, 시총 상위 500개 정도만이라도 개별 조회하여 리포트 구성
            print("벌크 조회 실패. 상위 종목 개별 분석으로 전환합니다.")
            cap_df = stock.get_market_cap_by_ticker(latest_date)
            top_tickers = cap_df.sort_values(by='시가총액', ascending=False).head(500).index
            
            data = []
            for t in top_tickers:
                try:
                    f_df = stock.get_market_fundamental(latest_date, latest_date, t)
                    if not f_df.empty:
                        row = f_df.iloc[-1]
                        if row['PER'] > 0.5:
                            data.append({'티커': t, 'PER': row['PER'], 'PBR': row['PBR'], '배당수익률': row['DIV'], 'EPS': row['EPS']})
                except: continue
            df = pd.DataFrame(data).set_index('티커')

        if df.empty: return None
        
        # PER 0.5 미만(이상치) 및 0(적자/데이터없음) 제외
        df = df[df['PER'] > 0.5]
        df_sorted = df.sort_values(by='PER', ascending=True)
        
        top_df = df_sorted.head(limit).copy()
        top_df['종목명'] = [stock.get_market_ticker_name(ticker) for ticker in top_df.index]
        
        # 컬럼 존재 여부 확인 후 정리
        cols = ['종목명', 'PER', 'PBR', '배당수익률', 'EPS']
        available_cols = [c for c in cols if c in top_df.columns]
        if 'DIV' in top_df.columns: # pykrx 버전에 따라 DIV/배당수익률 이름이 다를 수 있음
            top_df = top_df.rename(columns={'DIV': '배당수익률'})
            
        return top_df[available_cols]
    except Exception as e:
        print(f"오류 발생: {e}")
        return None

def main():
    print("저PER 종목 스크리닝 중 (약 1~2분 소요될 수 있습니다)...")
    top_30 = get_low_per_stocks_crawling(30)
    
    if top_30 is None or top_30.empty:
        print("유효한 데이터를 찾지 못했습니다.")
        return

    today_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"reports/per_screener_{today_str}.md"
    os.makedirs("reports", exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 저PER 종목 스크리닝 리포트 ({today_str})\n\n")
        f.write("## 📉 한국 증시(전체) PER 하위 30개 종목\n\n")
        f.write("이 리포트는 최근 확정 영업이익을 기반으로 시장에서 가장 저평가된(PER 기준) 30개 종목을 보여줍니다.\n\n")
        f.write("- **필터:** PER 0.5 미만(데이터 오류 가능성) 및 적자 종목 제외\n")
        f.write("- **기준일:** 리포트 생성 시점의 최신 영업일\n\n")
        f.write(top_30.reset_index().to_markdown(index=False))
        f.write("\n\n*이 리포트는 자동 생성되었습니다.*")

    print(f"스크리너 리포트 생성 완료: {filename}")

if __name__ == "__main__":
    main()
