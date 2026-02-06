import pandas as pd
import yfinance as yf
from pykrx import stock
from datetime import datetime, timedelta
import os
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

def get_stats_yf(tickers):
    # Fetch enough data for comparisons
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

    dates = data.index.tolist()
    
    def calc_period_metrics(t_list, start_idx, end_idx, base_start_idx, base_end_idx):
        prices = []
        volumes = []
        base_volumes = []
        
        for t in t_list:
            tdf = get_ticker_df(t)
            if tdf.empty or len(tdf) < abs(min(start_idx, base_start_idx)):
                continue
                
            try:
                # Price change: Current Close vs Baseline Close
                curr_p = tdf['Close'].iloc[end_idx]
                prev_p = tdf['Close'].iloc[base_end_idx]
                
                if prev_p > 0:
                    prices.append((curr_p - prev_p) / prev_p * 100)
                
                # Volume metrics
                # Current period slice
                s = start_idx
                e = end_idx + 1 if end_idx != -1 else None
                curr_v = tdf['Volume'].iloc[s:e].mean()
                
                # Baseline period slice
                bs = base_start_idx
                be = base_end_idx + 1 if base_end_idx != -1 else None
                prev_v = tdf['Volume'].iloc[bs:be].mean()
                
                if not pd.isna(curr_v):
                    volumes.append(curr_v)
                if not pd.isna(prev_v):
                    base_volumes.append(prev_v)
            except Exception as e:
                continue
        
        avg_price = sum(prices) / len(prices) if prices else 0
        avg_vol_inc = 0
        if volumes and base_volumes:
            cv = sum(volumes) / len(volumes)
            bv = sum(base_volumes) / len(base_volumes)
            if bv > 0:
                avg_vol_inc = (cv - bv) / bv * 100
        
        return avg_price, avg_vol_inc

    # 1. 당일 (Today -1 vs Yesterday -2)
    res_t = calc_period_metrics(tickers, -1, -1, -2, -2)
    # 2. 어제 (Yesterday -2 vs Day Before -3)
    res_y = calc_period_metrics(tickers, -2, -2, -3, -3)
    # 3. 주간 (Last 5 days -5:-1 vs Prev 5 days -10:-6)
    res_w = calc_period_metrics(tickers, -5, -1, -10, -6)

    return {
        "당일": res_t,
        "어제": res_y,
        "주간": res_w
    }

def get_investor_trends(tickers, start_date, end_date):
    # Try pykrx for investor trends (KRX only)
    codes = [t.split('.')[0] for t in tickers]
    
    ind_sum, for_sum, ins_sum, val_sum = 0, 0, 0, 0
    
    # Try both KOSPI and KOSDAQ
    for mkt in ["KOSPI", "KOSDAQ"]:
        try:
            # Note: get_market_net_purchases_of_equities_by_ticker is usually more reliable than 'ALL'
            net_purchase = stock.get_market_net_purchases_of_equities_by_ticker(start_date, end_date, mkt)
            trading_value = stock.get_market_price_change(start_date, end_date, mkt)
            
            if net_purchase.empty or trading_value.empty:
                continue
                
            c_val = '거래대금' if '거래대금' in trading_value.columns else 'Value'
            
            for c in codes:
                if c in net_purchase.index and c in trading_value.index:
                    ind_sum += net_purchase.loc[c, '개인'] if '개인' in net_purchase.columns else 0
                    for_sum += net_purchase.loc[c, '외국인'] if '외국인' in net_purchase.columns else 0
                    ins_sum += net_purchase.loc[c, '기관합계'] if '기관합계' in net_purchase.columns else 0
                    val_sum += trading_value.loc[c, c_val] if c_val in trading_value.columns else 0
        except:
            continue
            
    if val_sum > 0:
        return round(ind_sum/val_sum*100, 2), round(for_sum/val_sum*100, 2), round(ins_sum/val_sum*100, 2)
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
        metrics = get_stats_yf(tickers)
        if not metrics:
            continue
        
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
