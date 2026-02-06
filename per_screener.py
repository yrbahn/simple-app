import requests
import pandas as pd
from datetime import datetime
import os
import time
import re

def get_naver_market_sum(page=1):
    """
    네이버 금융 시가총액 페이지에서 기본 데이터 수집
    """
    url = f"https://finance.naver.com/sise/sise_market_sum.naver?&page={page}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        df_list = pd.read_html(res.content.decode('cp949', 'ignore'))
        df = df_list[1]
        df = df[df['종목명'].notna()].copy()
        
        # 티커 추출 (링크에서 추출 필요)
        soup = BeautifulSoup(res.content.decode('cp949', 'ignore'), 'html.parser')
        links = soup.select('table.type_2 a.tltle')
        tickers = [re.search(r'code=(\d+)', l['href']).group(1) for l in links]
        df['티커'] = tickers
        
        return df[['티커', '종목명', '현재가', '시가총액']]
    except Exception as e:
        print(f"Error Page {page}: {e}")
        return None

def get_recent_op_profit(ticker):
    """
    네이버 금융 종목분석 페이지에서 최근 분기 영업이익 수집
    """
    url = f"https://finance.naver.com/item/main.naver?code={ticker}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        # 테이블 파싱 (기업실적분석 테이블)
        df_list = pd.read_html(res.content.decode('cp949', 'ignore'))
        # 보통 3번째 혹은 4번째 테이블이 기업실적분석
        finance_df = None
        for temp_df in df_list:
            if '주요재무정보' in str(temp_df.columns):
                finance_df = temp_df
                break
        
        if finance_df is None: return None
        
        # 분기 영업이익 행 찾기 (보통 2행 혹은 '영업이익' 행)
        op_row = finance_df[finance_df.iloc[:, 0].str.contains('영업이익', na=False)]
        if op_row.empty: return None
        
        # 최근 분기 데이터 (오른쪽에서부터 유효한 숫자 찾기)
        # 네이버 재무제표 구성: [항목, 연간4개, 분기6개]
        # 최근 분기는 보통 뒤에서 두 번째 (마지막은 추정치일 수 있음)
        quarter_data = op_row.iloc[0, -6:] # 최근 6개 분기
        valid_ops = [pd.to_numeric(v, errors='coerce') for v in quarter_data if not pd.isna(v)]
        
        if not valid_ops: return None
        recent_op = valid_ops[-1] # 가장 최근 확정 분기
        if pd.isna(recent_op): return None
        
        return int(recent_op)
    except:
        return None

def main():
    print("네이버 금융 시총 상위 종목 분석 중 (영업이익 기반 PER 계산)...")
    
    # 1. 시총 상위 200개 종목 기본 정보 가져오기 (4페이지)
    base_data = []
    for p in range(1, 5):
        print(f"시총 페이지 {p} 수집 중...", end='\r')
        df = get_naver_market_sum(p)
        if df is not None: base_data.append(df)
        time.sleep(0.1)
    
    if not base_data: return
    full_df = pd.concat(base_data)
    
    # 2. 종목별 최근 분기 영업이익 수집 및 PER 계산
    results = []
    print("\n종목별 최근 분기 영업이익 수집 중 (약 1~2분 소요)...")
    
    for idx, row in full_df.iterrows():
        ticker = row['티커']
        name = row['종목명']
        print(f"[{name}] 분석 중...", end='\r')
        
        op = get_recent_op_profit(ticker)
        if op is not None and op > 0:
            # 시가총액 단위: 억 원 (네이버 기준)
            # 최근 분기 영업이익 단위: 억 원
            # 연간 예상 영업이익 = 최근 분기 영업이익 * 4
            mkt_cap = row['시가총액'] # 단위: 억 원
            annual_op_est = op * 4
            op_per = round(mkt_cap / annual_op_est, 2)
            
            results.append({
                '티커': ticker,
                '종목명': name,
                '시가총액(억)': mkt_cap,
                '최근분기영업이익(억)': op,
                '연환산영업이익(억)': annual_op_est,
                '영업이익기준PER': op_per
            })
        time.sleep(0.05) # 서버 부하 방지
        
    if not results:
        print("분석 가능한 종목이 없습니다.")
        return
        
    res_df = pd.DataFrame(results)
    # PER 0.5 미만 이상치 제거 및 정렬
    top_30 = res_df[res_df['영업이익기준PER'] > 0.5].sort_values(by='영업이익기준PER').head(30)
    
    # 리포트 생성
    today_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"reports/per_screener_{today_str}.md"
    os.makedirs("reports", exist_ok=True)
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 영업이익 기반 저PER 종목 리포트 ({today_str})\n\n")
        f.write("## 📉 최근 분기 실적 기준 저평가 TOP 30\n\n")
        f.write("본 리포트는 일반적인 당기순이익 기반 PER 대신, **최근 1개 분기 영업이익에 4를 곱한 연환산 수치**를 기준으로 PER을 재계산했습니다.\n\n")
        f.write("- **시가총액 단위:** 억 원\n")
        f.write("- **영업이익 단위:** 억 원\n")
        f.write("- **계산식:** 시가총액 / (최근 분기 영업이익 * 4)\n")
        f.write("- **대상:** 시총 상위 200개 종목 중 영업이익 흑자 기업\n\n")
        f.write(top_30.to_markdown(index=False))
        f.write("\n\n*이 리포트는 자동 생성되었습니다.*")
        
    print(f"\n리포트 생성 완료: {filename}")

if __name__ == "__main__":
    from bs4 import BeautifulSoup
    main()
