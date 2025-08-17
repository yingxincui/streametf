import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import akshare as ak
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="ETF对比分析", page_icon="📈", layout="wide")
st.title("📈 ETF对比分析")

st.markdown("""
> 全面对比分析ETF产品的收益、风险、流动性等多维度表现。
> 帮助投资者选择最适合的ETF产品，构建优质投资组合。

**🎯 核心功能：**
- **多维度对比**：收益、风险、流动性、费用全面分析
- **智能筛选**：按规模、费率、成立时间等条件筛选
- **可视化分析**：交互式图表展示对比结果
- **组合构建**：一键构建ETF投资组合
- **公平比较**：自动计算最短创立时间，确保不同ETF的公平对比

**📊 分析维度：**
- **收益分析**：绝对收益、相对收益、年化收益
- **风险分析**：波动率、最大回撤、夏普比率
- **流动性分析**：成交额、换手率、规模变化
- **费用分析**：管理费率、托管费率、总费率

**🎨 颜色规则：**
- **涨（正值）**：红色 🔴
- **跌（负值）**：绿色 🟢
（符合中国股市习惯）

**⚖️ 公平比较功能：**
- **智能时间计算**：自动识别所有ETF的创立时间
- **最短时间原则**：以最短创立时间为准进行分析
- **避免偏差**：防止因创立时间不同导致的比较偏差
- **灵活选择**：用户可选择是否启用公平比较
""")

# 导入数据模块
from data import get_etf_list, fetch_etf_data_with_retry
from utils import get_etf_options_with_favorites
from utils import get_favorite_etfs # Added missing import

def categorize_etf(name):
    """根据ETF名称进行分类"""
    name = str(name).lower()
    
    # 宽基ETF
    if any(keyword in name for keyword in ['沪深300', '中证500', '中证1000', '创业板', '科创50', '上证50']):
        return '宽基ETF'
    
    # 行业ETF
    elif any(keyword in name for keyword in ['科技', '医药', '消费', '金融', '地产', '能源', '材料', '工业']):
        return '行业ETF'
    
    # 主题ETF
    elif any(keyword in name for keyword in ['新能源', '芯片', '人工智能', 'ai', '5g', '军工', '环保', '农业']):
        return '主题ETF'
    
    # 海外ETF
    elif any(keyword in name for keyword in ['恒生', '纳指', '标普', '道指', '日经', '德国', '法国']):
        return '海外ETF'
    
    # 商品ETF
    elif any(keyword in name for keyword in ['黄金', '白银', '原油', '商品']):
        return '商品ETF'
    
    # 债券ETF
    elif any(keyword in name for keyword in ['债券', '国债', '信用债', '可转债']):
        return '债券ETF'
    
    else:
        return '其他ETF'

# 计算风险指标
def calculate_risk_metrics(returns):
    """计算风险指标"""
    if len(returns) < 2:
        return {
            'volatility': np.nan,
            'max_drawdown': np.nan,
            'sharpe_ratio': np.nan,
            'var_95': np.nan
        }
    
    # 波动率
    volatility = returns.std() * np.sqrt(252)  # 年化波动率
    
    # 最大回撤
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # 夏普比率 (假设无风险利率为3%)
    excess_returns = returns - 0.03/252
    sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else np.nan
    
    # VaR (95%置信度)
    var_95 = np.percentile(returns, 5)
    
    return {
        'volatility': volatility,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'var_95': var_95
    }

# 获取ETF列表
etf_list = get_etf_list()

if etf_list.empty:
    st.error("无法获取ETF列表，请检查网络连接")
    st.stop()

# 添加分类信息
etf_list['分类'] = etf_list['name'].apply(categorize_etf)

# 使用与定投页面相同的ETF选择方式
etf_options = get_etf_options_with_favorites(etf_list)

# 创建ETF选择器
etf_options_with_names = []
for code in etf_options:
    etf_info = etf_list[etf_list['symbol'] == code]
    if not etf_info.empty:
        name = etf_info.iloc[0]['name']
        category = etf_info.iloc[0]['分类']
        etf_options_with_names.append(f"{code} - {name} ({category})")

# ETF选择器
st.subheader("🔍 选择要对比的ETF")

# 直接使用所有ETF选项，不进行筛选
filtered_options = etf_options_with_names

# 初始化session_state
if 'selected_etfs' not in st.session_state:
    st.session_state.selected_etfs = filtered_options[:3] if filtered_options else []

