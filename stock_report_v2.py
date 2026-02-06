import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta
import os

def get_sector_data():
    return {
        "반도체": ['005930', '000660', '452230'],
        "이차전지": ['373220', '005490', '006400', '051910', '465320'],
        "자동차": ['005380', '000270', '001230'],
        "바이오": ['207940', '068270', '326030'],
        "인터넷/플랫폼": ['035420', '035720'],
        "금융": ['105560', '055550', '086790', '316140'],
        "철강": ['005490', '004020'],
        "통신": ['017670', '030200', '032640'],
        "게임": ['259960', '036570', '251270'],
        "엔터테인먼트": ['352820', '035900', '041510', '122870'],
        "화장품": ['051900', '002790', '192820', '161890']
    }

def get_trading_days(days=10):
    # 최근 영업일 리스트 가져오기 (삼성전자 기준)
    now = datetime.now()
    end_date = now.strftime("%Y%m%d")
    start_date = (now - timedelta(days=30)).strftime("%Y%m%d")
    df = stock.get_market_ohlcv(start_date, end_date, "005930")
    return df.index.strftime("%Y%m%d").tolist()[::-1]

def fetch_data(tickers, start_date, end_date):
    # OHLCV
    ohlcv = stock.get_market_ohlcv(start_date, end_date, tickers[0]) # Dummy for index
    
    # Investor Net Purchase
    investor = stock.get_market_net_purchases_of_equities_by_ticker(start_date, end_date, "KOSPI")
    # Actually, we need it per ticker to be accurate or we can filter it.
    # Better to get it for the whole market and filter.
    
    # But wait, get_market_net_purchases_of_equities_by_ticker returns a DF indexed by Ticker.
    return investor

def get_stats(tickers, start_date, end_date, prev_start=None, prev_end=None):
    prices = []
    volumes = []
    
    # Try to fetch per ticker to avoid 'ALL' bulk issues
    for t in tickers:
        try:
            df = stock.get_market_ohlcv(start_date, end_date, t)
            if not df.empty:
                # Use first row '시가' and last row '종가'
                start_p = df['시가'].iloc[0]
                end_p = df['종가'].iloc[-1]
                if start_p > 0:
                    prices.append((end_p - start_p) / start_p * 100)
                # Average volume for the period
                volumes.append(df['거래량'].mean())
        except:
            continue
            
    prev_volumes = []
    if prev_start and prev_end:
        for t in tickers:
            try:
                df_prev = stock.get_market_ohlcv(prev_start, prev_end, t)
                if not df_prev.empty:
                    prev_volumes.append(df_prev['거래량'].mean())
            except:
                continue

    avg_price_inc = sum(prices) / len(prices) if prices else 0
    vol_inc = 0
    if volumes and prev_volumes:
        curr_v = sum(volumes) / len(volumes)
        prev_v = sum(prev_volumes) / len(prev_volumes)
        if prev_v > 0:
            vol_inc = (curr_v - prev_v) / prev_v * 100

    # For investor trends, bulk usually works better but we can try-except
    ind_sum, for_sum, ins_sum, val_sum = 0, 0, 0, 0
    try:
        net_purchase = stock.get_market_net_purchases_of_equities_by_ticker(start_date, end_date, "ALL")
        trading_value = stock.get_market_price_change(start_date, end_date)
        
        c_val = '거래대금' if '거래대금' in trading_value.columns else 'Value'
        
        for t in tickers:
            if t in net_purchase.index and t in trading_value.index:
                ind_sum += net_purchase.loc[t, '개인'] if '개인' in net_purchase.columns else 0
                for_sum += net_purchase.loc[t, '외국인'] if '외국인' in net_purchase.columns else 0
                ins_sum += net_purchase.loc[t, '기관합계'] if '기관합계' in net_purchase.columns else 0
                val_sum += trading_value.loc[t, c_val] if c_val in trading_value.columns else 0
    except Exception as e:
        print(f"Warning: Failed to fetch investor data for {start_date}-{end_date}: {e}")
            
    ind_rate = (ind_sum / val_sum * 100) if val_sum > 0 else 0
    for_rate = (for_sum / val_sum * 100) if val_sum > 0 else 0
    ins_rate = (ins_sum / val_sum * 100) if val_sum > 0 else 0
    
    return {
        "가격증가율": round(avg_price_inc, 2),
        "거래량증가율": round(vol_inc, 2),
        "개인(%)": round(ind_rate, 2),
        "외국인(%)": round(for_rate, 2),
        "기관(%)": round(ins_rate, 2)
    }

def main():
    days = get_trading_days()
    print(f"Trading days: {days[:5]}")
    if not days:
        print("영업일 데이터를 가져올 수 없습니다.")
        return

    # If the latest day (today) fails, we might need to skip it or use previous day as 'today'
    # For now, let's assume the first day is 'current'
    today = days[0]
    yesterday = days[1]
    day_before_yesterday = days[2]
    
    last_week_start = days[4] if len(days) > 4 else days[-1]
    prev_week_end = days[5] if len(days) > 5 else days[-1]
    prev_week_start = days[9] if len(days) > 9 else days[-1]

    sectors = get_sector_data()
    
    all_reports = []
    
    for sector, tickers in sectors.items():
        print(f"Processing {sector}...")
        # Today
        res_today = get_stats(tickers, today, today, yesterday, yesterday)
        # Yesterday
        res_yesterday = get_stats(tickers, yesterday, yesterday, day_before_yesterday, day_before_yesterday)
        # Last Week
        res_week = get_stats(tickers, last_week_start, today, prev_week_start, prev_week_end)
        
        report = {
            "섹터": sector,
            "당일_가격%": res_today["가격증가율"],
            "당일_거래%": res_today["거래량증가율"],
            "당일_외인%": res_today["외국인(%)"],
            "당일_기관%": res_today["기관(%)"],
            "당일_개인%": res_today["개인(%)"],
            
            "어제_가격%": res_yesterday["가격증가율"],
            "어제_거래%": res_yesterday["거래량증가율"],
            "어제_외인%": res_yesterday["외국인(%)"],
            "어제_기관%": res_yesterday["기관(%)"],
            "어제_개인%": res_yesterday["개인(%)"],
            
            "주간_가격%": res_week["가격증가율"],
            "주간_거래%": res_week["거래량증가율"],
            "주간_외인%": res_week["외국인(%)"],
            "주간_기관%": res_week["기관(%)"],
            "주간_개인%": res_week["개인(%)"]
        }
        all_reports.append(report)

    df = pd.DataFrame(all_reports)
    
    # Save Markdown
    today_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"reports/sector_report_{today_str}.md"
    os.makedirs("reports", exist_ok=True)
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 한국 증시 섹터별 종합 리포트 ({today_str})\n\n")
        f.write("## 섹터별 평균 지표 (당일 / 어제 / 최근 1주일)\n")
        f.write("* 매매동향률 = (순매수대금 / 거래대금) * 100\n\n")
        
        # Create separate tables for readability
        for period in ["당일", "어제", "주간"]:
            f.write(f"### {period} 리포트\n\n")
            cols = ["섹터"] + [c for c in df.columns if c.startswith(period)]
            sub_df = df[cols].copy()
            # Rename columns for display
            sub_df.columns = [c.replace(f"{period}_", "") for c in sub_df.columns]
            f.write(sub_df.to_markdown(index=False))
            f.write("\n\n")
            
        f.write("*이 리포트는 자동 생성되었습니다.*")

    print(f"리포트 생성 완료: {filename}")
    print(df.to_string())

if __name__ == "__main__":
    main()
