import requests
import pandas as pd
from datetime import datetime
import os
import time

def get_naver_per_ranking(page=1):
    """
    네이버 금융의 상위 종목(시가총액 순) 페이지에서 PER 데이터를 수집합니다.
    """
    url = f"https://finance.naver.com/sise/sise_market_sum.naver?&page={page}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url, headers=headers)
        # 네이버 금융은 EUC-KR 사용
        df_list = pd.read_html(res.content.decode('cp949', 'ignore'))
        # 시가총액 테이블은 보통 리스트의 두 번째(index 1)에 위치함
        df = df_list[1]
        
        # 불필요한 로우 제거 (구분선 등)
        df = df[df['종목명'].notna()]
        
        # 필요한 컬럼만 추출
        # 네이버 테이블 컬럼: N, 종목명, 현재가, 전일비, 등락률, 액면가, 시가총액, 상장주식수, 외국인비율, 거래량, PER, ROE
        cols = ['종목명', 'PER', '시가총액', '현재가']
        available_cols = [c for c in cols if c in df.columns]
        df = df[available_cols]
        
        return df
    except Exception as e:
        print(f"네이버 데이터 수집 오류 (Page {page}): {e}")
        return None

def main():
    print("네이버 금융 데이터를 통한 저PER 종목 스크리닝 중...")
    
    all_data = []
    # 시가총액 상위 500개 종목 분석 (페이지당 50개씩 10페이지)
    for p in range(1, 11):
        print(f"페이지 {p} 분석 중...", end='\r')
        df = get_naver_per_ranking(p)
        if df is not None:
            all_data.append(df)
        time.sleep(0.1)
    
    if not all_data:
        print("데이터를 가져오는 데 실패했습니다.")
        return
        
    full_df = pd.concat(all_data)
    
    # PER 컬럼 수치화
    full_df['PER'] = pd.to_numeric(full_df['PER'], errors='coerce')
    
    # PER이 유효한(0보다 큰) 종목만 필터링 및 0.5 미만 이상치 제거
    filtered_df = full_df[full_df['PER'] > 0.5].copy()
    
    # PER 낮은 순 정렬
    top_30 = filtered_df.sort_values(by='PER', ascending=True).head(30)
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"reports/per_screener_{today_str}.md"
    os.makedirs("reports", exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 저PER 종목 스크리닝 리포트 ({today_str})\n\n")
        f.write("## 📉 한국 증시(시총 상위 500개 중) PER 하위 30개 종목\n\n")
        f.write("이 리포트는 네이버 금융 시가총액 상위 종목들을 전수 조사하여, 현재 주가 대비 영업이익(PER)이 가장 저평가된 30개 종목을 보여줍니다.\n\n")
        f.write("- **기준:** 최근 확정 실적 기반 PER\n")
        f.write("- **필터:** PER 0.5 미만 제외 및 시총 상위 500대 종목 중심\n\n")
        f.write(top_30.to_markdown(index=False))
        f.write("\n\n*이 리포트는 자동 생성되었습니다.*")

    print(f"\n스크리너 리포트 생성 완료: {filename}")

if __name__ == "__main__":
    main()
