import pandas as pd
import yfinance as yf
from pykrx import stock
from datetime import datetime, timedelta
import os
import requests
from bs4 import BeautifulSoup
import time
import xml.etree.ElementTree as ET
import urllib.parse

def get_sector_data():
    """
    각 섹터별 최대 10개 종목 (유동성 및 시총 고려 상위 종목 중심)
    """
    return {
        "반도체": ['005930.KS', '000660.KS', '042700.KS', '000990.KS', '058470.KQ', '222800.KQ', '067310.KQ', '176440.KQ', '036540.KQ', '032500.KQ'],
        "이차전지": ['373220.KS', '006400.KS', '051910.KS', '247540.KQ', '091990.KQ', '066570.KS', '003670.KS', '391250.KQ', '078330.KQ', '086390.KQ'],
        "자동차/부품": ['005380.KS', '000270.KS', '012330.KS', '011280.KS', '000660.KS', '002350.KS', '003620.KS', '010120.KS', '006110.KS', '009150.KS'],
        "바이오": ['207940.KS', '068270.KS', '000100.KS', '326030.KS', '183490.KQ', '066970.KS', '235980.KS', '096760.KS', '111770.KS', '006280.KS'],
        "인터넷/플랫폼": ['035420.KS', '035720.KS', '323410.KS', '377300.KS', '112040.KQ', '060330.KQ', '193250.KQ', '067160.KQ', '253450.KQ', '353200.KS'],
        "은행": ['105560.KS', '055550.KS', '024110.KS', '000030.KS', '138040.KS', '139130.KS', '316140.KS', '035720.KS', '323410.KS', '175330.KS'],
        "증권/카드": ['005940.KS', '016360.KS', '039490.KS', '003550.KS', '008560.KS', '001270.KS', '029780.KS', '000810.KS', '030190.KS', '071050.KS'],
        "보험": ['005830.KS', '000810.KS', '032830.KS', '000400.KS', '002550.KS', '000060.KS', '014530.KS', '012140.KS', '012320.KS', '010140.KS'],
        "철강/금속": ['005490.KS', '004020.KS', '016380.KS', '001230.KS', '003030.KS', '010130.KS', '000670.KS', '001140.KS', '000140.KS', '000540.KS'],
        "정유/화학": ['096770.KS', '010950.KS', '051910.KS', '011780.KS', '010130.KS', '004020.KS', '006120.KS', '003670.KS', '011170.KS', '010060.KS'],
        "조선/기계": ['042660.KS', '009540.KS', '010620.KS', '010120.KS', '003550.KS', '003620.KS', '001430.KS', '006280.KS', '000990.KS', '002350.KS'],
        "방산": ['012450.KS', '047810.KS', '073190.KS', '000660.KS', '035720.KS', '005490.KS', '001230.KS', '004020.KS', '000100.KS', '005380.KS'],
        "우주항공": ['047810.KS', '272210.KS', '440820.KS', '212560.KQ', '040910.KQ', '065350.KQ', '003620.KS', '006280.KS', '002350.KS', '010120.KS'],
        "건설": ['000720.KS', '047040.KS', '006360.KS', '000810.KS', '002550.KS', '000060.KS', '014530.KS', '012140.KS', '012320.KS', '010140.KS'],
        "로봇": ['443250.KS', '043090.KQ', '189330.KQ', '389140.KQ', '214450.KQ', '137400.KQ', '222080.KS', '010120.KS', '000990.KS', '002350.KS'],
        "원자력": ['034020.KS', '052690.KS', '068290.KS', '000660.KS', '000990.KS', '002350.KS', '001430.KS', '006280.KS', '010120.KS', '003620.KS'],
        "화장품": ['051900.KS', '002790.KS', '192820.KS', '161890.KS', '214320.KS', '004020.KS', '001230.KS', '010130.KS', '000670.KS', '001140.KS'],
        "게임": ['259960.KS', '036570.KS', '251270.KQ', '063080.KQ', '293490.KQ', '060330.KQ', '193250.KQ', '067160.KQ', '253450.KQ', '353200.KS'],
        "엔터테인먼트": ['352820.KS', '035900.KQ', '041510.KQ', '122870.KQ', '253450.KQ', '293490.KQ', '353200.KS', '060330.KQ', '193250.KQ', '067160.KQ'],
        "식음료": ['097950.KS', '004370.KS', '005180.KS', '000030.KS', '138040.KS', '139130.KS', '316140.KS', '035720.KS', '323410.KS', '175330.KS']
    }

