import pandas as pd
import yfinance as yf
from pykrx import stock
from datetime import datetime, timedelta
import os
import requests
from bs4 import BeautifulSoup
import time

def get_sector_data():
    return {
        "반도체": ['005930.KS', '000660.KS', '042700.KS', '058470.KQ', '000990.KS'],
        "이차전지": ['373220.KS', '006400.KS', '051910.KS', '247540.KQ', '003670.KS'],
        "자동차": ['005380.KS', '000270.KS', '012330.KS', '011280.KS'],
        "바이오": ['207940.KS', '068270.KS', '000100.KS', '326030.KS'],
        "인터넷/플랫폼": ['035420.KS', '035720.KS', '323410.KS', '377300.KS'],
        "금융": ['105560.KS', '055550.KS', '086790.KS', '316140.KS', '003550.KS'],
        "철강": ['005490.KS', '004020.KS', '016380.KS'],
        "통신": ['017670.KS', '030200.KS', '032640.KS'],
        "게임": ['259960.KS', '036570.KS', '251270.KQ', '063080.KQ'],
        "엔터테인먼트": ['352820.KS', '035900.KQ', '041510.KQ', '122870.KQ'],
        "화장품": ['051900.KS', '002790.KS', '192820.KS', '161890.KS', '214320.KS']
    }

def get_naver_investor_data(ticker_code):
    """
    Naver Finance에서 투자자별 매매동향(수량)을 크롤링합니다.
    """
    code = ticker_code.split('.')[0]
    url = f"https://finance.naver.com/item/frgn.naver?code={code}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        res = requests.get(url, headers=headers)
        # Naver Finance uses EUC-KR (CP949)
        content = res.content.decode('cp949', 'ignore')
        soup = BeautifulSoup(content, 'html.parser')
        
        # 'type2' 클래스를 가진 테이블 중 '날짜'가 포함된 테이블 찾기
        tables = soup.find_all('table', class_='type2')
        target_table = None
        for t in tables:
            if '날짜' in t.text:
                target_table = t
                break
        
        if not target_table:
            return None
            
        rows = target_table.find_all('tr')
        data = []
        for row in rows:
            cols = row.find_all('td')
            # 최소 7개 이상의 컬럼이 있어야 데이터 로우임
            if len(cols) < 7: continue
            
            date_str = cols[0].text.strip().replace('.', '')
            if not date_str or len(date_str) != 8: continue
            
            try:
                volume = int(cols[4].text.replace(',', ''))
                inst_net = int(cols[5].text.replace(',', ''))
                for_net = int(cols[6].text.replace(',', ''))
                # 개인은 (기관+외국인)의 반대로 추산
                ind_net = -(inst_net + for_net)
                
                data.append({
                    '날짜': date_str,
                    '거래량': volume,
                    '기관': inst_net,
                    '외국인': for_net,
                    '개인': ind_net
                })
            except:
                continue
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error scraping {ticker_code}: {e}")
        return None

