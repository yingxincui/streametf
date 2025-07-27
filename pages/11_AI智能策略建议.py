import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
from data import fetch_etf_data_with_retry, get_etf_list

st.set_page_config(page_title="智能行情统计分析", page_icon="📊", layout="centered")
st.title("📊 智能行情统计分析")

st.markdown("""
> 自动拉取ETF行情数据，进行统计分析和可视化。
> 
> 支持多只ETF，默认展示沪深300ETF和上证50ETF。
""")

# 默认自动拉取行情数据
etf_list = get_etf_list()
if etf_list.empty:
    st.error("无法获取ETF列表，请检查网络连接或数据源是否可用")
    st.stop()
else:
    from utils import get_etf_options_with_favorites, get_favorite_etfs
    all_etfs = {row['symbol']: row['name'] for _, row in etf_list.iterrows()}
    favorite_etfs = get_favorite_etfs()
    
    # 使用utils中的函数获取优先排序的ETF选项
    etf_options = get_etf_options_with_favorites(etf_list)
    
    # 优先使用自选ETF作为默认选择
    if favorite_etfs:
        default_codes = [c for c in favorite_etfs if c in all_etfs][:3]  # 最多选择3个自选ETF
    else:
        default_codes = [c for c in ["510300", "510880"] if c in all_etfs]
    
    selected_codes = st.multiselect(
        "选择ETF（可多选，支持搜索，显示名称）",
        options=etf_options,
        default=default_codes,
        format_func=lambda x: f"{x} - {all_etfs.get(x, x)}"
    )
start_date = st.date_input("开始日期", pd.to_datetime("2022-01-01"))
end_date = st.date_input("结束日期", pd.to_datetime("today"))
fetch_btn = st.button("拉取行情数据")

df = None
if selected_codes and fetch_btn:
    all_df = []
    for code in selected_codes:
        d = fetch_etf_data_with_retry(code, start_date, end_date, etf_list)
        if not d.empty:
            all_df.append(d)
        else:
            st.warning(f"{code} 无法获取数据或无数据")
    if all_df:
        df = pd.concat(all_df, axis=1, join='outer')
        df = df.reset_index().rename(columns={'index': '日期'})
        df = df.sort_values("日期")
        st.success("行情数据拉取成功！")
    else:
        df = None

