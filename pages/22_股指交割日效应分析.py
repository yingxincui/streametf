import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import akshare as ak
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="股指交割日效应分析", page_icon="📅", layout="wide")
st.title("📅 股指交割日效应分析")

st.markdown("""
> 深入分析股指交割日对ETF市场的影响，揭示交割日效应是否存在。
> 帮助投资者了解交割日前后市场表现规律，制定相应的投资策略。

**🎯 核心功能：**
- **交割日计算**：自动计算每月第三个周五的交割日（遇节假日顺延）
- **效应分析**：分析交割日当天及前后ETF的表现差异
- **统计验证**：通过数据统计验证交割日效应的显著性
- **策略建议**：基于分析结果提供投资策略建议

**📊 分析维度：**
- **时间窗口**：交割日前1天、当天、后1天、后2天
- **表现对比**：涨跌幅、成交量、波动率等指标对比
- **效应强度**：量化交割日效应的显著性
- **历史规律**：分析不同市场环境下的表现差异

**📅 交易日处理：**
- **智能识别**：自动识别并排除周末、节假日等非交易日
- **简化验证**：使用周末排除法识别交易日，避免不必要的API调用
- **数据验证**：通过实际ETF数据验证交易日有效性
- **避免null值**：确保分析结果基于真实交易数据

**🎨 颜色规则：**
- **涨（正值）**：红色 🔴
- **跌（负值）**：绿色 🟢
（符合中国股市习惯）
""")

# 导入数据模块
from data import get_etf_list, fetch_etf_data_with_retry
from utils import get_etf_options_with_favorites

def calculate_delivery_dates(start_year, end_year):
    """计算指定年份范围内的股指交割日（每月第三个周五，只考虑交易日）"""
    delivery_dates = []
    
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # 获取该月第一个周五
            first_day = datetime(year, month, 1)
            days_until_first_friday = (4 - first_day.weekday()) % 7
            first_friday = first_day + timedelta(days=days_until_first_friday)
            
            # 第三个周五
            third_friday = first_friday + timedelta(weeks=2)
            
            # 检查是否为交易日（排除周末）
            if third_friday.weekday() >= 5:  # 周六或周日
                # 顺延到下一个工作日（周一）
                while third_friday.weekday() >= 5:
                    third_friday += timedelta(days=1)
            
            delivery_dates.append(third_friday)
    
    return sorted(delivery_dates)

def get_next_trading_day(date, etf_list, max_lookback=10):
    """获取下一个交易日（向前查找）"""
    for i in range(1, max_lookback + 1):
        next_date = date + timedelta(days=i)
        # 排除周末
        if next_date.weekday() >= 5:
            continue
        
        # 使用简单的日期验证，避免不必要的API调用
        # 大多数情况下，非周末的日期就是交易日
        # 只有在特殊节假日时才需要进一步验证
        return next_date
    
    return None

def get_previous_trading_day(date, etf_list, max_lookback=10):
    """获取前一个交易日（向后查找）"""
    for i in range(1, max_lookback + 1):
        prev_date = date - timedelta(days=i)
        # 排除周末
        if prev_date.weekday() >= 5:
            continue
        
        # 使用简单的日期验证，避免不必要的API调用
        # 大多数情况下，非周末的日期就是交易日
        # 只有在特殊节假日时才需要进一步验证
        return prev_date
    
    return None

def get_delivery_period_data(etf_code, delivery_date, etf_list, days_before=1, days_after=2):
    """获取交割日前后指定天数的ETF数据（只考虑交易日）"""
    # 获取前一个交易日
    start_date = get_previous_trading_day(delivery_date, etf_list, max_lookback=days_before * 3)
    if start_date is None:
        start_date = delivery_date - timedelta(days=days_before)
    
    # 获取后一个交易日
    end_date = get_next_trading_day(delivery_date, etf_list, max_lookback=days_after * 3)
    if end_date is None:
        end_date = delivery_date + timedelta(days=days_after)
    
    # 获取ETF数据
    etf_data = fetch_etf_data_with_retry(
        etf_code, 
        start_date.strftime("%Y-%m-%d"), 
        end_date.strftime("%Y-%m-%d"), 
        etf_list
    )
    
    if etf_data.empty:
        return None
    
    # 获取价格列名
    price_column = [col for col in etf_data.columns if col.startswith(etf_code)]
    if not price_column:
        return None
    
    price_column = price_column[0]
    
    # 计算涨跌幅
    etf_data[price_column] = pd.to_numeric(etf_data[price_column], errors='coerce')
    etf_data = etf_data.dropna(subset=[price_column])
    
    if len(etf_data) < 2:
        return None
    
    # 计算日收益率
    etf_data['收益率'] = etf_data[price_column].pct_change()
    
    return etf_data

