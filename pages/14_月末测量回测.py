import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from data import get_etf_list, fetch_etf_data_with_retry
from utils import get_etf_options_with_favorites, get_favorite_etfs

st.set_page_config(page_title="月末测量回测", page_icon="📅", layout="wide")
st.title("📅 月末测量回测")

st.markdown("""
> 策略逻辑：每月倒数第二个交易日买入，次月第5个交易日收盘卖出，统计每次收益。
> 支持多ETF回测，自动汇总年化收益、胜率、最大回撤等指标。
""")

# 选择ETF
etf_list = get_etf_list()
if etf_list.empty:
    st.error("无法获取ETF列表，请检查网络连接或数据源是否可用")
    st.stop()
all_etfs = {row['symbol']: row['name'] for _, row in etf_list.iterrows()}
etf_options = get_etf_options_with_favorites(etf_list)
favorite_etfs = get_favorite_etfs()
# 默认优先自选
if favorite_etfs:
    raw_default = [c for c in favorite_etfs if c in etf_options][:3]
else:
    raw_default = etf_options[:3]
if etf_options and raw_default:
    default_etfs = [type(etf_options[0])(x) for x in raw_default]
    default_etfs = [x for x in default_etfs if x in etf_options]
else:
    default_etfs = []
selected_etfs = st.multiselect(
    "选择ETF（可多选）",
    options=etf_options,
    default=default_etfs,
    format_func=lambda x: f"{x} - {all_etfs.get(x, x)}"
)

# 选择回测区间
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("开始日期", value=datetime(2018, 1, 1), min_value=datetime(2010, 1, 1))
with col2:
    end_date = st.date_input("结束日期", value=datetime.now(), min_value=start_date)

run_btn = st.button("运行月末测量回测")

# 工具函数：获取每月倒数第二和次月第5个交易日
def get_trade_dates(df):
    df = df.sort_index()
    df['month'] = df.index.to_period('M')
    buy_dates = []
    sell_dates = []
    months = df['month'].unique()
    for i in range(len(months)-1):
        this_month = months[i]
        next_month = months[i+1]
        this_month_df = df[df['month'] == this_month]
        next_month_df = df[df['month'] == next_month]
        if len(this_month_df) < 2 or len(next_month_df) < 5:
            continue
        buy_dates.append(this_month_df.index[-2])
        sell_dates.append(next_month_df.index[4])
    return buy_dates, sell_dates

# 计算月末和月初各日平均收益
def calc_daily_avg_returns(df):
    df = df.sort_index()
    df['month'] = df.index.to_period('M')
    df['day'] = df.index.day
    df['pct_change'] = df.iloc[:, 0].pct_change()
    
    # 月末两个交易日平均收益
    month_end_returns = []
    month_end_last2_returns = []
    month_end_last1_returns = []
    
    # 月初五个交易日平均收益
    month_start_returns = []
    month_start_day1_returns = []
    month_start_day2_returns = []
    month_start_day3_returns = []
    month_start_day4_returns = []
    month_start_day5_returns = []
    
    months = df['month'].unique()
    for month in months:
        month_df = df[df['month'] == month]
        if len(month_df) < 5:
            continue
            
        # 月末收益（倒数第一个和倒数第二个交易日）
        if len(month_df) >= 2:
            last2_return = month_df.iloc[-2]['pct_change']
            last1_return = month_df.iloc[-1]['pct_change']
            if not pd.isna(last2_return):
                month_end_last2_returns.append(last2_return)
            if not pd.isna(last1_return):
                month_end_last1_returns.append(last1_return)
        
        # 月初收益（前5个交易日）
        first5_days = month_df.head(5)
        for i, (idx, row) in enumerate(first5_days.iterrows()):
            day_return = row['pct_change']
            if not pd.isna(day_return):
                if i == 0:
                    month_start_day1_returns.append(day_return)
                elif i == 1:
                    month_start_day2_returns.append(day_return)
                elif i == 2:
                    month_start_day3_returns.append(day_return)
                elif i == 3:
                    month_start_day4_returns.append(day_return)
                elif i == 4:
                    month_start_day5_returns.append(day_return)
                month_start_returns.append(day_return)
    
    # 计算平均值
    avg_month_end_last2 = np.mean(month_end_last2_returns) if month_end_last2_returns else np.nan
    avg_month_end_last1 = np.mean(month_end_last1_returns) if month_end_last1_returns else np.nan
    avg_month_start_day1 = np.mean(month_start_day1_returns) if month_start_day1_returns else np.nan
    avg_month_start_day2 = np.mean(month_start_day2_returns) if month_start_day2_returns else np.nan
    avg_month_start_day3 = np.mean(month_start_day3_returns) if month_start_day3_returns else np.nan
    avg_month_start_day4 = np.mean(month_start_day4_returns) if month_start_day4_returns else np.nan
    avg_month_start_day5 = np.mean(month_start_day5_returns) if month_start_day5_returns else np.nan
    avg_month_start_all = np.mean(month_start_returns) if month_start_returns else np.nan
    
    return {
        '月末倒数第2日平均收益': avg_month_end_last2,
        '月末倒数第1日平均收益': avg_month_end_last1,
        '月初第1日平均收益': avg_month_start_day1,
        '月初第2日平均收益': avg_month_start_day2,
        '月初第3日平均收益': avg_month_start_day3,
        '月初第4日平均收益': avg_month_start_day4,
        '月初第5日平均收益': avg_month_start_day5,
        '月初5日平均收益': avg_month_start_all,
        # 保存原始数据用于折线图
        '月末倒数第2日数据': month_end_last2_returns,
        '月末倒数第1日数据': month_end_last1_returns,
        '月初第1日数据': month_start_day1_returns,
        '月初第2日数据': month_start_day2_returns,
        '月初第3日数据': month_start_day3_returns
    }