# 确保默认值在可选项范围内
default_selection = []
if filtered_options:
    # 优先选择自选ETF
    favorite_etfs = get_favorite_etfs()
    if favorite_etfs:
        # 从自选ETF中选择前3个在可选项中的
        for fav in favorite_etfs:
            if len(default_selection) >= 3:
                break
            # 查找自选ETF在可选项中的完整信息
            for option in filtered_options:
                if option.startswith(fav + " - "):
                    default_selection.append(option)
                    break
    
    # 如果自选ETF不足3个，从所有可选项中补充
    if len(default_selection) < 3:
        for option in filtered_options:
            if option not in default_selection:
                default_selection.append(option)
                if len(default_selection) >= 3:
                    break
    
    # 更新session_state
    st.session_state.selected_etfs = default_selection

# ETF选择器 - 使用multiselect下拉选择器
# 确保默认值在可选项中
valid_defaults = [etf for etf in st.session_state.selected_etfs if etf in filtered_options]
if not valid_defaults and filtered_options:
    valid_defaults = filtered_options[:3]

selected_etfs = st.multiselect(
    "选择要对比的ETF（可多选）",
    options=filtered_options,
    default=valid_defaults,
    key="etf_selector",
    help="选择要对比分析的ETF，建议选择3-5只进行对比。自选ETF会优先显示。"
)

# 分析时间范围
col1, col2 = st.columns(2)
with col1:
    end_date = st.date_input("结束日期", value=datetime.now(), max_value=datetime.now())
with col2:
    time_period = st.selectbox(
        "分析时间范围", 
        options=["创立以来", "5年", "3年", "2年", "1年", "6个月", "3个月"], 
        index=0,  # 默认选择"创立以来"
        help="选择分析的时间范围"
    )

# 公平比较选项
fair_comparison = st.checkbox(
    "🎯 启用公平比较（以最短创立时间为准）", 
    value=True,
    help="启用后，系统会自动计算所有选中ETF的最短创立时间，确保比较的公平性。建议在分析不同创立时间的ETF时启用。"
)

# 根据选择的时间范围计算开始日期
if time_period == "创立以来":
    # 对于创立以来，我们将在数据获取时处理
    start_date = None
    start_date_str = None
else:
    # 解析时间范围
    if "年" in time_period:
        years = int(time_period.replace("年", ""))
        start_date = end_date - timedelta(days=years * 365)
    elif "个月" in time_period:
        months = int(time_period.replace("个月", ""))
        start_date = end_date - timedelta(days=months * 30)
    else:
        start_date = end_date - timedelta(days=365)  # 默认1年
    
    start_date_str = start_date.strftime("%Y-%m-%d")

end_date_str = end_date.strftime("%Y-%m-%d")

# 运行分析按钮
run_btn = st.button("🚀 运行ETF对比分析")