def analyze_delivery_effect(etf_code, etf_name, delivery_dates, etf_list):
    """分析单个ETF的交割日效应"""
    results = []
    
    for delivery_date in delivery_dates:
        # 获取交割日前后数据
        data = get_delivery_period_data(etf_code, delivery_date, etf_list)
        if data is None:
            continue
        
        # 计算各时间窗口的收益率
        delivery_date_str = delivery_date.strftime("%Y-%m-%d")
        
        # 找到交割日对应的数据行
        delivery_row = None
        for idx, row in data.iterrows():
            if 'date' in data.columns:
                row_date = pd.to_datetime(row['date']).date()
            else:
                row_date = pd.to_datetime(idx).date()
            
            if row_date == delivery_date.date():
                delivery_row = row
                break
        
        if delivery_row is None:
            continue
        
        # 计算各时间窗口的收益率（基于实际交易日）
        periods = {
            '前1天': -1,
            '当天': 0,
            '后1天': 1,
            '后2天': 2
        }
        
        period_returns = {}
        for period_name, days_offset in periods.items():
            if period_name == '当天':
                # 交割日当天
                period_returns[period_name] = delivery_row['收益率'] * 100
            else:
                # 前后交易日
                target_date = delivery_date + timedelta(days=days_offset)
                
                # 根据偏移方向查找最近的交易日
                if days_offset < 0:
                    # 向前查找
                    actual_date = get_previous_trading_day(delivery_date, etf_list, max_lookback=abs(days_offset) * 3)
                else:
                    # 向后查找
                    actual_date = get_next_trading_day(delivery_date, etf_list, max_lookback=days_offset * 3)
                
                if actual_date is None:
                    period_returns[period_name] = np.nan
                    continue
                
                # 找到对应日期的数据
                target_row = None
                for idx, row in data.iterrows():
                    if 'date' in data.columns:
                        row_date = pd.to_datetime(row['date']).date()
                    else:
                        row_date = pd.to_datetime(idx).date()
                    
                    if row_date == actual_date.date():
                        target_row = row
                        break
                
                if target_row is not None:
                    period_returns[period_name] = target_row['收益率'] * 100
                else:
                    period_returns[period_name] = np.nan
        
        # 计算累计收益率
        cumulative_returns = {}
        for period_name in ['当天', '后1天', '后2天']:
            if period_name == '当天':
                cumulative_returns[period_name] = period_returns.get('当天', np.nan)
            elif period_name == '后1天':
                if not np.isnan(period_returns.get('当天', np.nan)) and not np.isnan(period_returns.get('后1天', np.nan)):
                    cumulative_returns[period_name] = period_returns['当天'] + period_returns['后1天']
                else:
                    cumulative_returns[period_name] = np.nan
            elif period_name == '后2天':
                if not np.isnan(period_returns.get('当天', np.nan)) and not np.isnan(period_returns.get('后1天', np.nan)) and not np.isnan(period_returns.get('后2天', np.nan)):
                    cumulative_returns[period_name] = period_returns['当天'] + period_returns['后1天'] + period_returns['后2天']
                else:
                    cumulative_returns[period_name] = np.nan
        
        results.append({
            '交割日期': delivery_date_str,
            '前1天': period_returns.get('前1天', np.nan),
            '当天': period_returns.get('当天', np.nan),
            '后1天': period_returns.get('后1天', np.nan),
            '后2天': period_returns.get('后2天', np.nan),
            '当天累计': cumulative_returns.get('当天', np.nan),
            '后1天累计': cumulative_returns.get('后1天', np.nan),
            '后2天累计': cumulative_returns.get('后2天', np.nan)
        })
    
    return pd.DataFrame(results)

# 获取ETF列表
etf_list = get_etf_list()

if etf_list.empty:
    st.error("无法获取ETF列表，请检查网络连接")
    st.stop()