def get_ticker_name(ticker):
    names = {
        '005930.KS': '삼성전자', '000660.KS': 'SK하이닉스', '373220.KS': 'LG엔솔', '005380.KS': '현대차',
        '000270.KS': '기아', '207940.KS': '삼성바이오', '068270.KS': '셀트리온', '035420.KS': 'NAVER',
        '035720.KS': '카카오', '105560.KS': 'KB금융', '055550.KS': '신한지주', '005490.KS': 'POSCO홀딩스',
        '017670.KS': 'SK텔레콤', '030200.KS': 'KT', '259960.KS': '크래프톤', '352820.KS': '하이브',
        '051900.KS': 'LG생활건강', '002790.KS': '아모레퍼시픽', '096770.KS': 'SK이노베이션',
        '010620.KS': '현대중공업', '003490.KS': '대한항공', '011200.KS': 'HMM', '012450.KS': '한화에어로',
        '000720.KS': '현대건설', '097950.KS': 'CJ제일제당', '023530.KS': '롯데쇼핑'
    }
    return names.get(ticker, ticker)

def get_naver_investor_data(ticker_code):
    code = ticker_code.split('.')[0]
    url = f"https://finance.naver.com/item/frgn.naver?code={code}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        content = res.content.decode('cp949', 'ignore')
        soup = BeautifulSoup(content, 'html.parser')
        tables = soup.find_all('table', class_='type2')
        target_table = None
        for t in tables:
            if '날짜' in t.text:
                target_table = t; break
        if not target_table: return None
        rows = target_table.find_all('tr')
        data = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 7: continue
            date_str = cols[0].text.strip().replace('.', '')
            if not date_str or len(date_str) != 8: continue
            try:
                volume = int(cols[4].text.replace(',', ''))
                inst_net = int(cols[5].text.replace(',', ''))
                for_net = int(cols[6].text.replace(',', ''))
                data.append({'날짜': date_str, '거래량': volume, '기관': inst_net, '외국인': for_net, '개인': -(inst_net + for_net)})
            except: continue
        return pd.DataFrame(data)
    except: return None

def get_stats_yf_and_naver(tickers):
    data = yf.download(tickers, period="60d", interval="1d", progress=False)
    if data.empty: return None
    def get_ticker_df(t):
        if len(tickers) > 1:
            try: return data.xs(t, axis=1, level=1)
            except: return pd.DataFrame()
        return data
    naver_dfs = {}
    for t in tickers:
        df = get_naver_investor_data(t); naver_dfs[t] = df
        time.sleep(0.05)
    dates_yf = data.index.strftime("%Y%m%d").tolist()
    def calc_period_metrics(t_list, start_idx, end_idx, base_end_idx):
        prices, volumes = [], []
        ind_v_sum, for_v_sum, ins_v_sum = 0, 0, 0
        up_c, down_c, total_c = 0, 0, 0
        rep_ticker = t_list[0]
        rep_metrics = {"가격%": 0, "거래량": 0}
        start_date_str, end_date_str = dates_yf[start_idx], dates_yf[end_idx]
        for i, t in enumerate(t_list):
            tdf = get_ticker_df(t)
            if tdf.empty: continue
            try:
                curr_p, prev_p = tdf['Close'].iloc[end_idx], tdf['Close'].iloc[base_end_idx]
                p_change = (curr_p - prev_p) / prev_p * 100 if prev_p > 0 else 0
                if prev_p > 0:
                    prices.append(p_change); total_c += 1
                    if p_change > 0: up_c += 1
                    elif p_change < 0: down_c += 1
                v_sum = tdf['Volume'].iloc[start_idx:end_idx+1 if end_idx != -1 else None].sum()
                if not pd.isna(v_sum):
                    volumes.append(v_sum)
                    if i == 0: rep_metrics["거래량"] = int(v_sum)
                if i == 0: rep_metrics["가격%"] = round(p_change, 2)
                ndf = naver_dfs.get(t)
                if ndf is not None and not ndf.empty:
                    mask = (ndf['날짜'] >= start_date_str) & (ndf['날짜'] <= end_date_str)
                    period_ndf = ndf.loc[mask]
                    if not period_ndf.empty:
                        ind_v_sum += period_ndf['개인'].sum(); for_v_sum += period_ndf['외국인'].sum(); ins_v_sum += period_ndf['기관'].sum()
            except: continue
        avg_price = sum(prices) / len(prices) if prices else 0
        sum_vol = sum(volumes) if volumes else 0
        return {"가격%": round(avg_price, 2), "거래량": int(sum_vol), "개인": int(ind_v_sum), "외인": int(for_v_sum), "기관": int(ins_v_sum), "상승/하락": f"{up_c}/{down_c}", "상승비율%": round((up_c/total_c*100),1) if total_c>0 else 0, "rep_name": get_ticker_name(rep_ticker), "rep_price%": rep_metrics["가격%"], "rep_vol": rep_metrics["거래량"]}
    res_t = calc_period_metrics(tickers, -1, -1, -2)
    res_y = calc_period_metrics(tickers, -2, -2, -3)
    res_w = calc_period_metrics(tickers, -5, -1, -6)
    return {"당일": res_t, "어제": res_y, "주간": res_w}

