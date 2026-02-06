from pykrx import stock
import pandas as pd
from datetime import datetime
import os

def get_low_per_stocks(limit=30):
    """
    최근 확정 실적(보통 직전 연도) 기준 PER이 낮은 종목 TOP 30 추출
    """
    # 오늘 날짜
    today = datetime.now().strftime("%Y%m%d")
    
    # KOSPI, KOSDAQ 전 종목의 투자지표(PER, PBR 등) 가져오기
    # get_market_fundamental은 특정 일자의 모든 종목 지표를 반환함
    try:
        df_kospi = stock.get_market_fundamental(today, market="KOSPI")
        df_kosdaq = stock.get_market_fundamental(today, market="KOSDAQ")
        df = pd.concat([df_kospi, df_kosdaq])
    except:
        # 주말이나 공휴일일 경우 최근 영업일 데이터 사용
        print("오늘 데이터를 가져오지 못했습니다. 최근 영업일 데이터를 시도합니다.")
        return None

    # PER이 0인 것은 제외 (영업이익 적자거나 데이터 없는 경우)
    # 또한 PER이 지나치게 낮은(예: 0.1 미만) 데이터 오류 가능성 종목 필터링
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