def get_stats_yf_and_naver(tickers):
    data = yf.download(tickers, period="60d", interval="1d", progress=False)
    if data.empty:
        return None
        
    def get_ticker_df(t):
        if len(tickers) > 1:
            try:
                return data.xs(t, axis=1, level=1)
            except:
                return pd.DataFrame()
        return data

    # Pre-fetch Naver data
    naver_dfs = {}
    for t in tickers:
        df = get_naver_investor_data(t)
        naver_dfs[t] = df
        time.sleep(0.1)

    dates_yf = data.index.strftime("%Y%m%d").tolist()
    
    def calc_period_metrics(t_list, start_idx, end_idx, base_end_idx):
        prices = []
        volumes = []
        
        ind_v_sum, for_v_sum, ins_v_sum, total_v_sum = 0, 0, 0, 0
        
        start_date_str = dates_yf[start_idx]
        end_date_str = dates_yf[end_idx]
        
        for t in t_list:
            tdf = get_ticker_df(t)
            if tdf.empty: continue
            
            try:
                # Price change: (End Close - Base Close) / Base Close
                curr_p = tdf['Close'].iloc[end_idx]
                prev_p = tdf['Close'].iloc[base_end_idx]
                if prev_p > 0:
                    prices.append((curr_p - prev_p) / prev_p * 100)
                
                # Absolute Volume for the period
                s = start_idx
                e = end_idx + 1 if end_idx != -1 else None
                v_sum = tdf['Volume'].iloc[s:e].sum()
                if not pd.isna(v_sum):
                    volumes.append(v_sum)
                
                # Investor data from Naver
                ndf = naver_dfs.get(t)
                if ndf is not None and not ndf.empty:
                    mask = (ndf['날짜'] >= start_date_str) & (ndf['날짜'] <= end_date_str)
                    period_ndf = ndf.loc[mask]
                    if not period_ndf.empty:
                        ind_v_sum += period_ndf['개인'].sum()
                        for_v_sum += period_ndf['외국인'].sum()
                        ins_v_sum += period_ndf['기관'].sum()
                        total_v_sum += period_ndf['거래량'].sum()
            except:
                continue
        
        avg_price = sum(prices) / len(prices) if prices else 0
        sum_vol = sum(volumes) if volumes else 0
        
        return {
            "가격%": round(avg_price, 2),
            "거래량": int(sum_vol),
            "개인": int(ind_v_sum),
            "외인": int(for_v_sum),
            "기관": int(ins_v_sum)
        }

    # Results: Today, Yesterday, and Weekly
    # Today vs Yesterday Close
    res_t = calc_period_metrics(tickers, -1, -1, -2)
    # Yesterday vs Day Before yesterday Close
    res_y = calc_period_metrics(tickers, -2, -2, -3)
    # Week (last 5 days) vs 6th day ago Close
    res_w = calc_period_metrics(tickers, -5, -1, -6)

    return {
        "당일": res_t,
        "어제": res_y,
        "주간": res_w
    }

def main():
    print("=" * 80)
    print(f"한국 증시 섹터별 종합 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 80)
    
    sectors = get_sector_data()
    results = []
    
    for sector, tickers in sectors.items():
        print(f"분석 중: {sector}...")
        metrics = get_stats_yf_and_naver(tickers)
        if not metrics:
            continue
        
        res = {
            "섹터": sector,
            "당일_가격%": metrics["당일"]["가격%"], "당일_거래량": metrics["당일"]["거래량"],
            "당일_외인": metrics["당일"]["외인"], "당일_기관": metrics["당일"]["기관"], "당일_개인": metrics["당일"]["개인"],
            
            "어제_가격%": metrics["어제"]["가격%"], "어제_거래량": metrics["어제"]["거래량"],
            "어제_외인": metrics["어제"]["외인"], "어제_기관": metrics["어제"]["기관"], "어제_개인": metrics["어제"]["개인"],
            
            "주간_가격%": metrics["주간"]["가격%"], "주간_거래량": metrics["주간"]["거래량"],
            "주간_외인": metrics["주간"]["외인"], "주간_기관": metrics["주간"]["기관"], "주간_개인": metrics["주간"]["개인"]
        }
        results.append(res)
        
    if results:
        df = pd.DataFrame(results).fillna(0)
    else:
        print("데이터를 가져오지 못했습니다.")
        return
    
    # Markdown Report
    today_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"reports/report_{today_str}.md"
    os.makedirs("reports", exist_ok=True)
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 한국 증시 섹터별 종합 리포트 ({today_str})\n\n")
        f.write("## 섹터별 지표 (평균 가격 변동 및 누적 거래량)\n")
        f.write("- 가격% : 섹터 내 종목들의 평균 가격 변동률\n")
        f.write("- 거래량 : 해당 기간 섹터 내 종목들의 총 거래량 (주)\n")
        f.write("- 외인/기관/개인 : 해당 기간 섹터 내 종목들의 순매수 수량 합계 (주)\n\n")
        
        for period in ["당일", "어제", "주간"]:
            f.write(f"### {period} 리포트\n\n")
            cols = ["섹터"] + [c for c in df.columns if c.startswith(period)]
            sub_df = df[cols].copy()
            sub_df.columns = [c.replace(f"{period}_", "") for c in sub_df.columns]
            # Format large numbers with commas
            for c in sub_df.columns:
                if sub_df[c].dtype == 'int64' or sub_df[c].dtype == 'float64':
                    if c != '가격%':
                        sub_df[c] = sub_df[c].apply(lambda x: f"{int(x):,}")
            
            f.write(sub_df.to_markdown(index=False))
            f.write("\n\n")
            
        f.write("*이 리포트는 자동 생성되었습니다.*")

    print(f"\n[알림] 마크다운 리포트가 생성되었습니다: {filename}")
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()
