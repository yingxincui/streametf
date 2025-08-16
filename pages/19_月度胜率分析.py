import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from data import get_etf_list, fetch_etf_data_with_retry
from utils import get_etf_options_with_favorites, get_favorite_etfs

st.set_page_config(page_title="月度胜率分析", page_icon="📈", layout="wide")
st.title("📈 月度胜率分析")

st.markdown("""
> 分析每个月份的涨跌情况，统计哪个月胜率最高。
> 胜率定义为：该月上涨天数占总交易天数的比例。
> 帮助识别哪个月最容易上涨，哪个月最容易下跌。
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

run_btn = st.button("运行月度胜率分析")

def analyze_monthly_returns(df):
    """分析每个月的涨跌情况"""
    df = df.sort_index()
    df['pct_change'] = df.iloc[:, 0].pct_change()
    df['month'] = df.index.month
    df['year'] = df.index.year
    df['year_month'] = df.index.to_period('M')
    
    monthly_stats = {}
    month_names = {
        1: '1月', 2: '2月', 3: '3月', 4: '4月', 5: '5月', 6: '6月',
        7: '7月', 8: '8月', 9: '9月', 10: '10月', 11: '11月', 12: '12月'
    }
    
    for month in range(1, 13):
        month_data = df[df['month'] == month]
        if len(month_data) == 0:
            continue
            
        returns = month_data['pct_change'].dropna()
        if len(returns) == 0:
            continue
            
        # 按年月分组计算月度收益
        monthly_returns = []
        for year_month, group in month_data.groupby('year_month'):
            group_returns = group['pct_change'].dropna()
            if len(group_returns) > 0:
                # 计算该月的累计收益
                month_cumulative_return = (1 + group_returns).prod() - 1
                monthly_returns.append(month_cumulative_return)
        
        if len(monthly_returns) == 0:
            continue
            
        # 日度统计
        up_days = np.sum(returns > 0)
        down_days = np.sum(returns < 0)
        flat_days = np.sum(returns == 0)
        total_days = len(returns)
        
        # 月度统计
        monthly_returns = np.array(monthly_returns)
        up_months = np.sum(monthly_returns > 0)
        down_months = np.sum(monthly_returns < 0)
        flat_months = np.sum(monthly_returns == 0)
        total_months = len(monthly_returns)
        
        monthly_stats[month] = {
            # 日度统计
            '总天数': total_days,
            '上涨天数': up_days,
            '下跌天数': down_days,
            '平盘天数': flat_days,
            '日度胜率': up_days / total_days if total_days > 0 else 0,
            '日度平均收益': np.mean(returns),
            '日度最大涨幅': np.max(returns),
            '日度最大跌幅': np.min(returns),
            '日度收益标准差': np.std(returns),
            # 月度统计
            '总月数': total_months,
            '上涨月数': up_months,
            '下跌月数': down_months,
            '平盘月数': flat_months,
            '月度胜率': up_months / total_months if total_months > 0 else 0,
            '月度平均收益': np.mean(monthly_returns),
            '月度最大涨幅': np.max(monthly_returns),
            '月度最大跌幅': np.min(monthly_returns),
            '月度收益标准差': np.std(monthly_returns),
            '月度收益列表': monthly_returns.tolist()
        }
    
    return monthly_stats

if run_btn:
    if not selected_etfs:
        st.warning("请至少选择1只ETF")
        st.stop()
    
    all_monthly_stats = {}
    
    for symbol in selected_etfs:
        name = all_etfs.get(symbol, symbol)
        df = fetch_etf_data_with_retry(symbol, pd.to_datetime(start_date), pd.to_datetime(end_date), etf_list)
        if df.empty or len(df) < 30:
            st.warning(f"{symbol} - {name} 数据不足，跳过")
            continue
        
        monthly_stats = analyze_monthly_returns(df)
        all_monthly_stats[symbol] = monthly_stats
        
        # 显示每个ETF的月度统计
        st.subheader(f"📊 {symbol} - {name} 月度胜率统计")
        
        if monthly_stats:
            # 创建统计表格
            stats_data = []
            month_names = {
                1: '1月', 2: '2月', 3: '3月', 4: '4月', 5: '5月', 6: '6月',
                7: '7月', 8: '8月', 9: '9月', 10: '10月', 11: '11月', 12: '12月'
            }
            
            for month, stats in monthly_stats.items():
                stats_data.append({
                    '月份': month_names[month],
                    '总月数': stats['总月数'],
                    '上涨月数': stats['上涨月数'],
                    '下跌月数': stats['下跌月数'],
                    '月度胜率': f"{stats['月度胜率']:.1%}",
                    '月度平均收益': f"{stats['月度平均收益']:.2%}",
                    '月度最大涨幅': f"{stats['月度最大涨幅']:.2%}",
                    '月度最大跌幅': f"{stats['月度最大跌幅']:.2%}",
                    '日度胜率': f"{stats['日度胜率']:.1%}",
                    '日度平均收益': f"{stats['日度平均收益']:.2%}",
                    '总天数': stats['总天数']
                })
            
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True)
            
            # 可视化
            col1, col2 = st.columns(2)
            
            with col1:
                # 月度胜率柱状图
                months = list(monthly_stats.keys())
                month_labels = [month_names[m] for m in months]
                monthly_win_rates = [monthly_stats[m]['月度胜率'] for m in months]
                
                fig1, ax1 = plt.subplots(figsize=(10, 5))
                bars = ax1.bar(month_labels, monthly_win_rates, 
                              color=['red' if r > 0.5 else 'green' for r in monthly_win_rates], alpha=0.7)
                ax1.set_xlabel('月份')
                ax1.set_ylabel('月度胜率')
                ax1.set_title(f'{symbol} - {name} 各月胜率分布')
                ax1.axhline(y=0.5, color='black', linestyle='--', alpha=0.5, label='50%基准线')
                ax1.legend()
                ax1.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                st.pyplot(fig1)
            
            with col2:
                # 月度平均收益柱状图
                monthly_avg_returns = [monthly_stats[m]['月度平均收益'] for m in months]
                
                fig2, ax2 = plt.subplots(figsize=(10, 5))
                bars = ax2.bar(month_labels, monthly_avg_returns, 
                              color=['red' if r > 0 else 'green' for r in monthly_avg_returns], alpha=0.7)
                ax2.set_xlabel('月份')
                ax2.set_ylabel('月度平均收益率')
                ax2.set_title(f'{symbol} - {name} 各月平均收益')
                ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
                ax2.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                st.pyplot(fig2)
                
            # 月度收益分布箱线图
            st.subheader(f"📦 {symbol} - {name} 各月收益分布")
            
            fig3, ax3 = plt.subplots(figsize=(12, 6))
            returns_data = []
            labels = []
            for month in months:
                returns_list = monthly_stats[month]['月度收益列表']
                if len(returns_list) > 0:
                    returns_data.append([r * 100 for r in returns_list])  # 转换为百分比
                    labels.append(month_names[month])
            
            if returns_data:
                box_plot = ax3.boxplot(returns_data, labels=labels, patch_artist=True)
                for patch in box_plot['boxes']:
                    patch.set_facecolor('lightblue')
                    patch.set_alpha(0.7)
                ax3.set_xlabel('月份')
                ax3.set_ylabel('月度收益率 (%)')
                ax3.set_title(f'{symbol} - {name} 各月收益分布箱线图')
                ax3.axhline(y=0, color='red', linestyle='--', alpha=0.5)
                ax3.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                st.pyplot(fig3)
            
            # 累计收益趋势图
            st.subheader(f"📈 {symbol} - {name} 累计收益趋势图")
            
            # 计算标的累计收益
            df_processed = df.copy()
            df_processed['pct_change'] = df_processed.iloc[:, 0].pct_change()
            df_processed['month'] = df_processed.index.month
            
            price_series = df_processed.iloc[:, 0]
            buyhold_cum_returns = ((price_series / price_series.iloc[0]) - 1) * 100
            
            # 计算每月累计收益
            monthly_cum_returns = {}
            for month in range(1, 13):
                month_data = df_processed[df_processed['month'] == month]
                if len(month_data) > 0:
                    month_data_clean = month_data.dropna(subset=['pct_change'])
                    if len(month_data_clean) > 0:
                        month_returns = month_data_clean['pct_change']
                        # 计算该月的累计收益
                        cum_returns = (1 + month_returns).cumprod() - 1
                        monthly_cum_returns[month] = {
                            'dates': month_data_clean.index,
                            'returns': cum_returns * 100  # 转换为百分比
                        }
            
            # 绘制趋势图
            fig_trend, ax_trend = plt.subplots(figsize=(14, 8))
            
            # 绘制标的累计收益
            ax_trend.plot(buyhold_cum_returns.index, buyhold_cum_returns.values, 
                         linewidth=2, color='black', label='标的累计收益', alpha=0.8)
            
            # 绘制每月累计收益
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FCEA2B', '#FF9FF3',
                     '#54A0FF', '#5F27CD', '#FD79A8', '#FDCB6E', '#6C5CE7', '#A29BFE']
            month_names_full = ['1月', '2月', '3月', '4月', '5月', '6月',
                               '7月', '8月', '9月', '10月', '11月', '12月']
            
            for month in range(1, 13):
                if month in monthly_cum_returns:
                    ax_trend.plot(monthly_cum_returns[month]['dates'], 
                                monthly_cum_returns[month]['returns'],
                                linewidth=1.5, color=colors[month-1], 
                                label=f'{month_names_full[month-1]}累计收益', alpha=0.7)
            
            ax_trend.set_xlabel('日期')
            ax_trend.set_ylabel('累计收益率 (%)')
            ax_trend.set_title(f'{symbol} - {name} 标的vs各月累计收益趋势')
            ax_trend.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax_trend.grid(True, alpha=0.3)
            ax_trend.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig_trend)
        else:
            st.info(f"{symbol} - {name} 暂无有效数据")
        
        st.markdown("---")
    
    # 汇总统计
    if all_monthly_stats:
        st.subheader("📈 汇总统计")
        
        # 计算所有ETF的汇总统计
        summary_stats = {}
        month_names = {
            1: '1月', 2: '2月', 3: '3月', 4: '4月', 5: '5月', 6: '6月',
            7: '7月', 8: '8月', 9: '9月', 10: '10月', 11: '11月', 12: '12月'
        }
        
        for month in range(1, 13):
            total_up_months = 0
            total_down_months = 0
            total_flat_months = 0
            total_months = 0
            all_monthly_returns = []
            total_up_days = 0
            total_down_days = 0
            total_flat_days = 0
            total_days = 0
            all_daily_returns = []
            
            for symbol, monthly_stats in all_monthly_stats.items():
                if month in monthly_stats:
                    stats = monthly_stats[month]
                    # 月度统计
                    total_up_months += stats['上涨月数']
                    total_down_months += stats['下跌月数']
                    total_flat_months += stats['平盘月数']
                    total_months += stats['总月数']
                    all_monthly_returns.extend(stats['月度收益列表'])
                    # 日度统计
                    total_up_days += stats['上涨天数']
                    total_down_days += stats['下跌天数']
                    total_flat_days += stats['平盘天数']
                    total_days += stats['总天数']
                    all_daily_returns.append(stats['日度平均收益'])
            
            if total_months > 0:
                summary_stats[month] = {
                    # 月度统计
                    '总月数': total_months,
                    '上涨月数': total_up_months,
                    '下跌月数': total_down_months,
                    '平盘月数': total_flat_months,
                    '月度胜率': total_up_months / total_months,
                    '月度平均收益': np.mean(all_monthly_returns) if all_monthly_returns else 0,
                    # 日度统计
                    '总天数': total_days,
                    '上涨天数': total_up_days,
                    '下跌天数': total_down_days,
                    '平盘天数': total_flat_days,
                    '日度胜率': total_up_days / total_days if total_days > 0 else 0,
                    '日度平均收益': np.mean(all_daily_returns) if all_daily_returns else 0
                }
        
        if summary_stats:
            # 创建汇总表格
            summary_data = []
            for month, stats in summary_stats.items():
                summary_data.append({
                    '月份': month_names[month],
                    '总月数': stats['总月数'],
                    '上涨月数': stats['上涨月数'],
                    '下跌月数': stats['下跌月数'],
                    '月度胜率': f"{stats['月度胜率']:.1%}",
                    '月度平均收益': f"{stats['月度平均收益']:.2%}",
                    '日度胜率': f"{stats['日度胜率']:.1%}",
                    '日度平均收益': f"{stats['日度平均收益']:.2%}",
                    '总天数': stats['总天数']
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
            
            # 汇总可视化 - 胜率vs收益散点图
            etf_names_str = "、".join([f"{str(symbol)}({all_etfs.get(str(symbol), str(symbol))})" for symbol in selected_etfs])
            st.subheader(f"📊 月度胜率与收益关系分析")
            st.markdown(f"**分析标的：** {etf_names_str}")
            
            fig6, ax6 = plt.subplots(figsize=(12, 8))
            
            months = list(summary_stats.keys())
            month_labels = [month_names[m] for m in months]
            monthly_win_rates = [summary_stats[m]['月度胜率'] for m in months]
            monthly_avg_returns = [summary_stats[m]['月度平均收益'] for m in months]
            
            # 散点图
            scatter = ax6.scatter(monthly_win_rates, monthly_avg_returns, 
                                 s=150, alpha=0.7, c=range(len(months)), cmap='tab10')
            
            # 添加月份标签
            for i, (wr, ret, label) in enumerate(zip(monthly_win_rates, monthly_avg_returns, month_labels)):
                ax6.annotate(label, (wr, ret), xytext=(5, 5), textcoords='offset points', 
                           fontsize=10, alpha=0.8)
            
            # 添加象限分割线
            ax6.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax6.axvline(x=0.5, color='black', linestyle='-', alpha=0.3)
            
            # 添加象限标签
            ax6.text(0.75, max(monthly_avg_returns)*0.8, '高胜率\n高收益', 
                    ha='center', va='center', fontsize=12, 
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen", alpha=0.5))
            ax6.text(0.25, max(monthly_avg_returns)*0.8, '低胜率\n高收益', 
                    ha='center', va='center', fontsize=12,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.5))
            ax6.text(0.75, min(monthly_avg_returns)*0.8, '高胜率\n低收益', 
                    ha='center', va='center', fontsize=12,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="orange", alpha=0.5))
            ax6.text(0.25, min(monthly_avg_returns)*0.8, '低胜率\n低收益', 
                    ha='center', va='center', fontsize=12,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightcoral", alpha=0.5))
            
            ax6.set_xlabel('月度胜率')
            ax6.set_ylabel('月度平均收益率')
            
            # 构建标题，包含标的信息
            title_etfs = "、".join([str(etf) for etf in selected_etfs[:3]])  # 显示前3个，避免标题过长
            if len(selected_etfs) > 3:
                title_etfs += f"等{len(selected_etfs)}只ETF"
            ax6.set_title(f'{title_etfs} - 各月胜率与收益关系图')
            ax6.grid(True, alpha=0.3)
            ax6.set_xlim(0, 1)
            
            st.pyplot(fig6)
            
            # 找出胜率最高和最低的月份
            best_month = max(summary_stats.items(), key=lambda x: x[1]['月度胜率'])
            worst_month = min(summary_stats.items(), key=lambda x: x[1]['月度胜率'])
            
            # 找出收益最高和最低的月份
            best_return_month = max(summary_stats.items(), key=lambda x: x[1]['月度平均收益'])
            worst_return_month = min(summary_stats.items(), key=lambda x: x[1]['月度平均收益'])
            
            st.markdown(f"""
            **🎯 关键发现：**
            - **胜率最高的月份**：{month_names[best_month[0]]}（月度胜率：{best_month[1]['月度胜率']:.1%}）
            - **胜率最低的月份**：{month_names[worst_month[0]]}（月度胜率：{worst_month[1]['月度胜率']:.1%}）
            - **收益最高的月份**：{month_names[best_return_month[0]]}（平均收益：{best_return_month[1]['月度平均收益']:.2%}）
            - **收益最低的月份**：{month_names[worst_return_month[0]]}（平均收益：{worst_return_month[1]['月度平均收益']:.2%}）
            
            **📈 投资建议：**
            - 可以考虑在{month_names[best_month[0]]}加大投资力度（历史胜率较高）
            - 在{month_names[worst_month[0]]}保持谨慎或适当减仓（历史胜率较低）
            - 结合胜率和收益数据制定月度投资策略
            """)