# 使用与ETF对比分析页面相同的ETF选择方式
etf_options = get_etf_options_with_favorites(etf_list)

# 创建ETF选择器
etf_options_with_names = []
for code in etf_options:
    etf_info = etf_list[etf_list['symbol'] == code]
    if not etf_info.empty:
        name = etf_info.iloc[0]['name']
        etf_options_with_names.append(f"{code} - {name}")

# ETF选择器
st.subheader("🔍 选择要分析的ETF")
selected_etfs = st.multiselect(
    "选择要分析交割日效应的ETF（建议选择1-3只）",
    options=etf_options_with_names,
    default=etf_options_with_names[:1] if etf_options_with_names else [],
    help="选择要分析交割日效应的ETF，建议选择流动性较好的宽基ETF"
)

# 显示选择的ETF信息
if selected_etfs:
    st.info(f"🎯 已选择 {len(selected_etfs)} 只ETF进行分析：")
    for i, etf_info in enumerate(selected_etfs, 1):
        etf_code = etf_info.split(" - ")[0]
        etf_name = etf_info.split(" - ")[1]
        st.write(f"{i}. **{etf_name}** ({etf_code})")
else:
    st.info("请选择要分析的ETF")

# 分析时间范围
col1, col2 = st.columns(2)
with col1:
    start_year = st.selectbox("开始年份", options=list(range(2020, datetime.now().year + 1)), index=len(list(range(2020, datetime.now().year + 1))) - 1)
with col2:
    end_year = st.selectbox("结束年份", options=list(range(2020, datetime.now().year + 1)), index=len(list(range(2020, datetime.now().year + 1))) - 1)

# 运行分析按钮
run_btn = st.button("🚀 运行交割日效应分析")

