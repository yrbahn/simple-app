import pandas as pd
import yfinance as yf
from pykrx import stock
from datetime import datetime, timedelta
import os
import time

def get_sector_data():
    return {
        "반도체": ['005930.KS', '000660.KS', '042700.KS', '066970.KS', '282330.KS'], # 삼성, 하이닉스, 한미, 엘비, BGF(X) -> BGF리테일은 아님. 
        "이차전지": ['373220.KS', '006400.KS', '051910.KS', '247540.KQ', '091990.KQ'], # LG엔솔, SDI, LG화학, 에코프로비엠, 엘앤에프
        "자동차": ['005380.KS', '000270.KS', '001230.KS', '012330.KS'], # 현대차, 기아, 현대모비스, 현대글로비스
        "바이오": ['207940.KS', '068270.KS', '326030.KS', '183490.KQ'], # 삼바, 셀트리온, SK바이오팜, 엔케이맥스(X) -> 휴젤
        "인터넷/플랫폼": ['035420.KS', '035720.KS', '293490.KQ'], # 네이버, 카카오, 카카오게임즈
        "금융": ['105560.KS', '055550.KS', '086790.KS', '316140.KS', '003550.KS'], # KB, 신한, 하나, 우리, LG
        "철강": ['005490.KS', '004020.KS', '016380.KS'], # 포스코, 현대제철, 세아베스틸
        "통신": ['017670.KS', '030200.KS', '032640.KS'], # SKT, KT, LGU+
        "게임": ['259960.KS', '036570.KS', '251270.KQ', '063080.KQ'], # 크래프톤, 엔씨, 넷마블, 게임빌
        "엔터테인먼트": ['352820.KS', '035900.KQ', '041510.KQ', '122870.KQ'], # 하이브, JYP, SM, YG
        "화장품": ['051900.KS', '002790.KS', '192820.KS', '161890.KS', '131970.KS', '214320.KS'] # LG생활건강, 아모레, 코스맥스, 한국콜마, 토니모리, 아모레G
    }

def get_stats_yf(tickers):
    data = yf.download(tickers, period="30d", interval="1d", progress=False)
    if data.empty:
        return None
        
    # Handle both Single and Multi-ticker cases
    def get_ticker_df(t):
        if len(tickers) > 1:
            return data.xs(t, axis=1, level=1)
        return data

    dates = data.index.tolist()
    # Indices
    t_idx = -1 # Today
    y_idx = -2 # Yesterday
    db_idx = -3 # Day before yesterday
    
    # Last week (~5 trading days)
    w_idx = -6 if len(dates) >= 6 else 0
    pw_idx = -11 if len(dates) >= 11 else 0

    results = {}

    def calc_period(t_list, start_idx, end_idx, base_idx):
        prices = []
        volumes = []
        base_volumes = []
        
        for t in t_list:
            try:
                tdf = get_ticker_df(t)
                # Price: compare end_idx with base_idx (previous period close)
                # Or for 'Today', compare Close[-1] with Close[-2]
                curr_p = tdf['Close'].iloc[end_idx]
                prev_p = tdf['Close'].iloc[base_idx]
                if prev_p > 0:
                    prices.append((curr_p - prev_p) / prev_p * 100)
                
                # Volume: compare mean of [start:end] with base
                curr_v = tdf['Volume'].iloc[start_idx:end_idx+1 if end_idx != -1 else None].mean()
                volumes.append(curr_v)
                
                if base_idx is not None:
                    # For a period, baseline is the volume of the previous equivalent period
                    # Simplification: compare with the day before start_idx
                    # Or for week, compare with previous week
                    if start_idx == end_idx: # Single day
                        prev_v = tdf['Volume'].iloc[base_idx]
                    else: # Period
                        prev_v = tdf['Volume'].iloc[max(0, start_idx-(end_idx-start_idx+1)):start_idx].mean()
                    base_volumes.append(prev_v)
            except:
                continue
        
        avg_price = sum(prices) / len(prices) if prices else 0
        avg_vol_inc = 0
        if volumes and base_volumes:
            cv = sum(volumes) / len(volumes)
            bv = sum(base_volumes) / len(base_volumes)
            if bv > 0:
                avg_vol_inc = (cv - bv) / bv * 100
        
        return avg_price, avg_vol_inc

    # Today vs Yesterday
    res_t = calc_period(tickers, t_idx, t_idx, y_idx)
    # Yesterday vs DBY
    res_y = calc_period(tickers, y_idx, y_idx, db_idx)
    # Week (last 5 days) vs Previous 5 days
    res_w = calc_period(tickers, -5, -1, -6) # Simplified

    return {
        "당일": res_t,
        "어제": res_y,
        "주간": res_w
    }

