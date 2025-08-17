import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
from data import get_etf_list, fetch_etf_data_with_retry
from utils import get_etf_options_with_favorites, get_favorite_etfs

st.set_page_config(page_title="周度涨跌分析", page_icon="📅", layout="wide")
st.title("📅 周度涨跌分析")

st.markdown("""
> 将每月分为四个周，分析每月的第一周、第二周、第三周、第四周的涨跌情况。
> 帮助识别哪一周最容易上涨，哪一周最容易下跌。
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

run_btn = st.button("运行周度涨跌分析")

def get_week_of_month_improved(date):
    """改进的周度划分：按每月天数平均分配"""
    day_of_month = date.day
    # 简单按日期划分：1-7日为第1周，8-14日为第2周，15-21日为第3周，22-月末为第4周
    if day_of_month <= 7:
        return 1
    elif day_of_month <= 14:
        return 2
    elif day_of_month <= 21:
        return 3
    else:
        return 4

def analyze_weekly_returns(df):
    """分析每周的涨跌情况"""
    df = df.sort_index()
    df['pct_change'] = df.iloc[:, 0].pct_change()
    df['date'] = df.index.date
    # 使用改进的周度划分
    df['week_of_month'] = df['date'].apply(get_week_of_month_improved)
    
    weekly_stats = {}
    for week in range(1, 5):
        week_data = df[df['week_of_month'] == week]
        if len(week_data) == 0:
            continue
            
        returns = week_data['pct_change'].dropna()
        if len(returns) == 0:
            continue
            
        up_days = np.sum(returns > 0)
        down_days = np.sum(returns < 0)
        flat_days = np.sum(returns == 0)
        total_days = len(returns)
        
        weekly_stats[week] = {
            '总天数': total_days,
            '上涨天数': up_days,
            '下跌天数': down_days,
            '平盘天数': flat_days,
            '上涨占比': up_days / total_days if total_days > 0 else 0,
            '下跌占比': down_days / total_days if total_days > 0 else 0,
            '平盘占比': flat_days / total_days if total_days > 0 else 0,
            '平均收益': np.mean(returns),
            '最大涨幅': np.max(returns),
            '最大跌幅': np.min(returns),
            '收益标准差': np.std(returns)
        }
    
    # 添加调试信息（移到这里）
    st.write("**调试信息：**")
    for week in range(1, 5):
        week_data = df[df['week_of_month'] == week]
        if len(week_data) > 0:
            st.write(f"第{week}周：{len(week_data)}个交易日，日期范围：{week_data.index.min().date()} 到 {week_data.index.max().date()}")
    
    return weekly_stats

if run_btn:
    if not selected_etfs:
        st.warning("请至少选择1只ETF")
        st.stop()
    
    all_weekly_stats = {}
    
    for symbol in selected_etfs:
        name = all_etfs.get(symbol, symbol)
        df = fetch_etf_data_with_retry(symbol, pd.to_datetime(start_date), pd.to_datetime(end_date), etf_list)
        if df.empty or len(df) < 30:
            st.warning(f"{symbol} - {name} 数据不足，跳过")
            continue
        
        weekly_stats = analyze_weekly_returns(df)
        all_weekly_stats[symbol] = weekly_stats
        
        # 显示每个ETF的周度统计
        st.subheader(f"📊 {symbol} - {name} 周度统计")
        
        if weekly_stats:
            # 创建统计表格
            stats_data = []
            for week, stats in weekly_stats.items():
                stats_data.append({
                    '周次': f'第{week}周',
                    '总天数': stats['总天数'],
                    '上涨天数': stats['上涨天数'],
                    '下跌天数': stats['下跌天数'],
                    '平盘天数': stats['平盘天数'],
                    '上涨占比': f"{stats['上涨占比']:.1%}",
                    '下跌占比': f"{stats['下跌占比']:.1%}",
                    '平盘占比': f"{stats['平盘占比']:.1%}",
                    '平均收益': f"{stats['平均收益']:.2%}",
                    '最大涨幅': f"{stats['最大涨幅']:.2%}",
                    '最大跌幅': f"{stats['最大跌幅']:.2%}",
                    '收益标准差': f"{stats['收益标准差']:.2%}"
                })
            
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True)
            
            # 新增：累计收益趋势图
            st.subheader(f"📈 {symbol} - {name} 累计收益趋势图")
            
            # 确保df有week_of_month列
            df_processed = df.copy()
            df_processed['pct_change'] = df_processed.iloc[:, 0].pct_change()
            df_processed['date'] = df_processed.index.date
            df_processed['week_of_month'] = df_processed['date'].apply(get_week_of_month_improved)
            
            # 计算标的累计收益
            price_series = df_processed.iloc[:, 0]
            buyhold_cum_returns = ((price_series / price_series.iloc[0]) - 1) * 100
            
            # 计算每周累计收益
            weekly_cum_returns = {}
            for week in range(1, 5):
                week_data = df_processed[df_processed['week_of_month'] == week]
                if len(week_data) > 0:
                    # 确保日期和收益数据对应
                    week_data_clean = week_data.dropna(subset=['pct_change'])
                    if len(week_data_clean) > 0:
                        week_returns = week_data_clean['pct_change']
                        # 计算该周的累计收益
                        cum_returns = (1 + week_returns).cumprod() - 1
                        weekly_cum_returns[week] = {
                            'dates': week_data_clean.index,
                            'returns': cum_returns * 100  # 转换为百分比
                        }
            
            # 绘制趋势图
            fig_trend = go.Figure()
            
            # 绘制标的累计收益
            fig_trend.add_trace(go.Scatter(x=buyhold_cum_returns.index, y=buyhold_cum_returns.values, 
                                           mode='lines', line=dict(width=2, color='black'), 
                                           name='标的累计收益', opacity=0.8))
            
            # 绘制每周累计收益
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
            week_names = ['第1周', '第2周', '第3周', '第4周']
            
            for week in range(1, 5):
                if week in weekly_cum_returns:
                    fig_trend.add_trace(go.Scatter(x=weekly_cum_returns[week]['dates'], 
                                                   y=weekly_cum_returns[week]['returns'],
                                                   mode='lines', line=dict(width=1.5, color=colors[week-1]), 
                                                   name=f'{week_names[week-1]}累计收益', opacity=0.7))
            
            # 添加零线
            fig_trend.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray", opacity=0.5)
            
            fig_trend.update_layout(
                title=f'{symbol} - {name} 标的vs各周累计收益趋势',
                xaxis_title='日期',
                yaxis_title='累计收益率 (%)',
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=500,
                hovermode='x unified'
            )
            
            # 设置x轴日期格式
            fig_trend.update_xaxes(tickangle=45)
            
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # 可视化
            col1, col2 = st.columns(2)
            
            with col1:
                # 上涨占比柱状图
                weeks = list(weekly_stats.keys())
                up_ratios = [weekly_stats[w]['上涨占比'] for w in weeks]
                down_ratios = [weekly_stats[w]['下跌占比'] for w in weeks]
                
                # 创建分组柱状图
                fig1 = go.Figure()
                
                # 添加上涨占比
                fig1.add_trace(go.Bar(
                    x=[f'第{w}周' for w in weeks],
                    y=up_ratios,
                    name='上涨占比',
                    marker_color='green',
                    opacity=0.7
                ))
                
                # 添加下跌占比
                fig1.add_trace(go.Bar(
                    x=[f'第{w}周' for w in weeks],
                    y=down_ratios,
                    name='下跌占比',
                    marker_color='red',
                    opacity=0.7
                ))
                
                fig1.update_layout(
                    title=f'{symbol} - {name} 各周涨跌占比',
                    xaxis_title='周次',
                    yaxis_title='占比',
                    barmode='group',
                    showlegend=True,
                    height=400,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # 平均收益柱状图
                avg_returns = [weekly_stats[w]['平均收益'] for w in weeks]
                
                # 创建柱状图
                fig2 = go.Figure()
                
                # 根据收益值选择颜色
                colors = ['green' if r > 0 else 'red' for r in avg_returns]
                
                fig2.add_trace(go.Bar(
                    x=[f'第{w}周' for w in weeks],
                    y=avg_returns,
                    name='平均收益',
                    marker_color=colors,
                    opacity=0.7
                ))
                
                # 添加零线
                fig2.add_hline(y=0, line_width=1, line_dash="dash", line_color="black", opacity=0.5, annotation_text="零线")
                
                fig2.update_layout(
                    title=f'{symbol} - {name} 各周平均收益',
                    xaxis_title='周次',
                    yaxis_title='平均收益率',
                    showlegend=True,
                    height=400,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info(f"{symbol} - {name} 暂无有效数据")
        
        st.markdown("---")
    
    # 汇总统计
    if all_weekly_stats:
        st.subheader("📈 汇总统计")
        
        # 计算所有ETF的汇总统计
        summary_stats = {}
        for week in range(1, 5):
            total_up = 0
            total_down = 0
            total_flat = 0
            total_days = 0
            all_returns = []
            
            for symbol, weekly_stats in all_weekly_stats.items():
                if week in weekly_stats:
                    stats = weekly_stats[week]
                    total_up += stats['上涨天数']
                    total_down += stats['下跌天数']
                    total_flat += stats['平盘天数']
                    total_days += stats['总天数']
                    # 这里简化处理，实际应该收集所有收益率数据
                    all_returns.append(stats['平均收益'])
            
            if total_days > 0:
                summary_stats[week] = {
                    '总天数': total_days,
                    '上涨天数': total_up,
                    '下跌天数': total_down,
                    '平盘天数': total_flat,
                    '上涨占比': total_up / total_days,
                    '下跌占比': total_down / total_days,
                    '平盘占比': total_flat / total_days,
                    '平均收益': np.mean(all_returns) if all_returns else 0
                }
        
        if summary_stats:
            # 创建汇总表格
            summary_data = []
            for week, stats in summary_stats.items():
                summary_data.append({
                    '周次': f'第{week}周',
                    '总天数': stats['总天数'],
                    '上涨天数': stats['上涨天数'],
                    '下跌天数': stats['下跌天数'],
                    '平盘天数': stats['平盘天数'],
                    '上涨占比': f"{stats['上涨占比']:.1%}",
                    '下跌占比': f"{stats['下跌占比']:.1%}",
                    '平盘占比': f"{stats['平盘占比']:.1%}",
                    '平均收益': f"{stats['平均收益']:.2%}"
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
            
            # 汇总可视化
            col1, col2 = st.columns(2)
            
            with col1:
                # 上涨占比对比
                weeks = list(summary_stats.keys())
                up_ratios = [summary_stats[w]['上涨占比'] for w in weeks]
                
                fig3 = px.bar(x=weeks, y=up_ratios, color=up_ratios, 
                              labels={'x':'周次', 'y':'上涨占比'}, 
                              title='各周上涨占比汇总', 
                              color_continuous_scale=['green', 'orange'])
                fig3.update_layout(showlegend=True, legend_orientation="h", 
                                   legend=dict(yanchor="bottom", y=1.02, xanchor="right", x=1), 
                                   yaxis_title="上涨占比")
                fig3.add_hline(y=0.5, line_dash="dash", line_color="red", 
                               annotation_text="50%基准线", annotation_position="bottom right")
                st.plotly_chart(fig3, use_container_width=True)
            
            with col2:
                # 平均收益对比
                avg_returns = [summary_stats[w]['平均收益'] for w in weeks]
                
                fig4 = px.bar(x=weeks, y=avg_returns, color=avg_returns, 
                              labels={'x':'周次', 'y':'平均收益率'}, 
                              title='各周平均收益汇总', 
                              color_continuous_scale=['green', 'red'])
                fig4.update_layout(showlegend=True, legend_orientation="h", 
                                   legend=dict(yanchor="bottom", y=1.02, xanchor="right", x=1), 
                                   yaxis_title="平均收益率")
                fig4.add_hline(y=0, line_dash="dash", line_color="black", 
                               annotation_text="0%基准线", annotation_position="bottom right")
                st.plotly_chart(fig4, use_container_width=True)
            
            # 找出最容易涨和最容易跌的周
            best_week = max(summary_stats.items(), key=lambda x: x[1]['上涨占比'])
            worst_week = min(summary_stats.items(), key=lambda x: x[1]['上涨占比'])
            
            st.markdown(f"""
            **🎯 关键发现：**
            - **最容易上涨的周**：第{best_week[0]}周（上涨占比：{best_week[1]['上涨占比']:.1%}）
            - **最容易下跌的周**：第{worst_week[0]}周（上涨占比：{worst_week[1]['上涨占比']:.1%}）
            """) 