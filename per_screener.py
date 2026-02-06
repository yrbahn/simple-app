import requests
import pandas as pd
from datetime import datetime
import os
import time
import re
from bs4 import BeautifulSoup

def get_naver_market_sum(page=1):
    url = f"https://finance.naver.com/sise/sise_market_sum.naver?&page={page}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        content = res.content.decode('cp949', 'ignore')
        df_list = pd.read_html(content)
        df = df_list[1]
        df = df[df['종목명'].notna()].copy()
        
        soup = BeautifulSoup(content, 'html.parser')
        links = soup.select('table.type_2 a.tltle')
        tickers = [re.search(r'code=(\d+)', l['href']).group(1) for l in links]
        df['티커'] = tickers
        
        return df[['티커', '종목명', '시가총액']]
    except Exception as e:
        print(f"Error Page {page}: {e}")
        return None

def get_last_4q_op_sum(ticker):
    """
    네이버 금융에서 지난 4개 분기의 영업이익 합계를 구합니다.
    """
    url = f"https://finance.naver.com/item/main.naver?code={ticker}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        content = res.content.decode('cp949', 'ignore')
        df_list = pd.read_html(content)
        
        finance_df = None
        for temp_df in df_list:
            if any('주요재무정보' in str(col) for col in temp_df.columns):
                finance_df = temp_df
                break
        
        if finance_df is None: return None
        
        # '영업이익' 행 찾기
        op_row = finance_df[finance_df.iloc[:, 0].astype(str).str.contains('영업이익', na=False)]
        if op_row.empty: return None
        
        # 분기 데이터 영역 (보통 마지막 6개 컬럼이 분기 데이터)
        # 그중 실적이 확정된 최근 4개 분기 데이터를 합산
        quarter_data = op_row.iloc[0, -6:]
        valid_values = []
        for val in quarter_data:
            # (E) 가 붙은 추정치는 제외하고 실제 확정치만 수집
            # 하지만 최근 4분기 합산이 목적이므로 추정치가 섞여있을 수 있음
            # 안전하게 숫자형으로 변환 가능한 것들 중 뒤에서 4개 추출
            num = pd.to_numeric(val, errors='coerce')
            if not pd.isna(num):
                valid_values.append(num)
        
        if len(valid_values) < 4:
            # 데이터가 4개 미만이면 있는 것만이라도 합산 (신규 상장사 등)
            if not valid_values: return None
            return int(sum(valid_values))
            
        # 가장 최근 4개 분기 합산
        return int(sum(valid_values[-4:]))
    except:
        return None

def main():
    print("지난 4분기 영업이익 기반 저PER 종목 분석 시작 (상위 250개 종목)...")
    
    # 1. 시총 상위 250개 종목 기본 정보 가져오기 (5페이지)
    base_data = []
    for p in range(1, 6):
        df = get_naver_market_sum(p)
        if df is not None: base_data.append(df)
        time.sleep(0.1)
    
    if not base_data: return
    full_df = pd.concat(base_data)
    
    results = []
    for _, row in full_df.iterrows():
        print(f"[{row['종목명']}] 실적 분석 중...", end='\r')
        op_sum = get_last_4q_op_sum(row['티커'])
        
        if op_sum and op_sum > 0:
            mkt_cap = float(str(row['시가총액']).replace(',', ''))
            # 영업이익 기반 PER = 시가총액 / (지난 4분기 영업이익 합계)
            op_per = round(mkt_cap / op_sum, 2)
            
            results.append({
                '종목명': row['종목명'],
                '영업이익기준PER': op_per,
                '시가총액(억)': int(mkt_cap),
                '최근4분기영익합계(억)': op_sum
            })
        time.sleep(0.03) # 속도 개선을 위해 대기시간 소폭 단축
        
    if results:
        res_df = pd.DataFrame(results)
        # PER 0.5 미만 이상치 제거 및 상위 50개 선정
        top_50 = res_df[res_df['영업이익기준PER'] > 0.5].sort_values(by='영업이익기준PER').head(50)
        
        today_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"reports/per_screener_{today_str}.md"
        os.makedirs("reports", exist_ok=True)
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# 4분기 합산 영업이익 기반 저PER 종목 리포트 ({today_str})\n\n")
            f.write("## 📉 지난 4개 분기 실적 합계 기준 저평가 TOP 50\n\n")
            f.write("본 리포트는 당기순이익 대신 **지난 4개 분기의 실제 영업이익 합계**를 기준으로 PER을 계산했습니다.\n\n")
            f.write("### 📊 주요 지표 안내\n")
            f.write("- **시가총액 / 최근4분기영익합계 단위:** 억 원\n")
            f.write("- **영업이익기준PER 계산식:** 시가총액 / (지난 4개 분기 영업이익 합계)\n")
            f.write("- **대상:** 시총 상위 250개 종목 중 영업이익 흑자 기업\n\n")
            f.write(top_50.to_markdown(index=False))
            f.write("\n\n*본 리포트는 네이버 금융 데이터를 기반으로 자동 생성되었습니다.*")
            
        print(f"\n리포트 생성 및 저장 완료: {filename} (TOP 50)")

if __name__ == "__main__":
    from bs4 import BeautifulSoup
    main()