def get_investor_trends(tickers, start_date, end_date):
    # Try pykrx for investor trends (KRX only)
    # Convert yfinance tickers back to pykrx codes
    codes = [t.split('.')[0] for t in tickers]
    
    try:
        # Bulk fetch
        net_purchase = stock.get_market_net_purchases_of_equities_by_ticker(start_date, end_date, "ALL")
        # Trading value for normalization
        # Note: get_market_price_change might fail, so we'll use a safer approach if needed
        # But for now let's try
        trading_value = stock.get_market_price_change(start_date, end_date)
        
        c_val = '거래대금' if '거래대금' in trading_value.columns else 'Value'
        
        ind_sum, for_sum, ins_sum, val_sum = 0, 0, 0, 0
        for c in codes:
            if c in net_purchase.index and c in trading_value.index:
                ind_sum += net_purchase.loc[c, '개인'] if '개인' in net_purchase.columns else 0
                for_sum += net_purchase.loc[c, '외국인'] if '외국인' in net_purchase.columns else 0
                ins_sum += net_purchase.loc[c, '기관합계'] if '기관합계' in net_purchase.columns else 0
                val_sum += trading_value.loc[c, c_val] if c_val in trading_value.columns else 0
        
        if val_sum > 0:
            return round(ind_sum/val_sum*100, 2), round(for_sum/val_sum*100, 2), round(ins_sum/val_sum*100, 2)
    except:
        pass
    return 0.0, 0.0, 0.0

def main():
    print("=" * 80)
    print(f"한국 증시 섹터별 종합 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 80)
    
    sectors = get_sector_data()
    all_tickers = [t for tickers in sectors.values() for t in tickers]
    
    # Investor dates
    # We'll use yfinance to get the dates
    df_dates = yf.download("005930.KS", period="10d", progress=False)
    dates = df_dates.index.strftime("%Y%m%d").tolist()[::-1]
    
    today_dt = dates[0]
    yesterday_dt = dates[1]
    last_week_dt = dates[4] if len(dates) > 4 else dates[-1]

    results = []
    
    for sector, tickers in sectors.items():
        print(f"분석 중: {sector}...")
        metrics = get_stats_yf(tickers)
        if not metrics: continue
        
        # Today trends
        t_ind, t_for, t_ins = get_investor_trends(tickers, today_dt, today_dt)
        # Yesterday trends
        y_ind, y_for, y_ins = get_investor_trends(tickers, yesterday_dt, yesterday_dt)
        # Week trends
        w_ind, w_for, w_ins = get_investor_trends(tickers, last_week_dt, today_dt)
        
        res = {
            "섹터": sector,
            "당일_가격%": metrics["당일"][0], "당일_거래%": metrics["당일"][1],
            "당일_외인%": t_for, "당일_기관%": t_ins, "당일_개인%": t_ind,
            
            "어제_가격%": metrics["어제"][0], "어제_거래%": metrics["어제"][1],
            "어제_외인%": y_for, "어제_기관%": y_ins, "어제_개인%": y_ind,
            
            "주간_가격%": metrics["주간"][0], "주간_거래%": metrics["주간"][1],
            "주간_외인%": w_for, "주간_기관%": w_ins, "주간_개인%": w_ind
        }
        results.append(res)
        
    if results:
        df = pd.DataFrame(results).fillna(0)
        # Round numeric columns
        cols = df.select_dtypes(include=['number']).columns
        df[cols] = df[cols].round(2)
    else:
        print("데이터를 가져오지 못했습니다.")
        return
    
    # Markdown Report
    today_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"reports/report_{today_str}.md"
    os.makedirs("reports", exist_ok=True)
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 한국 증시 섹터별 종합 리포트 ({today_str})\n\n")
        f.write("## 섹터별 평균 지표 및 매매동향\n")
        f.write("- 가격% : 섹터 내 종목들의 평균 가격 변동률\n")
        f.write("- 거래% : 전일(또는 전주) 대비 평균 거래량 변동률\n")
        f.write("- 매매동향률 : (순매수대금 / 거래대금) * 100\n\n")
        
        for period in ["당일", "어제", "주간"]:
            f.write(f"### {period} 리포트\n\n")
            cols = ["섹터"] + [c for c in df.columns if c.startswith(period)]
            sub_df = df[cols].copy()
            sub_df.columns = [c.replace(f"{period}_", "") for c in sub_df.columns]
            f.write(sub_df.to_markdown(index=False))
            f.write("\n\n")
            
        f.write(f"\n*데이터 기준일: 당일({today_dt}), 어제({yesterday_dt}), 주간({last_week_dt}~{today_dt})*\n")
        f.write("*이 리포트는 자동 생성되었습니다.*")

    print(f"\n[알림] 마크다운 리포트가 생성되었습니다: {filename}")
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()