# 回测主逻辑
def backtest_month_end_measure(price_df):
    buy_dates, sell_dates = get_trade_dates(price_df)
    trades = []
    for buy, sell in zip(buy_dates, sell_dates):
        buy_price = price_df.loc[buy].values[0]
        sell_price = price_df.loc[sell].values[0]
        ret = (sell_price / buy_price) - 1
        trades.append({
            '买入日期': buy,
            '卖出日期': sell,
            '买入价': buy_price,
            '卖出价': sell_price,
            '收益率': ret
        })
    trades_df = pd.DataFrame(trades)
    return trades_df

def calc_stats(trades_df):
    if trades_df.empty:
        return {'年化收益': np.nan, '胜率': np.nan, '最大回撤': np.nan, '交易次数': 0}
    n = len(trades_df)
    total_return = (trades_df['收益率'] + 1).prod() - 1
    years = n / 12 if n > 0 else 1
    ann_return = (total_return + 1) ** (1/years) - 1 if years > 0 else np.nan
    win_rate = (trades_df['收益率'] > 0).mean()
    # 计算净值曲线和最大回撤
    nav = (trades_df['收益率'] + 1).cumprod()
    drawdown = (nav - nav.cummax()) / nav.cummax()
    max_dd = drawdown.min()
    return {
        '年化收益': ann_return,
        '胜率': win_rate,
        '最大回撤': max_dd,
        '交易次数': n
    }