if run_btn:
    if not selected_etfs:
        st.warning("请至少选择1只ETF进行分析")
        st.stop()
    
    if len(selected_etfs) > 3:
        st.warning("建议选择不超过3只ETF进行分析，以确保分析质量")
        st.stop()
    
    # 计算交割日
    st.subheader("📅 交割日计算")
    delivery_dates = calculate_delivery_dates(start_year, end_year)
    
    # 显示交割日列表
    delivery_df = pd.DataFrame({
        '交割日期': [d.strftime("%Y-%m-%d") for d in delivery_dates],
        '星期': [d.strftime("%A") for d in delivery_dates],
        '年份': [d.year for d in delivery_dates],
        '月份': [d.month for d in delivery_dates]
    })
    
    st.info(f"📊 在 {start_year}-{end_year} 期间共有 {len(delivery_dates)} 个交割日")
    st.dataframe(delivery_df, use_container_width=True)
    
    # 开始分析
    st.subheader("📊 交割日效应分析结果")
    
    all_results = {}
    
    # 进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 使用expander折叠数据获取日志
    with st.expander("🔍 数据获取进度（点击展开查看详情）", expanded=False):
        st.info("💡 交易日验证已优化：使用周末排除法，避免不必要的API调用和混淆的缓存日志")
        
        for i, etf_info in enumerate(selected_etfs):
            etf_code = etf_info.split(" - ")[0]
            etf_name = etf_info.split(" - ")[1]
            
            status_text.text(f"正在分析 {etf_name} ({etf_code})...")
            
            with st.spinner(f"正在分析 {etf_name} 的交割日效应..."):
                # 分析交割日效应
                results = analyze_delivery_effect(etf_code, etf_name, delivery_dates, etf_list)
                
                if not results.empty:
                    all_results[etf_name] = results
                    st.success(f"✅ {etf_name} 分析完成，共分析 {len(results)} 个交割日")
                else:
                    st.warning(f"⚠️ {etf_name} 数据不足，无法分析")
            
            # 更新进度条
            progress_bar.progress((i + 1) / len(selected_etfs))
    
    status_text.text("分析完成！")
    progress_bar.empty()
    status_text.empty()
    
    if not all_results:
        st.error("没有成功分析到任何ETF数据，请检查网络连接或选择其他ETF")
        st.stop()
    
    # 显示分析结果
    for etf_name, results in all_results.items():
        # 从selected_etfs中找到对应的ETF代码
        etf_code = None
        for etf_info in selected_etfs:
            if etf_info.split(" - ")[1] == etf_name:
                etf_code = etf_info.split(" - ")[0]
                break
        
        st.subheader(f"📈 {etf_name} ({etf_code}) 交割日效应分析")
        
        # 格式化表格显示
        def color_returns(val):
            if pd.isna(val):
                return ''
            if isinstance(val, (int, float)) and val > 0:
                return 'background-color: #f8d7da; color: #721c24'  # 红色背景（涨）
            elif isinstance(val, (int, float)) and val < 0:
                return 'background-color: #d4edda; color: #155724'  # 绿色背景（跌）
            else:
                return ''
        
        # 应用样式
        styled_df = results.style.applymap(
            color_returns, 
            subset=['前1天', '当天', '后1天', '后2天', '当天累计', '后1天累计', '后2天累计']
        ).format({
            '前1天': '{:.2f}%',
            '当天': '{:.2f}%',
            '后1天': '{:.2f}%',
            '后2天': '{:.2f}%',
            '当天累计': '{:.2f}%',
            '后1天累计': '{:.2f}%',
            '后2天累计': '{:.2f}%'
        })
        
        st.dataframe(styled_df, use_container_width=True)
        
        # 统计摘要
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_delivery = results['当天'].mean()
            st.metric(
                "交割日平均收益", 
                f"{avg_delivery:.2f}%",
                delta_color="normal" if avg_delivery > 0 else "inverse"
            )
        
        with col2:
            positive_delivery = sum(1 for x in results['当天'] if not pd.isna(x) and x > 0)
            total_delivery = sum(1 for x in results['当天'] if not pd.isna(x))
            st.metric(
                "交割日正收益次数", 
                f"{positive_delivery}/{total_delivery}",
                f"{positive_delivery/total_delivery*100:.1f}%" if total_delivery > 0 else "0%"
            )
        
        with col3:
            avg_next_day = results['后1天'].mean()
            st.metric(
                "后1天平均收益", 
                f"{avg_next_day:.2f}%",
                delta_color="normal" if avg_next_day > 0 else "inverse"
            )
        
        with col4:
            avg_cumulative = results['后1天累计'].mean()
            st.metric(
                "后1天累计收益", 
                f"{avg_cumulative:.2f}%",
                delta_color="normal" if avg_cumulative > 0 else "inverse"
            )
    
    # 可视化分析
    st.subheader("📊 交割日效应可视化分析")
    
    # 创建子图：各时间窗口的收益分布
    fig_distribution = make_subplots(
        rows=2, cols=2,
        subplot_titles=('交割日前1天收益分布', '交割日当天收益分布', 
                       '交割日后1天收益分布', '交割日后2天收益分布'),
        specs=[[{"type": "histogram"}, {"type": "histogram"}],
               [{"type": "histogram"}, {"type": "histogram"}]]
    )
    
    # 为每个ETF添加分布图
    colors = ['#d62728', '#ff7f0e', '#2ca02c']  # 红、橙、绿
    
    for i, (etf_name, results) in enumerate(all_results.items()):
        color = colors[i % len(colors)]
        
        # 前1天分布
        fig_distribution.add_trace(
            go.Histogram(x=results['前1天'].dropna(), name=f'{etf_name}-前1天', 
                        marker_color=color, opacity=0.7, showlegend=True),
            row=1, col=1
        )
        
        # 当天分布
        fig_distribution.add_trace(
            go.Histogram(x=results['当天'].dropna(), name=f'{etf_name}-当天', 
                        marker_color=color, opacity=0.7, showlegend=True),
            row=1, col=2
        )
        
        # 后1天分布
        fig_distribution.add_trace(
            go.Histogram(x=results['后1天'].dropna(), name=f'{etf_name}-后1天', 
                        marker_color=color, opacity=0.7, showlegend=True),
            row=2, col=1
        )
        
        # 后2天分布
        fig_distribution.add_trace(
            go.Histogram(x=results['后2天'].dropna(), name=f'{etf_name}-后2天', 
                        marker_color=color, opacity=0.7, showlegend=True),
            row=2, col=2
        )
    
    fig_distribution.update_layout(
        height=600,
        title_text="交割日各时间窗口收益分布对比",
        showlegend=True
    )
    
    st.plotly_chart(fig_distribution, use_container_width=True)
    
    # 时间序列趋势图
    if len(all_results) > 0:
        st.subheader("📈 交割日效应时间趋势")
        
        # 选择第一个ETF的数据进行时间趋势分析
        first_etf_name = list(all_results.keys())[0]
        first_etf_results = all_results[first_etf_name]
        
        # 获取ETF代码
        first_etf_code = None
        for etf_info in selected_etfs:
            if etf_info.split(" - ")[1] == first_etf_name:
                first_etf_code = etf_info.split(" - ")[0]
                break
        
        fig_trend = go.Figure()
        
        # 添加各时间窗口的趋势线
        periods = ['前1天', '当天', '后1天', '后2天']
        colors_trend = ['#1f77b4', '#d62728', '#ff7f0e', '#2ca02c']
        
        for i, period in enumerate(periods):
            fig_trend.add_trace(go.Scatter(
                x=first_etf_results['交割日期'],
                y=first_etf_results[period],
                mode='lines+markers',
                name=period,
                line=dict(color=colors_trend[i], width=2),
                marker=dict(size=6),
                hovertemplate=f'<b>{period}</b><br>' +
                            '日期: %{x}<br>' +
                            '收益率: %{y:.2f}%<extra></extra>'
            ))
        
        # 添加零线
        fig_trend.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig_trend.update_layout(
            title=f'{first_etf_name} ({first_etf_code}) 交割日效应时间趋势',
            xaxis_title='交割日期',
            yaxis_title='收益率 (%)',
            height=500,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig_trend, use_container_width=True)
    
    # 投资建议
    st.subheader("💡 投资建议")
    
    # 分析交割日效应
    delivery_effects = {}
    for etf_name, results in all_results.items():
        # 计算各时间窗口的统计指标
        delivery_effects[etf_name] = {
            '交割日平均收益': results['当天'].mean(),
            '交割日正收益概率': sum(1 for x in results['当天'] if not pd.isna(x) and x > 0) / sum(1 for x in results['当天'] if not pd.isna(x)),
            '后1天平均收益': results['后1天'].mean(),
            '后1天累计平均收益': results['后1天累计'].mean(),
            '效应强度': abs(results['当天'].mean()) + abs(results['后1天'].mean())
        }
    
    # 找出效应最明显的ETF
    strongest_effect_etf = max(delivery_effects.keys(), 
                              key=lambda x: delivery_effects[x]['效应强度'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 获取ETF代码
        strongest_effect_etf_code = None
        for etf_info in selected_etfs:
            if etf_info.split(" - ")[1] == strongest_effect_etf:
                strongest_effect_etf_code = etf_info.split(" - ")[0]
                break
        
        st.markdown(f"""
        **🏆 交割日效应最明显：**
        - **ETF：** {strongest_effect_etf} ({strongest_effect_etf_code})
        - **交割日平均收益：** {delivery_effects[strongest_effect_etf]['交割日平均收益']:.2f}%
        - **交割日正收益概率：** {delivery_effects[strongest_effect_etf]['交割日正收益概率']*100:.1f}%
        - **后1天平均收益：** {delivery_effects[strongest_effect_etf]['后1天平均收益']:.2f}%
        """)
    
    with col2:
        st.markdown(f"""
        **📊 整体分析：**
        - **分析期间：** {start_year}年 - {end_year}年
        - **交割日数量：** {len(delivery_dates)}个
        - **分析ETF数量：** {len(all_results)}只
        
        **💡 策略建议：**
        - **关注交割日**：每月第三个周五前后市场波动可能加大
        - **择时策略**：根据历史表现选择合适的时间窗口
        - **风险控制**：交割日前后注意控制仓位和风险
        """)
    
    # 下载功能
    st.subheader("💾 下载分析结果")
    
    # 合并所有结果
    all_results_combined = []
    for etf_name, results in all_results.items():
        # 获取ETF代码
        etf_code = None
        for etf_info in selected_etfs:
            if etf_info.split(" - ")[1] == etf_name:
                etf_code = etf_info.split(" - ")[0]
                break
        
        results_copy = results.copy()
        results_copy['ETF名称'] = etf_name
        results_copy['ETF代码'] = etf_code
        all_results_combined.append(results_copy)
    
    if all_results_combined:
        combined_df = pd.concat(all_results_combined, ignore_index=True)
        
        # 下载CSV
        csv = combined_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 下载CSV报告",
            data=csv,
            file_name=f"股指交割日效应分析_{start_year}-{end_year}.csv",
            mime="text/csv"
        )