if run_btn:
    if not selected_etfs:
        st.warning("请至少选择1只ETF进行分析")
        st.stop()
    
    if len(selected_etfs) > 10:
        st.warning("建议选择不超过10只ETF进行分析，以确保分析质量")
        st.stop()
    
    # 开始分析
    st.subheader("📊 ETF对比分析结果")
    
    analysis_results = []
    # 收集时间序列数据用于绘制趋势图
    time_series_data = {}
    
    # 进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 使用expander折叠数据获取日志
    with st.expander("🔍 数据获取进度（点击展开查看详情）", expanded=False):
        # 如果启用公平比较且选择"创立以来"，先获取所有ETF的创立时间
        if fair_comparison and start_date_str is None:
            st.info("🔍 正在计算公平比较时间范围...")
            etf_start_dates = {}
            
            for etf_info in selected_etfs:
                etf_code = etf_info.split(" - ")[0]
                etf_name = etf_info.split(" - ")[1].split(" (")[0]
                
                with st.spinner(f"正在获取 {etf_name} 创立时间..."):
                    # 获取ETF数据来确定创立时间
                    etf_data = fetch_etf_data_with_retry(etf_code, None, end_date_str, etf_list)
                    
                    if not etf_data.empty:
                        # 获取价格列名
                        price_column = [col for col in etf_data.columns if col.startswith(etf_code)]
                        if price_column:
                            price_column = price_column[0]
                            etf_data[price_column] = pd.to_numeric(etf_data[price_column], errors='coerce')
                            etf_data = etf_data.dropna(subset=[price_column])
                            
                            if len(etf_data) > 0:
                                # 确定创立时间
                                if 'date' in etf_data.columns:
                                    actual_start = pd.to_datetime(etf_data['date'].iloc[0])
                                elif etf_data.index.name in ['日期', 'date']:
                                    actual_start = pd.to_datetime(etf_data.index[0])
                                else:
                                    actual_start = pd.to_datetime(end_date) - timedelta(days=365)
                                
                                etf_start_dates[etf_name] = actual_start
                                st.success(f"✅ {etf_name} 创立时间: {actual_start.strftime('%Y-%m-%d')}")
            
            # 计算最短创立时间
            if etf_start_dates:
                earliest_start = max(etf_start_dates.values())
                st.success(f"🎯 公平比较起始时间: {earliest_start.strftime('%Y-%m-%d')} (以最短创立时间为准)")
                
                # 更新start_date_str用于后续分析
                start_date_str = earliest_start.strftime("%Y-%m-%d")
                start_date = earliest_start
        
        # 开始正式分析
        for i, etf_info in enumerate(selected_etfs):
            etf_code = etf_info.split(" - ")[0]
            etf_name = etf_info.split(" - ")[1].split(" (")[0]
            etf_category = etf_info.split("(")[1].split(")")[0]
            
            status_text.text(f"正在分析 {etf_name} ({etf_code})...")
            
            with st.spinner(f"正在获取 {etf_name} 数据..."):
                # 使用与定投回测相同的数据获取接口
                if start_date_str is None:
                    # 创立以来的情况，不指定开始日期，获取所有可用数据
                    etf_data = fetch_etf_data_with_retry(etf_code, None, end_date_str, etf_list)
                else:
                    etf_data = fetch_etf_data_with_retry(etf_code, start_date_str, end_date_str, etf_list)
            
            if etf_data.empty:
                st.warning(f"⚠️ {etf_name} 数据获取失败，跳过")
                continue
            
            # 获取价格数据列名
            price_column = [col for col in etf_data.columns if col.startswith(etf_code)][0]
            
            # 计算收益率
            etf_data[price_column] = pd.to_numeric(etf_data[price_column], errors='coerce')
            etf_data = etf_data.dropna(subset=[price_column])
            
            if len(etf_data) < 2:
                st.warning(f"⚠️ {etf_name} 数据不足，跳过")
                continue
            
            # 计算日收益率
            etf_data['收益率'] = etf_data[price_column].pct_change()
            returns = etf_data['收益率'].dropna()
            
            # 计算累计收益
            total_return = (etf_data[price_column].iloc[-1] / etf_data[price_column].iloc[0] - 1) * 100
            
            # 计算年化收益
            if start_date_str is None:
                # 创立以来的情况，使用数据的实际时间范围
                if 'date' in etf_data.columns:
                    actual_start = pd.to_datetime(etf_data['date'].iloc[0])
                elif etf_data.index.name in ['日期', 'date']:
                    actual_start = pd.to_datetime(etf_data.index[0])
                else:
                    # 如果没有明确的日期信息，使用默认值
                    actual_start = pd.to_datetime(end_date) - timedelta(days=365)
                
                # 确保类型一致，都转换为pandas.Timestamp
                end_date_ts = pd.to_datetime(end_date)
                days = (end_date_ts - actual_start).days
            else:
                # 确保类型一致，都转换为pandas.Timestamp
                end_date_ts = pd.to_datetime(end_date)
                start_date_ts = pd.to_datetime(start_date)
                days = (end_date_ts - start_date_ts).days
            
            # 确保天数至少为1
            days = max(days, 1)
            annual_return = ((etf_data[price_column].iloc[-1] / etf_data[price_column].iloc[0]) ** (365/days) - 1) * 100
            
            # 计算风险指标
            risk_metrics = calculate_risk_metrics(returns)
            
            # 收集时间序列数据用于趋势图
            if 'date' in etf_data.columns:
                # 计算累计涨跌幅
                etf_data['累计涨跌幅'] = (etf_data[price_column] / etf_data[price_column].iloc[0] - 1) * 100
                time_series_data[etf_name] = {
                    'dates': etf_data['date'],
                    'cumulative_returns': etf_data['累计涨跌幅']
                }
            elif etf_data.index.name == '日期' or etf_data.index.name == 'date':
                # 如果索引是日期，使用索引作为日期
                etf_data['累计涨跌幅'] = (etf_data[price_column] / etf_data[price_column].iloc[0] - 1) * 100
                time_series_data[etf_name] = {
                    'dates': etf_data.index,
                    'cumulative_returns': etf_data['累计涨跌幅']
                }
            elif len(etf_data) > 0:
                # 如果没有明确的日期列，创建一个基于行数的日期序列
                if start_date_str is not None:
                    start_date_obj = pd.to_datetime(start_date_str)
                else:
                    # 创立以来的情况，使用数据的实际开始日期
                    if 'date' in etf_data.columns:
                        start_date_obj = pd.to_datetime(etf_data['date'].iloc[0])
                    elif etf_data.index.name in ['日期', 'date']:
                        start_date_obj = pd.to_datetime(etf_data.index[0])
                    else:
                        # 如果没有明确的日期信息，使用默认值
                        start_date_obj = pd.to_datetime(end_date) - timedelta(days=365)
                
                date_range = pd.date_range(start=start_date_obj, periods=len(etf_data), freq='D')
                etf_data['累计涨跌幅'] = (etf_data[price_column] / etf_data[price_column].iloc[0] - 1) * 100
                time_series_data[etf_name] = {
                    'dates': date_range,
                    'cumulative_returns': etf_data['累计涨跌幅']
                }
            
            # 存储结果
            result = {
                'ETF代码': etf_code,
                'ETF名称': etf_name,
                '分类': etf_category,
                '累计收益(%)': round(total_return, 2),
                '年化收益(%)': round(annual_return, 2),
                '波动率(%)': round(risk_metrics['volatility'] * 100, 2) if not np.isnan(risk_metrics['volatility']) else "N/A",
                '最大回撤(%)': round(risk_metrics['max_drawdown'] * 100, 2) if not np.isnan(risk_metrics['max_drawdown']) else "N/A",
                '夏普比率': round(risk_metrics['sharpe_ratio'], 3) if not np.isnan(risk_metrics['sharpe_ratio']) else "N/A",
                'VaR(%)': round(risk_metrics['var_95'] * 100, 2) if not np.isnan(risk_metrics['var_95']) else "N/A",
                '数据点数': len(etf_data)
            }
            
            analysis_results.append(result)
            
            # 更新进度条
            progress_bar.progress((i + 1) / len(selected_etfs))
    
    status_text.text("分析完成！")
    progress_bar.empty()
    status_text.empty()
    
    if not analysis_results:
        st.error("没有成功获取到任何ETF数据，请检查网络连接或选择其他ETF")
        st.stop()
    
    # 显示分析结果
    st.subheader("📋 ETF对比结果表格")
    
    # 创建结果DataFrame
    results_df = pd.DataFrame(analysis_results)
    
    # 格式化表格显示
    def color_returns(val):
        if isinstance(val, (int, float)) and val > 0:
            return 'background-color: #f8d7da; color: #721c24'  # 红色背景（涨）
        elif isinstance(val, (int, float)) and val < 0:
            return 'background-color: #d4edda; color: #155724'  # 绿色背景（跌）
        else:
            return ''
    
    # 应用样式
    styled_df = results_df.style.applymap(
        color_returns, 
        subset=['累计收益(%)', '年化收益(%)']
    ).format({
        '累计收益(%)': '{:.2f}%',
        '年化收益(%)': '{:.2f}%',
        '波动率(%)': '{:.2f}%',
        '最大回撤(%)': '{:.2f}%',
        '夏普比率': '{:.3f}',
        'VaR(%)': '{:.2f}%'
    })
    
    st.dataframe(styled_df, use_container_width=True)
    
    # 快速统计
    st.subheader("📊 快速统计")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_return = results_df['累计收益(%)'].mean()
        st.metric(
            "平均累计收益", 
            f"{avg_return:.2f}%",
            delta_color="normal" if avg_return > 0 else "inverse"
        )
    
    with col2:
        avg_annual = results_df['年化收益(%)'].mean()
        st.metric(
            "平均年化收益", 
            f"{avg_annual:.2f}%",
            delta_color="normal" if avg_annual > 0 else "inverse"
        )
    
    with col3:
        best_return = results_df['累计收益(%)'].max()
        best_etf = results_df.loc[results_df['累计收益(%)'].idxmax(), 'ETF名称']
        st.metric(
            "最佳表现", 
            f"{best_return:.2f}%",
            best_etf
        )
    
    with col4:
        positive_count = sum(1 for x in results_df['累计收益(%)'] if x > 0)
        st.metric(
            "正收益数量", 
            f"{positive_count}/{len(results_df)}",
            f"{positive_count/len(results_df)*100:.1f}%"
        )
    
    # 可视化分析
    st.subheader("📈 可视化分析")
    
    # 创建结果DataFrame用于可视化
    viz_df = pd.DataFrame(analysis_results)
    
    # 第一行：涨跌幅趋势图（全宽）
    if time_series_data:
        st.subheader("📈 ETF涨跌幅趋势图")
        
        # 创建涨跌幅趋势图
        fig_trend = go.Figure()
        
        # 定义颜色列表
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                 '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        for i, (etf_name, data) in enumerate(time_series_data.items()):
            # 确保日期格式正确
            dates = pd.to_datetime(data['dates'])
            cumulative_returns = data['cumulative_returns']
            
            # 添加趋势线
            fig_trend.add_trace(go.Scatter(
                x=dates,
                y=cumulative_returns,
                mode='lines',
                name=etf_name,
                line=dict(color=colors[i % len(colors)], width=2),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '日期: %{x}<br>' +
                            '累计涨跌幅: %{y:.2f}%<extra></extra>'
            ))
        
        # 添加零线
        fig_trend.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        # 更新布局
        fig_trend.update_layout(
            title='ETF累计涨跌幅趋势对比',
            xaxis_title='时间',
            yaxis_title='累计涨跌幅 (%)',
            height=500,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            xaxis=dict(
                type="date"
            )
        )
        
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # 添加趋势图说明
        st.info("""
        **📊 趋势图说明：**
        - **横轴**：时间（支持缩放和拖动）
        - **纵轴**：累计涨跌幅（相对于起始价格的百分比变化）
        - **零线**：灰色虚线表示无涨跌状态
        - **交互功能**：鼠标悬停查看详细数据，可缩放特定时间段
        """)
    else:
        st.info("⚠️ 时间序列数据不足，无法生成涨跌幅趋势图")
    
    # 第二行：收益对比分析（全宽）
    st.subheader("📊 收益对比分析")
    
    # 累计收益和年化收益对比
    col1, col2 = st.columns(2)
    
    with col1:
        # 累计收益对比柱状图
        fig_returns = go.Figure()
        
        # 根据收益值设置颜色：涨用红色，跌用绿色
        colors_returns = ['#d62728' if x > 0 else '#2ca02c' for x in viz_df['累计收益(%)']]
        
        fig_returns.add_trace(go.Bar(
            x=viz_df['ETF名称'],
            y=viz_df['累计收益(%)'],
            marker_color=colors_returns,
            hovertemplate='<b>%{x}</b><br>累计收益: %{y:.2f}%<extra></extra>',
            text=[f'{x:.2f}%' for x in viz_df['累计收益(%)']],
            textposition='auto'
        ))
        
        fig_returns.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig_returns.update_layout(
            title='ETF累计收益对比',
            xaxis_title='ETF',
            yaxis_title='累计收益 (%)',
            height=400,
            showlegend=False,
            hovermode='closest'
        )
        
        if len(viz_df) > 6:
            fig_returns.update_xaxes(tickangle=45)
        
        st.plotly_chart(fig_returns, use_container_width=True)
    
    with col2:
        # 年化收益对比柱状图
        fig_annual = go.Figure()
        
        # 根据收益值设置颜色：涨用红色，跌用绿色
        colors_annual = ['#d62728' if x > 0 else '#2ca02c' for x in viz_df['年化收益(%)']]
        
        fig_annual.add_trace(go.Bar(
            x=viz_df['ETF名称'],
            y=viz_df['年化收益(%)'],
            marker_color=colors_annual,
            hovertemplate='<b>%{x}</b><br>年化收益: %{y:.2f}%<extra></extra>',
            text=[f'{x:.2f}%' for x in viz_df['年化收益(%)']],
            textposition='auto'
        ))
        
        fig_annual.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig_annual.update_layout(
            title='ETF年化收益对比',
            xaxis_title='ETF',
            yaxis_title='年化收益 (%)',
            height=400,
            showlegend=False,
            hovermode='closest'
        )
        
        if len(viz_df) > 6:
            fig_annual.update_xaxes(tickangle=45)
        
        st.plotly_chart(fig_annual, use_container_width=True)
    
    # 第三行：风险分析和分类分析
    st.subheader("📈 风险与分类分析")
    col1, col2 = st.columns(2)
    
    with col1:
        # 风险收益散点图
        valid_data = viz_df[viz_df['波动率(%)'] != 'N/A'].copy()
        if not valid_data.empty:
            valid_data['波动率(%)'] = pd.to_numeric(valid_data['波动率(%)'])
            
            # 创建size_value列，使用绝对收益值
            valid_data['size_value'] = valid_data['累计收益(%)'].abs()
            
            fig_scatter = px.scatter(
                valid_data,
                x='波动率(%)',
                y='累计收益(%)',
                color='分类',
                size='size_value',
                hover_name='ETF名称',
                title='风险收益散点图',
                size_max=20,
                color_discrete_map={
                    '宽基ETF': '#d62728',      # 红色
                    '行业ETF': '#ff7f0e',      # 橙色
                    '主题ETF': '#2ca02c',      # 绿色
                    '海外ETF': '#9467bd',      # 紫色
                    '商品ETF': '#8c564b',      # 棕色
                    '债券ETF': '#e377c2',      # 粉色
                    '其他ETF': '#7f7f7f'       # 灰色
                }
            )
            
            fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            
            fig_scatter.update_layout(
                height=400,
                hovermode='closest'
            )
            
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("⚠️ 波动率数据不足，无法生成风险收益散点图")
    
    with col2:
        # 分类收益对比
        category_returns = viz_df.groupby('分类')['累计收益(%)'].mean().reset_index()
        
        fig_category = go.Figure()
        
        # 根据收益值设置颜色：涨用红色，跌用绿色
        colors_category = ['#d62728' if x > 0 else '#2ca02c' for x in category_returns['累计收益(%)']]
        
        fig_category.add_trace(go.Bar(
            x=category_returns['分类'],
            y=category_returns['累计收益(%)'],
            marker_color=colors_category,
            hovertemplate='<b>%{x}</b><br>平均收益: %{y:.2f}%<extra></extra>',
            text=[f'{x:.2f}%' for x in category_returns['累计收益(%)']],
            textposition='auto'
        ))
        
        fig_category.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig_category.update_layout(
            title='ETF分类平均收益对比',
            xaxis_title='分类',
            yaxis_title='平均累计收益 (%)',
            height=400,
            showlegend=False,
            hovermode='closest'
        )
        
        st.plotly_chart(fig_category, use_container_width=True)
    
    # 第四行：风险指标对比（全宽）
    st.subheader("⚠️ 风险指标对比")
    
    # 创建子图：波动率、最大回撤、夏普比率
    fig_risk = make_subplots(
        rows=1, cols=3,
        subplot_titles=('波动率对比', '最大回撤对比', '夏普比率对比'),
        specs=[[{"type": "bar"}, {"type": "bar"}, {"type": "bar"}]]
    )
    
    # 波动率对比
    valid_vol = viz_df[viz_df['波动率(%)'] != 'N/A'].copy()
    if not valid_vol.empty:
        valid_vol['波动率(%)'] = pd.to_numeric(valid_vol['波动率(%)'])
        fig_risk.add_trace(
            go.Bar(x=valid_vol['ETF名称'], y=valid_vol['波动率(%)'], 
                   name='波动率', marker_color='#FF9999'),
            row=1, col=1
        )
    
    # 最大回撤对比
    valid_drawdown = viz_df[viz_df['最大回撤(%)'] != 'N/A'].copy()
    if not valid_drawdown.empty:
        valid_drawdown['最大回撤(%)'] = pd.to_numeric(valid_drawdown['最大回撤(%)'])
        fig_risk.add_trace(
            go.Bar(x=valid_drawdown['ETF名称'], y=valid_drawdown['最大回撤(%)'], 
                   name='最大回撤', marker_color='#FFCC99'),
            row=1, col=2
        )
    
    # 夏普比率对比
    valid_sharpe = viz_df[viz_df['夏普比率'] != 'N/A'].copy()
    if not valid_sharpe.empty:
        valid_sharpe['夏普比率'] = pd.to_numeric(valid_sharpe['夏普比率'])
        
        # 根据夏普比率值设置颜色：正值用红色，负值用绿色
        colors_sharpe = ['#d62728' if x > 0 else '#2ca02c' for x in valid_sharpe['夏普比率']]
        
        fig_risk.add_trace(
            go.Bar(x=valid_sharpe['ETF名称'], y=valid_sharpe['夏普比率'], 
                   name='夏普比率', marker_color=colors_sharpe),
            row=1, col=3
        )
    
    fig_risk.update_layout(
        height=400,
        showlegend=False,
        title_text="ETF风险指标综合对比"
    )
    
    # 调整x轴标签角度
    for i in range(1, 4):
        fig_risk.update_xaxes(tickangle=45, row=1, col=i)
    
    st.plotly_chart(fig_risk, use_container_width=True)
    
    # 添加风险指标说明
    st.info("""
    **📊 风险指标说明：**
    - **波动率**：衡量价格波动程度，越低越稳定
    - **最大回撤**：从峰值到谷值的最大跌幅，越低越好
    - **夏普比率**：风险调整后收益，越高越好（>1为优秀）
    """)
    
    # 投资建议
    st.subheader("💡 投资建议")
    
    # 找出表现最好和最差的ETF
    best_etf = max(analysis_results, key=lambda x: x['累计收益(%)'])
    worst_etf = min(analysis_results, key=lambda x: x['累计收益(%)'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        **🏆 表现最佳：**
        - **ETF：** {best_etf['ETF名称']} ({best_etf['ETF代码']})
        - **分类：** {best_etf['分类']}
        - **累计收益：** {best_etf['累计收益(%)']:.2f}%
        - **年化收益：** {best_etf['年化收益(%)']:.2f}%
        - **夏普比率：** {best_etf['夏普比率']}
        """)
    
    with col2:
        st.markdown(f"""
        **📉 表现最差：**
        - **ETF：** {worst_etf['ETF名称']} ({worst_etf['ETF代码']})
        - **分类：** {worst_etf['分类']}
        - **累计收益：** {worst_etf['累计收益(%)']:.2f}%
        - **年化收益：** {worst_etf['年化收益(%)']:.2f}%
        - **夏普比率：** {worst_etf['夏普比率']}
        """)
    
    st.markdown(f"""
    **📊 整体分析：**
    - **分析期间：** {f"{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}" if start_date else f"创立以来至 {end_date.strftime('%Y-%m-%d')}"} ({time_period})
    - **分析ETF数量：** {len(analysis_results)}只
    - **正收益ETF：** {sum(1 for r in analysis_results if r['累计收益(%)'] > 0)}只
    - **负收益ETF：** {sum(1 for r in analysis_results if r['累计收益(%)'] < 0)}只
    - **公平比较：** {'✅ 已启用' if fair_comparison else '❌ 未启用'}
    """ + (f"""
    - **公平比较说明：** 以最短创立时间 {start_date.strftime('%Y-%m-%d')} 为准，确保比较公平性
    """ if fair_comparison and start_date else ""))
    
    st.markdown(f"""
    **💡 投资建议：**
    - **高收益低风险**：关注夏普比率较高的ETF
    - **分散投资**：建议配置不同分类的ETF以分散风险
    - **长期持有**：ETF适合长期投资，避免频繁交易
    - **定期再平衡**：根据市场变化调整ETF配置比例
    """ + ("""
    - **公平比较建议**：启用公平比较功能，确保不同创立时间的ETF能够公平对比
    """ if fair_comparison else ""))
    
    # 下载功能
    st.subheader("💾 下载分析结果")
    col1, col2 = st.columns(2)
    
    with col1:
        # 下载CSV
        csv = results_df.to_csv(index=False, encoding='utf-8-sig')
        start_date_for_filename = start_date.strftime('%Y%m%d') if start_date else '创立以来'
        st.download_button(
            label="📥 下载CSV报告",
            data=csv,
            file_name=f"ETF对比分析_{start_date_for_filename}_{end_date.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # 下载Excel
        try:
            import io
            from openpyxl import Workbook
            
            # 创建Excel文件
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                results_df.to_excel(writer, sheet_name='ETF对比结果', index=False)
                
                # 获取工作表
                worksheet = writer.sheets['ETF对比结果']
                
                # 设置列宽
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 20)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            excel_data = output.getvalue()
            start_date_for_excel = start_date.strftime('%Y%m%d') if start_date else '创立以来'
            st.download_button(
                label="📥 下载Excel报告",
                data=excel_data,
                file_name=f"ETF对比分析_{start_date_for_excel}_{end_date.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except ImportError:
            st.info("💡 安装 openpyxl 可下载Excel格式报告")