def get_sector_news(sector, tickers):
    company_names = [get_ticker_name(t) for t in tickers[:3]]
    query = f"({sector}) OR ({' OR '.join(company_names)}) 주식 뉴스"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    headers = {'User-Agent': 'Mozilla/5.0'}
    today_dt = datetime.now()
    allowed_date = today_dt.strftime("%d %b %Y")
    try:
        res = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(res.content)
        raw_news = []
        for item in root.findall('.//item'):
            if allowed_date not in item.find('pubDate').text: continue
            title = item.find('title').text
            link = item.find('link').text
            if ' - ' in title: title = title.rsplit(' - ', 1)[0]
            raw_news.append({'title': title, 'link': link})
            if len(raw_news) >= 30: break
        final_filtered, seen_norm = [], []
        for news in raw_news:
            curr_norm = "".join(news['title'].split()).lower()
            duplicate = False
            for seen in seen_norm:
                if curr_norm in seen or seen in curr_norm or (len(set(curr_norm).intersection(set(seen))) / max(len(curr_norm), len(seen)) > 0.6):
                    duplicate = True; break
            if not duplicate:
                final_filtered.append(f"- {news['title']} ([링크]({news['link']}))")
                seen_norm.append(curr_norm)
                if len(final_filtered) >= 3: break
        return final_filtered if final_filtered else ["- 관련 뉴스가 없습니다."]
    except: return ["- 뉴스를 불러오지 못했습니다."]

def generate_summary(df, sector_news):
    summary = "## 📝 시장 분석 요약\n\n"
    weekly_top = df.loc[df['주간_가격%'].idxmax()]; weekly_worst = df.loc[df['주간_가격%'].idxmin()]
    summary += f"### 🚀 주간 베스트 섹터: **{weekly_top['섹터']}**\n- 지난 일주일간 평균 **{weekly_top['주간_가격%']}%** 상승 (상승비율: **{weekly_top['주간_상승비율%']}%**)\n- 대표 종목 **{weekly_top['rep_name']}**: 주간 **{weekly_top['주간_rep_price%']}%** 변동, 거래량 **{int(weekly_top['주간_rep_vol']):,}주**\n\n"
    summary += f"### 📉 주간 워스트 섹터: **{weekly_worst['섹터']}**\n- 지난 일주일간 평균 **{weekly_worst['주간_가격%']}%** 하락 (하락종목: **{weekly_worst['주간_상승/하락'].split('/')[1]}개**)\n- 대표 종목 **{weekly_worst['rep_name']}**: 주간 **{weekly_worst['주간_rep_price%']}%** 변동, 거래량 **{int(weekly_worst['주간_rep_vol']):,}주**\n\n"
    today_up = df[df['당일_가격%'] > 0]
    if not today_up.empty:
        top_today = today_up.loc[today_up['당일_가격%'].idxmax()]
        summary += f"### 📈 당일 강세 섹터: **{top_today['섹터']}**\n- 오늘 **{top_today['당일_가격%']}%** 상승하며 시장 방어. 대표 종목 **{top_today['rep_name']}** (**{top_today['당일_rep_price%']}%**)\n\n"
    else:
        worst_today = df.loc[df['당일_가격%'].idxmin()]
        summary += f"### 📉 당일 시장 동향\n- 오늘 시장 조정세. **{worst_today['섹터']}** 섹터 **{worst_today['당일_가격%']}%** 하락. (대표 종목 {worst_today['rep_name']} {worst_today['당일_rep_price%']}%)\n\n"
    summary += "### 📰 주요 섹터 뉴스 요약\n"
    for sector in ["반도체", "이차전지", "자동차/부품", "로봇", "AI/SW"]:
        if sector in sector_news:
            summary += f"**[{sector}]**\n" + "\n".join(sector_news[sector][:2]) + "\n\n"
    summary += "\n---"
    return summary

