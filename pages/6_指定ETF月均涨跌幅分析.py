import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from data import get_etf_list, fetch_etf_data_with_retry

st.title("📈 指定ETF月均涨跌幅分析")

# 默认ETF池
DEFAULT_ETF_POOL = {
    '516300': '中证1000'
}

# 获取ETF列表
etf_list = get_etf_list()
all_etfs = {row['symbol']: row['name'] for _, row in etf_list.iterrows()} if not etf_list.empty else DEFAULT_ETF_POOL

st.markdown("""
可选择ETF，默认展示中证1000（516300）近3年、5年、10年等区间的月均涨跌幅，并作图分析其季节性规律。
""")

from utils import get_favorite_etfs, get_etf_options_with_favorites

etf_options = get_etf_options_with_favorites(etf_list) if not etf_list.empty else list(DEFAULT_ETF_POOL.keys())
# 修复default类型和内容
raw_default = list(DEFAULT_ETF_POOL.keys())
if etf_options and raw_default:
    default = [type(etf_options[0])(x) for x in raw_default]
    default = [x for x in default if x in etf_options]
else:
    default = []
with st.container():
    selected_etfs = st.multiselect(
        "🔍 选择ETF",
        options=etf_options,
        default=default,
        format_func=lambda x: f"{x} - {all_etfs.get(x, x)}"
    )

    period = st.selectbox("⏳ 选择区间", ["近3年", "近5年", "近10年"], index=0)
    period_map = {"近3年": 3, "近5年": 5, "近10年": 10}
    years = period_map[period]

    run_btn = st.button("🚀 计算月均涨跌幅并作图")

if run_btn:
    end_date = pd.to_datetime("today")
    start_date = end_date - pd.DateOffset(years=years)
    st.caption(f"📅 统计区间：{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    results = {}
    for symbol in selected_etfs:
        name = all_etfs.get(symbol, symbol)
        df = fetch_etf_data_with_retry(symbol, start_date, end_date, etf_list)
        if df.empty or len(df) < 30:
            st.caption(f"⚠️ {symbol} - {name} 数据不足，跳过")
            continue
        df = df.sort_index()
        # 取每月最后一个交易日收盘价
        df['month'] = df.index.to_period('M')
        monthly = df.groupby('month').last()
        monthly['pct'] = monthly.iloc[:, 0].pct_change()
        results[name] = monthly['pct'] * 100
    if not results:
        st.caption("❌ 无有效ETF数据")
        st.stop()
    # 合并为DataFrame
    res_df = pd.DataFrame(results)
    st.subheader("📊 各ETF每月涨跌幅曲线（单独展示）")
    for etf in res_df.columns:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=res_df.index.astype(str), y=res_df[etf], mode='lines+markers', name=etf))
        fig.update_layout(
            title=f"{etf} 每月涨跌幅（{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}）",
            xaxis_title="月份",
            yaxis_title=f"{etf} 月涨跌幅(%)"
        )
        st.plotly_chart(fig, use_container_width=True)

    # 只支持单ETF时，统计该ETF各月份平均涨跌幅
    if len(res_df.columns) == 1:
        etf = res_df.columns[0]
        st.subheader(f"📅 各月份平均涨跌幅统计（{etf}）")
        month_num = res_df.index.to_series().astype(str).str[-2:].astype(int)
        res_df['month_num'] = month_num.values
        month_avg = res_df.groupby('month_num')[etf].mean().to_frame(f'{etf}均值(%)')
        st.dataframe(month_avg.style.format({f'{etf}均值(%)': '{:.2f}%'}), use_container_width=True)
        # 可视化
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=month_avg.index.astype(str), y=month_avg[f'{etf}均值(%)'], marker_color='orange'))
        fig2.update_layout(
            title=f"各月份{etf}平均涨跌幅（{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}）",
            xaxis_title="月份",
            yaxis_title=f"{etf} 平均月涨跌幅(%)"
        )
        st.plotly_chart(fig2, use_container_width=True)
        # 结论性文字
        max_month = month_avg[f'{etf}均值(%)'].idxmax()
        min_month = month_avg[f'{etf}均值(%)'].idxmin()
        max_val = month_avg[f'{etf}均值(%)'].max()
        min_val = month_avg[f'{etf}均值(%)'].min()
        st.markdown(f"**结论：**\n\n近{years}年{etf}来看，<span style='color:red'>**{max_month}月**</span>的平均涨幅最高（{max_val:.2f}%），<span style='color:green'>**{min_month}月**</span>的平均涨幅最低（{min_val:.2f}%）。整体来看，该ETF在不同月份的表现存在一定季节性规律，建议关注高均值月份的机会。", unsafe_allow_html=True)

    # 可选：展示所有月度涨跌幅明细
    with st.expander("查看所有月度涨跌幅明细"):
        st.dataframe(res_df.drop(columns=['month_num']).style.format('{:.2f}%'), use_container_width=True) 