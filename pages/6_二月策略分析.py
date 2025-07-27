import streamlit as st
import pandas as pd
import numpy as np
from data import fetch_etf_data_with_retry, get_etf_list
from utils import get_etf_options_with_favorites

st.title("二月策略分析")

# 默认ETF池
DEFAULT_ETF_POOL = {
    '512100': '中证1000'
}

# 获取ETF列表
etf_list = get_etf_list()
if not etf_list.empty:
    etf_options = get_etf_options_with_favorites(etf_list)
    all_etfs = {row['symbol']: row['name'] for _, row in etf_list.iterrows()}
else:
    etf_options = list(DEFAULT_ETF_POOL.keys())
    all_etfs = DEFAULT_ETF_POOL

# 用户选择ETF和月份
selected_etf = st.selectbox(
    "选择ETF",
    options=etf_options,
    index=etf_options.index('512100') if '512100' in etf_options else 0,
    format_func=lambda x: f"{x} - {all_etfs.get(x, x)}"
)

month_options = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
selected_month = st.selectbox("选择买入月份", options=month_options, index=1)  # 默认选择2月

run_btn = st.button("计算策略收益")

if run_btn:
    # 获取ETF数据
    end_date = pd.to_datetime("today")
    start_date = pd.to_datetime("2010-01-01")  # 从2010年开始回测
    
    df = fetch_etf_data_with_retry(selected_etf, start_date, end_date, etf_list)
    
    if df.empty:
        st.error(f"未能获取ETF {selected_etf} 的数据")
        st.stop()
    
    df = df.sort_index()
    
    # 计算每年指定月份的收益
    month_number = month_options.index(selected_month) + 1
    df['year'] = df.index.year
    df['month'] = df.index.month
    
    # 筛选出指定月份的数据
    monthly_data = df[df['month'] == month_number]
    
    # 计算每年的收益
    yearly_returns = []
    years = sorted(monthly_data['year'].unique())
    
    for year in years:
        year_data = monthly_data[monthly_data['year'] == year]
        if not year_data.empty and len(year_data) > 1:
            # 取月初买入，月末卖出（使用收盘价模拟）
            buy_price = year_data.iloc[0].iloc[0]  # 第一天的收盘价作为买入价
            sell_price = year_data.iloc[-1].iloc[0]  # 最后一天的收盘价作为卖出价
            
            if buy_price > 0:
                return_rate = (sell_price - buy_price) / buy_price * 100
                yearly_returns.append({
                    'year': year,
                    'return': return_rate
                })
    
    if not yearly_returns:
        st.error(f"未能计算{selected_month}的收益数据")
        st.stop()
    
    # 转换为DataFrame
    returns_df = pd.DataFrame(yearly_returns)
    
    # 计算总收益率和年化收益率
    total_return = 1.0
    for ret in returns_df['return']:
        total_return *= (1 + ret / 100)
    
    total_return_percentage = (total_return - 1) * 100
    
    # 年化收益率计算
    num_years = len(returns_df)
    annualized_return = (total_return ** (1 / num_years) - 1) * 100
    
    # 用指标卡展示结果
    st.subheader("策略分析结果")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("年化收益率", f"{annualized_return:.2f}%", delta="达标" if annualized_return >= 10 else "未达标")
    with col2:
        st.metric("总收益率", f"{total_return_percentage:.2f}%")
    with col3:
        st.metric("回测周期", f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    st.markdown(f"**ETF代码:** {selected_etf}")
    st.markdown(f"**ETF名称:** {all_etfs.get(selected_etf, selected_etf)}")
    st.markdown(f"**买入月份:** {selected_month}")
    
    # 显示每年收益
    st.subheader("每年收益")
    st.dataframe(returns_df.style.format({'return': '{:.2f}%'}), use_container_width=True)
    
    # 可视化每年收益
    import plotly.graph_objects as go
    
    fig = go.Figure(data=go.Bar(x=returns_df['year'], y=returns_df['return']))
    fig.update_layout(
        title=f"{selected_etf} ETF在每年{selected_month}的收益率",
        xaxis_title="年份",
        yaxis_title="收益率(%)"
    )
    st.plotly_chart(fig, use_container_width=True)