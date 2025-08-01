import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from data import fetch_etf_data_with_retry, get_etf_list

st.set_page_config(page_title="网格策略回测", page_icon="📊", layout="centered")
st.title("📊 网格策略回测")

st.markdown("""
> 策略规则：每年年底以收盘价买入半仓，后续一年内：
> - 涨N：仓位降至25%
> - 涨2N：清仓
> - 跌N：仓位增至75%
> - 跌2N：满仓
> N为5%~50%可批量回测。
""")

etf_list = get_etf_list()
if etf_list.empty:
    st.error("无法获取ETF列表，请检查网络连接或数据源是否可用")
    st.stop()
from utils import get_favorite_etfs
all_etfs = {row['symbol']: row['name'] for _, row in etf_list.iterrows()}
favorite_etfs = get_favorite_etfs()

# 优先显示自选ETF
etf_options = list(all_etfs.keys())
if favorite_etfs:
    favorite_in_options = [etf for etf in favorite_etfs if etf in etf_options]
    other_etfs = [etf for etf in etf_options if etf not in favorite_etfs]
    etf_options = favorite_in_options + other_etfs

# 修复default类型和内容
raw_default = ["510300"]
if etf_options and raw_default:
    default = [type(etf_options[0])(x) for x in raw_default]
    default = [x for x in default if x in etf_options]
else:
    default = []

selected_codes = st.multiselect(
    "选择ETF（可多选）",
    options=etf_options,
    default=default,
    format_func=lambda x: f"{x} - {all_etfs.get(x, x)}"
)
start_date = st.date_input("开始日期", pd.to_datetime("2015-01-01"))
end_date = st.date_input("结束日期", pd.to_datetime("today"))
col1, col2, col3 = st.columns(3)
with col1:
    N_start = st.number_input("N起始(%)", min_value=1, max_value=40, value=5, step=1)
with col2:
    N_end = st.number_input("N结束(%)", min_value=N_start+1, max_value=50, value=30, step=1)
with col3:
    N_step = st.number_input("步长", min_value=1, max_value=10, value=5, step=1)
run_btn = st.button("批量回测")

# 修正版网格策略回测，返回净值曲线

def grid_backtest(df, N):
    df = df.copy()
    df = df.sort_index()
    df['year'] = df.index.year
    years = sorted(df['year'].unique())
    net_value = []
    date_list = []
    for y in years:
        year_df = df[df['year'] == y]
        if year_df.empty:
            continue
        start_price = year_df.iloc[0, 0]
        cash = 0.5  # 初始半仓，剩余现金0.5
        position = 0.5  # 当前持仓比例
        shares = 0.5 / start_price  # 买入半仓
        grid1 = start_price * (1 + N/100)
        grid2 = start_price * (1 + 2*N/100)
        grid_1 = start_price * (1 - N/100)
        grid_2 = start_price * (1 - 2*N/100)
        for dt, row in year_df.iterrows():
            price = row[0]
            # 仓位调整
            total = cash + shares * price
            if price >= grid2 and position > 0:
                # 清仓
                cash += shares * price
                shares = 0
                position = 0
            elif price >= grid1 and position > 0.25:
                # 降至25%
                target = 0.25
                target_shares = target * total / price
                delta = shares - target_shares
                cash += delta * price
                shares = target_shares
                position = target
            elif price <= grid_2 and position < 1:
                # 满仓
                target = 1
                target_shares = target * total / price
                delta = target_shares - shares
                cash -= delta * price
                shares = target_shares
                position = target
            elif price <= grid_1 and position < 0.75:
                # 增至75%
                target = 0.75
                target_shares = target * total / price
                delta = target_shares - shares
                cash -= delta * price
                shares = target_shares
                position = target
            # 每日净值
            total = cash + shares * price
            net_value.append(total)
            date_list.append(dt)
    if not net_value:
        return [1], []
    return net_value, date_list

if run_btn and selected_codes:
    for code in selected_codes:
        st.subheader(f"{code} - {all_etfs.get(code, code)}")
        df = fetch_etf_data_with_retry(code, start_date, end_date, etf_list)
        if df.empty:
            st.warning(f"{code} 数据不足，跳过")
            continue
        close_col = df.columns[0]
        data = df[[close_col]].rename(columns={close_col: 'close'})
        data = data.sort_index()
        # 批量回测
        results = []
        navs = {}
        nav_curves = {}
        for N in range(int(N_start), int(N_end)+1, int(N_step)):
            nav_curve, date_list = grid_backtest(data, N)
            final_nav = nav_curve[-1] if nav_curve else 1
            results.append({
                'N(%)': N,
                '最终净值': f"{final_nav:.4f}"
            })
            navs[N] = final_nav
            nav_curves[N] = (date_list, nav_curve)
        st.markdown(f"**回测区间：{start_date} ~ {end_date}**")
        st.markdown("**参数回测对比表：**")
        result_df = pd.DataFrame(results)
        st.dataframe(result_df, use_container_width=True)
        # 净值对比柱状图
        st.markdown("**不同N参数下最终净值对比：**")
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar([str(N) for N in navs.keys()], list(navs.values()))
        ax.set_xlabel('N(%)')
        ax.set_ylabel('最终净值')
        ax.set_title(f"{all_etfs.get(code, code)} 不同N参数网格策略最终净值对比")
        st.pyplot(fig)
        # 净值曲线对比
        st.markdown("**不同N参数下净值曲线对比：**")
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        for N, (date_list, nav_curve) in nav_curves.items():
            if not date_list:
                continue
            ax2.plot(date_list, nav_curve, label=f'N={N}')
        ax2.set_xlabel('日期')
        ax2.set_ylabel('净值')
        ax2.set_title(f"{all_etfs.get(code, code)} 不同N参数网格策略净值曲线对比")
        ax2.legend()
        st.pyplot(fig2) 