def main():
    print(f"한국 증시 섹터별 종합 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    sectors = get_sector_data(); results, sector_news_dict = [], {}
    for sector, tickers in sectors.items():
        print(f"분석 중: {sector}...")
        metrics = get_stats_yf_and_naver(tickers)
        if not metrics: continue
        sector_news_dict[sector] = get_sector_news(sector, tickers)
        res = {"섹터": sector, "당일_가격%": metrics["당일"]["가격%"], "당일_거래량": metrics["당일"]["거래량"], "당일_외인": metrics["당일"]["외인"], "당일_기관": metrics["당일"]["기관"], "당일_개인": metrics["당일"]["개인"], "당일_상승/하락": metrics["당일"]["상승/하락"], "당일_상승비율%": metrics["당일"]["상승비율%"], "당일_rep_price%": metrics["당일"]["rep_price%"], "당일_rep_vol": metrics["당일"]["rep_vol"], "어제_가격%": metrics["어제"]["가격%"], "어제_거래량": metrics["어제"]["거래량"], "어제_외인": metrics["어제"]["외인"], "어제_기관": metrics["어제"]["기관"], "어제_개인": metrics["어제"]["개인"], "어제_상승/하락": metrics["어제"]["상승/하락"], "어제_상승비율%": metrics["어제"]["상승비율%"], "어제_rep_price%": metrics["어제"]["rep_price%"], "어제_rep_vol": metrics["어제"]["rep_vol"], "주간_가격%": metrics["주간"]["가격%"], "주간_거래량": metrics["주간"]["거래량"], "주간_외인": metrics["주간"]["외인"], "주간_기관": metrics["주간"]["기관"], "주간_개인": metrics["주간"]["개인"], "주간_상승/하락": metrics["주간"]["상승/하락"], "주간_상승비율%": metrics["주간"]["상승비율%"], "주간_rep_price%": metrics["주간"]["rep_price%"], "주간_rep_vol": metrics["주간"]["rep_vol"], "rep_name": metrics["당일"]["rep_name"]}
        results.append(res)
    if not results: return
    df = pd.DataFrame(results).fillna(0)
    analysis_summary = generate_summary(df, sector_news_dict)
    today_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"reports/report_{today_str}.md"
    os.makedirs("reports", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 한국 증시 섹터별 종합 리포트 ({today_str})\n\n" + analysis_summary + "\n\n## 📊 섹터별 세부 지표\n- 가격% : 섹터 내 종목들의 평균 가격 변동률\n- 거래량 : 해당 기간 섹터 내 종목들의 총 거래량 (주)\n- 외인/기관/개인 : 해당 기간 섹터 내 종목들의 순매수 수량 합계 (주)\n- 상승/하락 : 섹터 내 상승 종목 수 / 하락 종목 수\n- 상승비율% : 섹터 내 전체 종목 중 상승한 종목의 비중\n\n")
        for period in ["당일", "어제", "주간"]:
            f.write(f"### {period} 리포트\n\n")
            display_cols = ["섹터", f"{period}_가격%", f"{period}_상승/하락", f"{period}_상승비율%", f"{period}_거래량", f"{period}_외인", f"{period}_기관", f"{period}_개인"]
            sub_df = df[display_cols].copy(); sub_df.columns = [c.replace(f"{period}_", "") for c in sub_df.columns]
            sub_df = sub_df.sort_values(by=["가격%", "거래량"], ascending=False)
            for c in sub_df.columns:
                if sub_df[c].dtype in ['int64', 'float64'] and c not in ['가격%', '상승비율%']: sub_df[c] = sub_df[c].apply(lambda x: f"{int(x):,}")
            f.write(sub_df.to_markdown(index=False) + "\n\n")
        f.write("## 🔍 섹터별 주요 뉴스 전체 보기\n\n")
        for sector, news in sector_news_dict.items():
            f.write(f"### {sector}\n" + "\n".join(news) + "\n\n")
        f.write("*이 리포트는 자동 생성되었습니다.*")
    print(f"\n[알림] 마크다운 리포트가 생성되었습니다: {filename}")

if __name__ == "__main__":
    main()
