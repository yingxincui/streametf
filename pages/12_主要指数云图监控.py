import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
import plotly.express as px
from datetime import datetime, timedelta

st.title("主要指数云图监控")

st.markdown("""
本页监控A股主要指数的阶段涨跌幅，分为近一周、近一月、今年以来、创立以来，采用云图（热力色块）可视化。
数据来源：东方财富网。
""")

index_symbols = [
    {"symbol": "000001", "name": "上证指数"},
    {"symbol": "000016", "name": "上证50"},
    {"symbol": "000300", "name": "沪深300"},
    {"symbol": "000852", "name": "中证1000"},
    {"symbol": "000688", "name": "科创50"},
    {"symbol": "000905", "name": "中证500"},
    {"symbol": "899050", "name": "北证50"},
    {"symbol": "932000", "name": "中证2000"},
    {"symbol": "399006", "name": "创业板指"},
    {"symbol": "000922", "name": "中证红利"}
]

@st.cache_data(ttl=3600)
def get_index_hist(symbol, start_date, end_date):
    try:
        return ak.index_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date)
    except Exception as e:
        return pd.DataFrame()

today = datetime.today()
start_dates = {
    "近一周": (today - timedelta(days=10)).strftime("%Y%m%d"),
    "近一月": (today - timedelta(days=35)).strftime("%Y%m%d"),
    "今年以来": today.replace(month=1, day=1).strftime("%Y%m%d"),
    "创立以来": "20000101"
}

periods = list(start_dates.keys())

run_btn = st.button("刷新指数云图")

if run_btn:
    result = []
    for idx in index_symbols:
        row = {"指数": idx["name"]}
        for period, start in start_dates.items():
            df = get_index_hist(idx["symbol"], start, today.strftime("%Y%m%d"))
            if df.empty or len(df) < 2:
                row[period] = np.nan
                continue
            close_col = '收盘'
            if close_col not in df.columns:
                close_cols = [c for c in df.columns if '收' in c]
                if not close_cols:
                    row[period] = np.nan
                    continue
                close_col = close_cols[0]
            df[close_col] = pd.to_numeric(df[close_col], errors='coerce')
            df = df.dropna(subset=[close_col])
            df = df.sort_values("日期")
            # 调试输出
            st.write(f"{idx['name']} {period} 原始行数: {len(df)}, 有效收盘价行数: {df.shape[0]}")
            if not df.empty:
                st.write(f"首日: {df.iloc[0]['日期']} {df.iloc[0][close_col]}, 末日: {df.iloc[-1]['日期']} {df.iloc[-1][close_col]}")
            # 若有效数据不足2行，自动向前补足
            if len(df) < 2:
                # 尝试向前多取7天
                extra_start = (datetime.strptime(start, "%Y%m%d") - timedelta(days=7)).strftime("%Y%m%d")
                df2 = get_index_hist(idx["symbol"], extra_start, today.strftime("%Y%m%d"))
                df2[close_col] = pd.to_numeric(df2[close_col], errors='coerce')
                df2 = df2.dropna(subset=[close_col])
                df2 = df2.sort_values("日期")
                if len(df2) >= 2:
                    st.write(f"{idx['name']} {period} 自动向前补足后有效行数: {df2.shape[0]}")
                    df = df2
                else:
                    row[period] = np.nan
                    continue
            # 找区间首日和末日的有效收盘价
            first = df.iloc[0]
            last = df.iloc[-1]
            if pd.isna(first[close_col]):
                first_valid = df[~df[close_col].isna()].iloc[0]
                first = first_valid
            if pd.isna(last[close_col]):
                last_valid = df[~df[close_col].isna()].iloc[-1]
                last = last_valid
            start_close = first[close_col]
            end_close = last[close_col]
            if pd.isna(start_close) or pd.isna(end_close) or start_close == 0:
                row[period] = np.nan
            else:
                pct = (end_close / start_close - 1) * 100
                row[period] = pct
        result.append(row)
    df_result = pd.DataFrame(result)
    # 计算创立以来年化
    cagr_list = []
    for i, row in df_result.iterrows():
        period = "创立以来"
        df = get_index_hist(index_symbols[i]["symbol"], start_dates[period], today.strftime("%Y%m%d"))
        close_col = '收盘'
        if close_col not in df.columns:
            close_cols = [c for c in df.columns if '收' in c]
            if not close_cols:
                cagr_list.append(np.nan)
                continue
            close_col = close_cols[0]
        df[close_col] = pd.to_numeric(df[close_col], errors='coerce')
        df = df.dropna(subset=[close_col])
        df = df.sort_values("日期")
        if len(df) < 2:
            cagr_list.append(np.nan)
            continue
        first = df.iloc[0]
        last = df.iloc[-1]
        start_close = first[close_col]
        end_close = last[close_col]
        days = (pd.to_datetime(last['日期']) - pd.to_datetime(first['日期'])).days
        years = days / 365.25 if days > 0 else 1
        if pd.isna(start_close) or pd.isna(end_close) or start_close == 0 or years <= 0:
            cagr = np.nan
        else:
            cagr = (end_close / start_close) ** (1/years) - 1
        cagr_list.append(cagr*100 if not pd.isna(cagr) else np.nan)
    df_result['创立以来年化(%)'] = cagr_list
    st.subheader("主要指数阶段涨跌幅云图")
    df_melt = df_result.melt(id_vars=["指数"], var_name="区间", value_name="涨跌幅(%)")
    fig = px.density_heatmap(df_melt, x="区间", y="指数", z="涨跌幅(%)", color_continuous_scale=["#d73027", "#ffffbf", "#1a9850"],
                             text_auto='.2f',
                             title="主要指数阶段涨跌幅云图（绿色为涨，红色为跌）")
    fig.update_traces(texttemplate='%{z:.2f}%')
    st.plotly_chart(fig, use_container_width=True)
    # 表格数字：涨幅为红色（越大越深红），跌幅为绿色（越大绝对值越深绿），零为灰色
    def color_text(val, vmin, vmax):
        try:
            v = float(val)
            if pd.isna(v):
                return 'color:#888888;'
            if v > 0:
                # 红色：#ffcccc(浅红)到#b20000(深红)
                norm = v / vmax if vmax > 0 else 0
                r = 178 + int((255-178)*(1-norm))  # 255~178
                g = int(204*(1-norm))  # 204~0
                b = int(204*(1-norm))  # 204~0
                return f'color:rgb({r},{g},{g});'
            elif v < 0:
                # 绿色：#ccffcc(浅绿)到#006400(深绿)
                norm = abs(v) / abs(vmin) if vmin < 0 else 0
                r = int(204*(1-norm))  # 204~0
                g = 255 - int((255-100)*norm)  # 255~100
                b = int(204*(1-norm))  # 204~0
                return f'color:rgb({r},{g},{r});'
            else:
                return 'color:#888888;'
        except:
            return 'color:#888888;'
    def color_col(s):
        vmin, vmax = s.min(), s.max()
        return [color_text(v, vmin, vmax) for v in s]
    periods_with_cagr = periods + ['创立以来年化(%)']
    style = df_result.style.format({k: '{:.2f}%' for k in periods_with_cagr})
    for col in periods_with_cagr:
        style = style.apply(color_col, subset=[col])
    st.dataframe(style, use_container_width=True) 