if run_btn:
    if not selected_etfs:
        st.warning("请至少选择1只ETF")
        st.stop()
    result_stats = {}
    all_trades = {}
    daily_stats = {}
    
    # 新增：策略收益趋势图
    st.subheader("📈 策略收益趋势图")
    
    for symbol in selected_etfs:
        name = all_etfs.get(symbol, symbol)
        df = fetch_etf_data_with_retry(symbol, pd.to_datetime(start_date), pd.to_datetime(end_date), etf_list)
        if df.empty or len(df) < 30:
            st.warning(f"{symbol} - {name} 数据不足，跳过")
            continue
        price_df = df.copy()
        price_df = price_df.sort_index()
        trades_df = backtest_month_end_measure(price_df)
        if trades_df.empty:
            st.warning(f"{symbol} - {name} 无有效交易，跳过")
            continue
        stats = calc_stats(trades_df)
        result_stats[symbol] = stats
        all_trades[symbol] = trades_df
        # 计算日平均收益
        daily_stats[symbol] = calc_daily_avg_returns(price_df)
        
        # 创建策略收益趋势图
        col1, col2 = st.columns(2)
        
        with col1:
            # 策略净值曲线
            nav = (trades_df['收益率'] + 1).cumprod()
            fig_strategy, ax_strategy = plt.subplots(figsize=(8, 4))
            ax_strategy.plot(nav.index, nav.values, marker='o', linewidth=2, markersize=4, color='blue', label='策略净值')
            ax_strategy.set_title(f"{symbol} - {name} 策略净值曲线")
            ax_strategy.set_ylabel("净值")
            ax_strategy.set_xlabel("交易次数")
            ax_strategy.grid(True, alpha=0.3)
            ax_strategy.legend()
            st.pyplot(fig_strategy)
            
            # 策略统计
            total_return = nav.iloc[-1] - 1 if len(nav) > 0 else 0
            annual_return = (nav.iloc[-1] ** (12/len(nav)) - 1) if len(nav) > 0 else 0
            st.markdown(f"""
            **策略统计：**
            - 总收益率：{total_return:.2%}
            - 年化收益率：{annual_return:.2%}
            - 交易次数：{len(trades_df)}
            """)
        
        with col2:
            # 标的净值曲线（买入持有）
            price_series = price_df.iloc[:, 0]
            buy_hold_nav = (price_series / price_series.iloc[0])
            fig_buyhold, ax_buyhold = plt.subplots(figsize=(8, 4))
            ax_buyhold.plot(buy_hold_nav.index, buy_hold_nav.values, linewidth=2, color='red', label='标的净值')
            ax_buyhold.set_title(f"{symbol} - {name} 标的净值曲线")
            ax_buyhold.set_ylabel("净值")
            ax_buyhold.set_xlabel("日期")
            ax_buyhold.grid(True, alpha=0.3)
            ax_buyhold.legend()
            plt.xticks(rotation=45)
            st.pyplot(fig_buyhold)
            
            # 标的统计
            buyhold_return = buy_hold_nav.iloc[-1] - 1 if len(buy_hold_nav) > 0 else 0
            buyhold_annual = (buy_hold_nav.iloc[-1] ** (252/len(buy_hold_nav)) - 1) if len(buy_hold_nav) > 0 else 0
            st.markdown(f"""
            **标的统计：**
            - 总收益率：{buyhold_return:.2%}
            - 年化收益率：{buyhold_annual:.2%}
            - 持有天数：{len(buy_hold_nav)}
            """)
        
        # 策略vs标的对比
        st.subheader(f"📊 {symbol} - {name} 策略vs标的对比")
        fig_compare, ax_compare = plt.subplots(figsize=(12, 5))
        
        # 计算策略的累计收益时间序列
        strategy_cum_returns = []
        strategy_dates = []
        cumulative_return = 0
        
        for _, trade in trades_df.iterrows():
            cumulative_return += trade['收益率']
            strategy_cum_returns.append(cumulative_return)
            strategy_dates.append(trade['卖出日期'])  # 使用卖出日期作为策略收益的实现日期
        
        # 计算标的的累计收益时间序列
        price_series = price_df.iloc[:, 0]
        # 修复计算逻辑：使用正确的累计收益计算
        buyhold_cum_returns = ((price_series / price_series.iloc[0]) - 1) * 100  # 转换为百分比
        buyhold_dates = buyhold_cum_returns.index
        
        # 绘制标的累计收益
        ax_compare.plot(buyhold_dates, buyhold_cum_returns, linewidth=2, color='red', label='标的累计收益', alpha=0.8)
        
        # 绘制策略累计收益（在卖出日期标记）
        if strategy_dates and strategy_cum_returns:
            strategy_cum_percent = [r * 100 for r in strategy_cum_returns]
            ax_compare.plot(strategy_dates, strategy_cum_percent, 
                          marker='o', linewidth=2, color='blue', label='策略累计收益', markersize=6)
        
        ax_compare.set_title(f"{symbol} - {name} 策略vs标的累计收益对比")
        ax_compare.set_ylabel("累计收益率 (%)")
        ax_compare.set_xlabel("日期")
        ax_compare.legend()
        ax_compare.grid(True, alpha=0.3)
        ax_compare.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        plt.xticks(rotation=45)
        st.pyplot(fig_compare)
        
        # 修复对比统计计算
        strategy_total_return = total_return  # 策略总收益
        buyhold_total_return = buyhold_return  # 标的总收益
        excess_return = strategy_total_return - buyhold_total_return
        
        st.markdown(f"""
        **对比结果：**
        - 策略总收益：{strategy_total_return:.2%}
        - 标的总收益：{buyhold_total_return:.2%}
        - 超额收益：{excess_return:.2%}
        - 策略年化：{annual_return:.2%}
        - 标的年化：{buyhold_annual:.2%}
        """)
        
        st.markdown("---")  # 分隔线
        
        # 展示明细
        with st.expander(f"{symbol} - {name} 交易明细"):
            st.dataframe(trades_df.style.format({'买入价': '{:.2f}', '卖出价': '{:.2f}', '收益率': '{:.2%}'}), use_container_width=True)
            # 净值曲线
            nav = (trades_df['收益率'] + 1).cumprod()
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.plot(nav.index, nav.values, marker='o')
            ax.set_title(f"{symbol} - {name} 策略净值曲线")
            ax.set_ylabel("净值")
            ax.grid(True, linestyle='--', alpha=0.5)
            st.pyplot(fig)
            # 收益分布
            fig2, ax2 = plt.subplots(figsize=(6, 3))
            ax2.hist(trades_df['收益率']*100, bins=20, color='skyblue', edgecolor='k')
            ax2.set_title("单次收益分布（%）")
            ax2.set_xlabel("收益率%")
            st.pyplot(fig2)
    # 汇总统计
    if result_stats:
        st.subheader("📊 策略汇总统计")
        stats_df = pd.DataFrame(result_stats).T
        stats_df = stats_df.rename_axis("ETF代码")
        stats_df = stats_df.style.format({'年化收益': '{:.2%}', '胜率': '{:.1%}', '最大回撤': '{:.2%}'})
        st.dataframe(stats_df, use_container_width=True)
        
        # 日平均收益统计
        st.subheader("📈 日平均收益统计")
        # 只保留平均收益数据，不包含原始数据列表
        daily_stats_clean = {}
        for symbol, stats in daily_stats.items():
            daily_stats_clean[symbol] = {
                '月末倒数第2日平均收益': stats['月末倒数第2日平均收益'],
                '月末倒数第1日平均收益': stats['月末倒数第1日平均收益'],
                '月初第1日平均收益': stats['月初第1日平均收益'],
                '月初第2日平均收益': stats['月初第2日平均收益'],
                '月初第3日平均收益': stats['月初第3日平均收益'],
                '月初第4日平均收益': stats['月初第4日平均收益'],
                '月初第5日平均收益': stats['月初第5日平均收益'],
                '月初5日平均收益': stats['月初5日平均收益']
            }
        daily_stats_df = pd.DataFrame(daily_stats_clean).T
        daily_stats_df = daily_stats_df.rename_axis("ETF代码")
        daily_stats_df = daily_stats_df.style.format('{:.2%}')
        st.dataframe(daily_stats_df, use_container_width=True)
        
        # 可视化日平均收益
        if len(daily_stats) > 0:
            st.subheader("📊 日平均收益对比图")
            fig3, ax3 = plt.subplots(figsize=(10, 6))
            etf_names = [f"{s} - {all_etfs.get(s, s)}" for s in daily_stats.keys()]
            day_labels = ['月末倒数第2日', '月末倒数第1日', '月初第1日', '月初第2日', '月初第3日', '月初第4日', '月初第5日']
            day_values = ['月末倒数第2日平均收益', '月末倒数第1日平均收益', '月初第1日平均收益', '月初第2日平均收益', 
                         '月初第3日平均收益', '月初第4日平均收益', '月初第5日平均收益']
            
            x = np.arange(len(day_labels))
            width = 0.8 / len(daily_stats)
            
            for i, (symbol, stats) in enumerate(daily_stats.items()):
                values = [stats[day] for day in day_values]
                values = [v if not pd.isna(v) else 0 for v in values]
                ax3.bar(x + i * width, values, width, label=etf_names[i], alpha=0.8)
            
            ax3.set_xlabel('交易日')
            ax3.set_ylabel('平均收益率')
            ax3.set_title('各ETF日平均收益对比')
            ax3.set_xticks(x + width * (len(daily_stats) - 1) / 2)
            ax3.set_xticklabels(day_labels, rotation=45)
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            st.pyplot(fig3)
            
            # 新增折线图
            st.subheader("📈 日平均收益走势图")
            fig4, ax4 = plt.subplots(figsize=(12, 6))
            
            # 选择要显示的日期（月末倒数第2天、第1天，月初第1天、第2天、第3天）
            selected_day_labels = ['月末倒数第2日', '月末倒数第1日', '月初第1日', '月初第2日', '月初第3日']
            selected_day_values = ['月末倒数第2日平均收益', '月末倒数第1日平均收益', '月初第1日平均收益', '月初第2日平均收益', '月初第3日平均收益']
            
            x_line = np.arange(len(selected_day_labels))
            
            for symbol, stats in daily_stats.items():
                values = [stats[day] for day in selected_day_values]
                values = [v if not pd.isna(v) else 0 for v in values]
                ax4.plot(x_line, values, marker='o', linewidth=2, markersize=8, label=f"{symbol} - {all_etfs.get(symbol, symbol)}")
            
            ax4.set_xlabel('交易日')
            ax4.set_ylabel('平均收益率')
            ax4.set_title('月末月初收益走势对比')
            ax4.set_xticks(x_line)
            ax4.set_xticklabels(selected_day_labels)
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            ax4.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='零收益线')
            st.pyplot(fig4)
            
            # 新增：显示所有ETF的实际涨跌幅折线图
            st.subheader("📊 各ETF实际涨跌幅走势图")
            fig5, ax5 = plt.subplots(figsize=(14, 8))
            
            # 时间点标签
            time_labels = ['月末倒数第2日', '月末倒数第1日', '月初第1日', '月初第2日', '月初第3日']
            data_keys = ['月末倒数第2日数据', '月末倒数第1日数据', '月初第1日数据', '月初第2日数据', '月初第3日数据']
            
            # 为每个ETF绘制折线图
            for symbol, stats in daily_stats.items():
                etf_name = f"{symbol} - {all_etfs.get(symbol, symbol)}"
                
                # 获取该ETF的所有时间点数据
                all_data = []
                for key in data_keys:
                    if key in stats and stats[key]:
                        all_data.extend(stats[key])
                    else:
                        all_data.append(0)
                
                # 计算每个时间点的平均值作为该ETF的代表值
                time_avg_values = []
                for key in data_keys:
                    if key in stats and stats[key]:
                        time_avg_values.append(np.mean(stats[key]))
                    else:
                        time_avg_values.append(0)
                
                # 绘制折线
                x_points = np.arange(len(time_labels))
                ax5.plot(x_points, time_avg_values, marker='o', linewidth=2, markersize=6, label=etf_name)
            
            ax5.set_xlabel('交易日')
            ax5.set_ylabel('涨跌幅')
            ax5.set_title('各ETF月末月初实际涨跌幅走势')
            ax5.set_xticks(np.arange(len(time_labels)))
            ax5.set_xticklabels(time_labels)
            ax5.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax5.grid(True, alpha=0.3)
            ax5.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='零收益线')
            plt.tight_layout()
            st.pyplot(fig5)
            
            # 新增：按时间顺序显示所有涨跌幅数据
            st.subheader("📈 各ETF历史涨跌幅时间序列图")
            
            # 定义交易日类型
            day_types = ['月末倒数第2日', '月末倒数第1日', '月初第1日', '月初第2日', '月初第3日']
            
            # 为每个交易日类型创建独立的图表
            for day_type in day_types:
                fig_day, ax_day = plt.subplots(figsize=(14, 6))
                
                # 为每个ETF收集该交易日类型的数据
                etf_stats = {}  # 存储每个ETF的统计数据
                
                for symbol, stats in daily_stats.items():
                    etf_name = f"{symbol} - {all_etfs.get(symbol, symbol)}"
                    
                    # 获取该ETF的价格数据
                    df = fetch_etf_data_with_retry(symbol, pd.to_datetime(start_date), pd.to_datetime(end_date), etf_list)
                    if df.empty:
                        continue
                        
                    df = df.sort_index()
                    df['month'] = df.index.to_period('M')
                    df['pct_change'] = df.iloc[:, 0].pct_change()
                    
                    months = df['month'].unique()
                    dates = []
                    returns = []
                    
                    for i in range(len(months)-1):
                        this_month = months[i]
                        next_month = months[i+1]
                        this_month_df = df[df['month'] == this_month]
                        next_month_df = df[df['month'] == next_month]
                        
                        if len(this_month_df) < 2 or len(next_month_df) < 5:
                            continue
                        
                        if day_type == '月末倒数第2日':
                            date = this_month_df.index[-2]
                            ret = this_month_df.iloc[-2]['pct_change']
                        elif day_type == '月末倒数第1日':
                            date = this_month_df.index[-1]
                            ret = this_month_df.iloc[-1]['pct_change']
                        elif day_type == '月初第1日':
                            date = next_month_df.index[0]
                            ret = next_month_df.iloc[0]['pct_change']
                        elif day_type == '月初第2日':
                            date = next_month_df.index[1]
                            ret = next_month_df.iloc[1]['pct_change']
                        elif day_type == '月初第3日':
                            date = next_month_df.index[2]
                            ret = next_month_df.iloc[2]['pct_change']
                        
                        if not pd.isna(ret):
                            dates.append(date)
                            returns.append(ret)
                    
                    if dates and returns:
                        # 按日期排序
                        sorted_data = sorted(zip(dates, returns))
                        dates_sorted, returns_sorted = zip(*sorted_data)
                        
                        # 绘制时间序列
                        ax_day.plot(dates_sorted, returns_sorted, marker='o', markersize=4, linewidth=1, label=etf_name, alpha=0.8)
                        
                        # 计算统计数据
                        returns_array = np.array(returns_sorted)
                        up_days = np.sum(returns_array > 0)
                        down_days = np.sum(returns_array < 0)
                        flat_days = np.sum(returns_array == 0)
                        total_days = len(returns_array)
                        
                        etf_stats[etf_name] = {
                            '总天数': total_days,
                            '上涨天数': up_days,
                            '下跌天数': down_days,
                            '平盘天数': flat_days,
                            '上涨占比': up_days / total_days if total_days > 0 else 0,
                            '下跌占比': down_days / total_days if total_days > 0 else 0,
                            '平盘占比': flat_days / total_days if total_days > 0 else 0,
                            '平均收益': np.mean(returns_array),
                            '最大涨幅': np.max(returns_array),
                            '最大跌幅': np.min(returns_array)
                        }
                
                ax_day.set_xlabel('日期')
                ax_day.set_ylabel('涨跌幅')
                ax_day.set_title(f'{day_type}历史涨跌幅时间序列')
                ax_day.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                ax_day.grid(True, alpha=0.3)
                ax_day.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='零收益线')
                plt.xticks(rotation=45)
                plt.tight_layout()
                st.pyplot(fig_day)
                
                # 显示统计数据
                if etf_stats:
                    st.subheader(f"📊 {day_type}统计数据")
                    
                    # 创建统计表格
                    stats_data = []
                    for etf_name, stats in etf_stats.items():
                        stats_data.append({
                            'ETF': etf_name,
                            '总天数': stats['总天数'],
                            '上涨天数': stats['上涨天数'],
                            '下跌天数': stats['下跌天数'],
                            '平盘天数': stats['平盘天数'],
                            '上涨占比': f"{stats['上涨占比']:.1%}",
                            '下跌占比': f"{stats['下跌占比']:.1%}",
                            '平盘占比': f"{stats['平盘占比']:.1%}",
                            '平均收益': f"{stats['平均收益']:.2%}",
                            '最大涨幅': f"{stats['最大涨幅']:.2%}",
                            '最大跌幅': f"{stats['最大跌幅']:.2%}"
                        })
                    
                    stats_df = pd.DataFrame(stats_data)
                    st.dataframe(stats_df, use_container_width=True)
                    
                    # 添加总结
                    total_up = sum(stats['上涨天数'] for stats in etf_stats.values())
                    total_down = sum(stats['下跌天数'] for stats in etf_stats.values())
                    total_flat = sum(stats['平盘天数'] for stats in etf_stats.values())
                    total_days = sum(stats['总天数'] for stats in etf_stats.values())
                    
                    if total_days > 0:
                        overall_up_ratio = total_up / total_days
                        overall_down_ratio = total_down / total_days
                        overall_flat_ratio = total_flat / total_days
                        
                        st.markdown(f"""
                        **📈 汇总统计：**
                        - 总交易天数：{total_days}天
                        - 上涨天数：{total_up}天 ({overall_up_ratio:.1%})
                        - 下跌天数：{total_down}天 ({overall_down_ratio:.1%})
                        - 平盘天数：{total_flat}天 ({overall_flat_ratio:.1%})
                        """)
                else:
                    st.info(f"{day_type}暂无有效数据")
                
                st.markdown("---")  # 分隔线
            
            # 添加说明
            st.markdown("""
            **图表说明：**
            - 每个图表显示特定交易日类型的历史涨跌幅数据
            - 横轴为实际日期，纵轴为涨跌幅百分比
            - 红色虚线为零收益线
            - 不同颜色的线代表不同的ETF
            """)
    else:
        st.info("无有效回测结果") 