# 数据预览和统计分析
if df is not None:
    st.write("**数据预览：**")
    st.dataframe(df.head(), use_container_width=True)
    date_col = '日期'
    price_cols = [col for col in df.columns if col != date_col]
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    df = df.sort_values(date_col)
    df = df.set_index(date_col)

    # 收盘价走势图 -> 归一化累计涨跌幅走势图
    st.markdown("### 归一化累计涨跌幅走势图")
    norm_df = df[price_cols] / df[price_cols].iloc[0] - 1  # 归一化，首日为0
    fig, ax = plt.subplots(figsize=(8, 4))
    (norm_df * 100).plot(ax=ax)
    ax.set_ylabel("累计涨跌幅(%)")
    ax.set_xlabel("日期")
    ax.set_title("归一化累计涨跌幅对比")
    ax.legend(loc='best')
    ax.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig)

    st.markdown("### 日涨跌幅分布")
    pct_change = df[price_cols].pct_change().dropna()*100
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    for col in price_cols:
        sns.histplot(pct_change[col], bins=40, kde=True, label=col, ax=ax2, alpha=0.5)
    ax2.set_xlabel("日涨跌幅(%)")
    ax2.set_ylabel("频数")
    ax2.legend()
    st.pyplot(fig2)

    # 统计分析表
    st.markdown("### 统计分析表")
    stats = df[price_cols].describe().T
    stats = stats[['count','mean','std','min','max']]
    stats = stats.rename(columns={'count':'样本数','mean':'均值','std':'标准差','min':'最小值','max':'最大值'})
    st.dataframe(stats, use_container_width=True)

    st.markdown("### 日涨跌幅区间（%）")
    pct_stats = pct_change.agg(['min','max','mean','std']).T.round(2)
    def color_pct(val):
        try:
            v = float(val)
            if v > 0:
                return 'color:red;'
            elif v < 0:
                return 'color:green;'
        except:
            pass
        return ''
    def fmt_zero(val):
        try:
            v = float(val)
            if abs(v) < 1e-6:
                return ""
            return f"{v:.2f}"
        except:
            return val
    st.dataframe(pct_stats.style.format(fmt_zero).applymap(color_pct), use_container_width=True)

    if len(price_cols) > 1:
        st.markdown("### 资产间相关性热力图")
        fig3, ax3 = plt.subplots(figsize=(6, 4))
        corr = df[price_cols].corr()
        sns.heatmap(corr, annot=True, cmap='coolwarm', ax=ax3)
        st.pyplot(fig3)

    # ===== 文字性总结分析 =====
    st.markdown("## 文字性总结分析")
    
    # ====== 标的月度涨跌幅热力图 ======
    if len(price_cols) > 0:
        st.markdown("### 标的月度涨跌幅热力图")
        import plotly.figure_factory as ff
        col = price_cols[0]
        monthly_price = df[col].resample('M').last()
        monthly_ret = monthly_price.pct_change() * 100
        heatmap_df = monthly_ret.to_frame(name='涨跌幅').reset_index()
        heatmap_df['年'] = heatmap_df['日期'].dt.year
        heatmap_df['月'] = heatmap_df['日期'].dt.month
        heatmap_pivot = heatmap_df.pivot(index='年', columns='月', values='涨跌幅').fillna(0)
        fig_heat = ff.create_annotated_heatmap(
            z=heatmap_pivot.values,
            x=[str(m) for m in heatmap_pivot.columns],
            y=[str(y) for y in heatmap_pivot.index],
            annotation_text=np.round(heatmap_pivot.values, 2),
            colorscale='RdYlGn', showscale=True, reversescale=True
        )
        fig_heat.update_layout(title=f"{col} 月度涨跌幅热力图", xaxis_title="月份", yaxis_title="年份")
        st.plotly_chart(fig_heat, use_container_width=True)

    # 1. 总涨幅
    summary_lines = []
    for col in price_cols:
        first = df[col].iloc[0]
        last = df[col].iloc[-1]
        total_return = (last / first - 1) * 100 if first > 0 else float('nan')
        color = 'red' if total_return > 0 else 'green' if total_return < 0 else 'black'
        summary_lines.append(f"- **{col}** 区间总涨幅：<span style='color:{color}'>{fmt_zero(total_return)}%</span>（{df.index[0].date()} ~ {df.index[-1].date()}）")
    st.markdown("\n".join(summary_lines), unsafe_allow_html=True)

    # 2. 各月平均涨幅
    st.markdown("**各月平均涨幅（%）：**")
    month_pct = df[price_cols].resample('M').last().pct_change().dropna()*100
    month_avg = month_pct.groupby(month_pct.index.month).mean().round(2)
    month_avg.index = [f"{m}月" for m in month_avg.index]
    st.dataframe(month_avg.T.style.format(fmt_zero).applymap(color_pct), use_container_width=True)
    # 柱状图
    fig_month, ax_month = plt.subplots(figsize=(8, 4))
    month_avg.plot(kind='bar', ax=ax_month)
    ax_month.set_ylabel("平均月涨幅(%)")
    ax_month.set_xlabel("月份")
    ax_month.set_title("各月平均涨幅对比")
    st.pyplot(fig_month)
    # 文字结论
    for col in price_cols:
        best_month = month_avg[col].idxmax()
        best_val = month_avg[col].max()
        color = 'red' if best_val > 0 else 'green' if best_val < 0 else 'black'
        st.markdown(f"- **{col}** 平均涨幅最高的月份：{best_month}（<span style='color:{color}'>{fmt_zero(best_val)}%</span>）", unsafe_allow_html=True)

    # 3. 每年涨幅分析
    st.markdown("**每年涨幅（%）：**")
    year_pct = df[price_cols].resample('Y').last().pct_change().dropna()*100
    year_pct.index = year_pct.index.year
    st.dataframe(year_pct.T.style.format(fmt_zero).applymap(color_pct), use_container_width=True)
    # 年度涨幅折线+点图
    fig_year, ax_year = plt.subplots(figsize=(8, 4))
    for col in price_cols:
        ax_year.plot(year_pct.index, year_pct[col], marker='o', label=col)
    ax_year.set_ylabel("年度涨幅(%)")
    ax_year.set_xlabel("年份")
    ax_year.set_title("每年涨幅对比（折线图）")
    ax_year.legend()
    ax_year.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig_year)
    # 文字结论
    for col in price_cols:
        best_year = year_pct[col].idxmax()
        best_val = year_pct[col].max()
        color = 'red' if best_val > 0 else 'green' if best_val < 0 else 'black'
        st.markdown(f"- **{col}** 涨幅最高的年份：{best_year}（<span style='color:{color}'>{fmt_zero(best_val)}%</span>）", unsafe_allow_html=True)

    # 年化收益率（CAGR）分析
    st.markdown("**年化收益率（CAGR）分析：**")
    cagr_lines = []
    for col in price_cols:
        first = df[col].iloc[0]
        last = df[col].iloc[-1]
        n_years = (df.index[-1] - df.index[0]).days / 365.25
        cagr = (last / first) ** (1 / n_years) - 1 if first > 0 and n_years > 0 else float('nan')
        color = 'red' if cagr > 0 else 'green' if cagr < 0 else 'black'
        cagr_lines.append(f"- **{col}** 区间年化收益率：<span style='color:{color}'>{fmt_zero(cagr*100)}%</span>（{df.index[0].date()} ~ {df.index[-1].date()}，共{n_years:.2f}年）")
    st.markdown("\n".join(cagr_lines), unsafe_allow_html=True)
    # ===== 文字性总结分析结束 =====

    # 数据下载按钮
    csv_bytes = df.reset_index().to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="下载当前数据 (CSV)",
        data=csv_bytes,
        file_name="strategy_data.csv",
        mime="text/csv"
    )
else:
    st.info("请先选择ETF并拉取行情数据。") 