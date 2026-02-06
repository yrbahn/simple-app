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

def get_recent_op_profit(ticker):
    url = f"https://finance.naver.com/item/main.naver?code={ticker}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        content = res.content.decode('cp949', 'ignore')
        df_list = pd.read_html(content)
        
        finance_df = None
        for temp_df in df_list:
            # 주요재무정보 테이블 식별
            if any('주요재무정보' in str(col) for col in temp_df.columns):
                finance_df = temp_df
                break
        
        if finance_df is None: return None
        
        # '영업이익' 행 찾기 (정확한 매칭을 위해 인덱스 0 사용)
        op_row = finance_df[finance_df.iloc[:, 0].astype(str).str.contains('영업이익', na=False)]
        if op_row.empty: return None
        
        # 분기 데이터는 보통 컬럼 5~10 (총 6개 분기)
        # 마지막 유효한 실적 데이터 추출
        quarter_data = op_row.iloc[0, -6:]
        valid_ops = []
        for val in quarter_data:
            num = pd.to_numeric(val, errors='coerce')
            if not pd.isna(num):
                valid_ops.append(num)
        
        if not valid_ops: return None
        return int(valid_ops[-1])
    except:
        return None

def main():
    print("분석 시작...")
    base_data = []
    for p in range(1, 4): # 상위 150개 대상
        df = get_naver_market_sum(p)
        if df is not None: base_data.append(df)
        time.sleep(0.1)
    
    if not base_data: return
    full_df = pd.concat(base_data)
    
    results = []
    for _, row in full_df.iterrows():
        print(f"[{row['종목명']}] 분석 중...", end='\r')
        op = get_recent_op_profit(row['티커'])
        if op and op > 0:
            annual_op = op * 4
            # 네이버 시가총액은 이미 '억' 단위 숫자임 (예: 14,500 -> 1조 4500억)
            mkt_cap = float(str(row['시가총액']).replace(',', ''))
            op_per = round(mkt_cap / annual_op, 2)
            
            results.append({
                '종목명': row['종목명'],
                '영업이익기준PER': op_per,
                '시가총액(억)': int(mkt_cap),
                '최근분기영업이익(억)': op,
                '연환산영업이익(억)': annual_op
            })
        time.sleep(0.05)
        
    if results:
        res_df = pd.DataFrame(results)
        # PER 0.5 미만 이상치 제거 및 오름차순 정렬
        top_30 = res_df[res_df['영업이익기준PER'] > 0.5].sort_values(by='영업이익기준PER').head(30)
        
        today_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"reports/per_screener_{today_str}.md"
        os.makedirs("reports", exist_ok=True)
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# 영업이익 기반 저PER 종목 리포트 ({today_str})\n\n")
            f.write("이 리포트는 시가총액 상위 종목 중 **최근 1개 분기 영업이익 * 4**를 연간 실적으로 가정하여 계산한 PER 리스트입니다.\n\n")
            f.write("### 📊 주요 지표 안내\n")
            f.write("- **시가총액 / 최근분기영업이익 / 연환산영업이익 단위:** 억 원\n")
            f.write("- **영업이익기준PER 계산식:** 시가총액 / (최근 분기 영업이익 * 4)\n\n")
            f.write(top_30.to_markdown(index=False))
            f.write("\n\n*본 리포트는 네이버 금융 데이터를 기반으로 자동 생성되었습니다.*")
            
        print(f"\n리포트 생성 성공: {filename}")

if __name__ == "__main__":
    main()
