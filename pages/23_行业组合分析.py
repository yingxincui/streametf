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

st.set_page_config(page_title="中证全指行业组合分析", page_icon="🏭", layout="wide")
st.title("🏭 中证全指行业组合分析")

st.markdown("""
> 深入分析中证全指行业指数的相对表现，帮助投资者了解不同行业的强弱变化。
> 通过趋势图直观展示行业轮动规律，为投资决策提供数据支持。

**🎯 核心功能：**
- **全指行业组合**：自动加载10个中证全指行业指数
- **灵活基准选择**：支持选择上证指数、沪深300、中证500等作为基准
- **相对分析**：相对于选定基准指数的涨跌幅表现
- **基准对比**：以选定指数为基准，直观对比行业表现
- **趋势图表**：横轴日期、纵轴涨跌幅的交互式趋势图
- **双重趋势**：相对涨幅趋势图 + 自身涨幅趋势图
- **行业轮动**：识别行业强弱变化规律

**📊 分析维度：**
- **相对涨幅**：行业指数相对于大盘的表现
- **时间趋势**：行业表现的时间序列变化
- **强弱对比**：不同行业间的相对强弱
- **轮动规律**：行业轮动的周期性特征
- **全指覆盖**：中证全指指数覆盖更全面，行业分类更准确

**🚀 性能优化：**
- **专用接口**：使用中证指数专用接口 `stock_zh_index_hist_csindex`
- **数据源**：直接从中证指数官网获取数据，速度更快
- **备用方案**：中证接口失败时自动切换到备用接口
- **智能缓存**：24小时缓存机制，避免重复请求

**🎨 颜色规则：**
- **涨（正值）**：红色 🔴
- **跌（负值）**：绿色 🟢
（符合中国股市习惯）

**🏭 行业指数说明：**
- **能源材料**：000986中证全指能源（石油、煤炭、天然气等）、000987中证全指材料（化工、钢铁、有色金属、建材等）
- **工业制造**：000988中证全指工业（机械、电气设备、航空航天、建筑等）、000989中证全指可选消费（汽车、家电、传媒、零售等）
- **消费服务**：000990中证全指主要消费（食品饮料、农牧渔、日用品等）、000991中证全指医药卫生（医药、生物科技、医疗器械等）
- **金融地产**：000992中证全指金融地产（银行、保险、券商、房地产等）、000993中证全指信息技术（软件、硬件、半导体、互联网等）
- **电信科技**：000994中证全指通信服务（电信、5G、传媒服务等）、000995中证全指公用事业（电力、燃气、水务、环保等）

**💡 使用提示：**
- 页面已更新为中证全指行业指数，覆盖更全面，行业分类更准确
- 如果默认选择仍显示旧指数，请点击"🔄 重置默认"按钮更新
- 建议选择中证全指行业指数进行行业轮动分析
""")

# 获取指数列表
@st.cache_data(ttl=86400)  # 缓存24小时（指数列表变化很少）
def get_index_list():
    """获取指数列表，带重试机制和备用接口"""
    max_retries = 3
    
    # 首先尝试东方财富接口
    for attempt in range(max_retries):
        try:
            # 获取更多指数系列
            index_series = [
                "沪深重要指数",
                "上证系列指数", 
                "深证系列指数",
                "中证系列指数"
            ]
            
            all_indices_list = []
            
            for series in index_series:
                try:
                    series_data = ak.stock_zh_index_spot_em(symbol=series)
                    if not series_data.empty:
                        all_indices_list.append(series_data)
                    else:
                        continue
                except Exception as e:
                    continue
            
            if all_indices_list:
                # 合并所有指数
                all_indices = pd.concat(all_indices_list, ignore_index=True)
                # 去重
                all_indices = all_indices.drop_duplicates(subset=['代码'])
                
                if not all_indices.empty:
                    return all_indices
                else:
                    continue
            else:
                continue
                
        except Exception as e:
            if attempt < max_retries - 1:
                import time
                time.sleep(3)  # 等待3秒后重试
            else:
                break
    
    # 如果东方财富接口失败，尝试新浪接口
    for attempt in range(max_retries):
        try:
            # 使用新浪接口获取指数列表
            sina_indices = ak.stock_zh_index_spot_sina()
            
            if not sina_indices.empty:
                # 转换新浪数据格式以匹配东方财富格式
                sina_indices['代码'] = sina_indices['代码'].str.replace('sh', '').str.replace('sz', '')
                sina_indices = sina_indices[['代码', '名称', '最新价', '涨跌幅']]
                return sina_indices
        except Exception as e:
            if attempt < max_retries - 1:
                import time
                time.sleep(3)
            else:
                break
    
    return pd.DataFrame()

# 获取指数历史数据
@st.cache_data(ttl=86400)  # 缓存24小时（历史数据不会变化）
def get_index_history(symbol, start_date, end_date, max_retries=3):
    """获取指数历史数据，使用中证指数专用接口提升速度"""
    for attempt in range(max_retries):
        try:
            # 清理指数代码
            clean_symbol = symbol.replace('sh', '').replace('sz', '')
            
            # 转换日期格式为YYYYMMDD
            start_date_formatted = start_date.replace('-', '')
            end_date_formatted = end_date.replace('-', '')
            
            # 使用中证指数专用接口
            df = ak.stock_zh_index_hist_csindex(
                symbol=clean_symbol,
                start_date=start_date_formatted,
                end_date=end_date_formatted
            )
            
            if not df.empty:
                # 转换日期列
                df['日期'] = pd.to_datetime(df['日期'])
                df.set_index('日期', inplace=True)
                return df
            else:
                continue
                
        except Exception as e:
            if attempt < max_retries - 1:
                import time
                time.sleep(3)
                continue
            else:
                # 如果中证指数接口失败，尝试备用接口
                try:
                    st.warning(f"⚠️ 中证指数接口失败，尝试备用接口: {str(e)}")
                    df = ak.index_zh_a_hist(
                        symbol=clean_symbol,
                        period='daily',
                        start_date=start_date,
                        end_date=end_date,
                        adjust='qfq'
                    )
                    
                    if not df.empty:
                        df['日期'] = pd.to_datetime(df['日期'])
                        df.set_index('日期', inplace=True)
                        return df
                except Exception as backup_e:
                    continue
                break
    
    return pd.DataFrame()

# 获取指数列表
index_list = get_index_list()

if index_list.empty:
    st.error("无法获取指数列表，请检查网络连接")
    st.stop()

# 创建指数选项
index_options = []
for _, row in index_list.iterrows():
    code = row['代码']
    name = row['名称']
    index_options.append(f"{code} - {name}")

# 行业指数代码列表（10个中证全指行业指数）
industry_codes = ["000986", "000987", "000988", "000989", "000990", "000991", "000992", "000993", "000994", "000995"]

# 查找匹配的行业指数
selected_industry = []
found_codes = []

for code in industry_codes:
    for option in index_options:
        if option.startswith(f"{code} -"):
            selected_industry.append(option)
            found_codes.append(code)
            break

# 初始化session_state
if 'selected_industry_indices' not in st.session_state:
    if selected_industry:
        st.session_state.selected_industry_indices = selected_industry
    else:
        st.session_state.selected_industry_indices = index_options[:3] if index_options else []
else:
    # 如果session_state已存在，检查是否需要更新为新的行业指数
    current_defaults = st.session_state.selected_industry_indices
    # 检查当前默认值是否包含旧的指数代码
    old_codes = ["000928", "000929", "000930", "000931", "000932", "000933", "000934", "000935", "000936", "000937"]
    new_codes = ["000986", "000987", "000988", "000989", "000990", "000991", "000992", "000993", "000994", "000995"]
    
    # 如果当前默认值包含旧代码，则更新为新的行业指数
    if any(any(old_code in default for old_code in old_codes) for default in current_defaults):
        if selected_industry:
            st.session_state.selected_industry_indices = selected_industry
        else:
            st.session_state.selected_industry_indices = index_options[:3] if index_options else []

# 指数选择器
st.subheader("🔍 选择要分析的行业指数")

# 添加重置默认选择按钮
col1, col2 = st.columns([3, 1])
with col1:
    selected_indices = st.multiselect(
        "选择要分析的行业指数（可多选）",
        options=index_options,
        default=st.session_state.selected_industry_indices,
        key="industry_selector",
        help="选择要分析的行业指数，建议选择中证全指行业指数进行行业轮动分析，覆盖更全面，行业分类更准确"
    )

with col2:
    if st.button("🔄 重置默认", help="重置为新的中证全指行业指数"):
        if selected_industry:
            st.session_state.selected_industry_indices = selected_industry
            st.rerun()
        else:
            st.warning("未找到中证全指行业指数，请检查网络连接")

# 基准选择器
st.subheader("🎯 选择基准指数")
col1, col2 = st.columns([3, 1])

with col1:
    # 常用基准指数列表
    common_benchmarks = [
        "000001 - 上证指数",
        "000300 - 沪深300",
        "000905 - 中证500", 
        "399001 - 深证成指",
        "399006 - 创业板指",
        "000016 - 上证50"
    ]
    
    # 从指数列表中查找这些常用基准
    benchmark_options = []
    for benchmark in common_benchmarks:
        code = benchmark.split(" - ")[0]
        for option in index_options:
            if option.startswith(f"{code} -"):
                benchmark_options.append(option)
                break
    
    # 如果没有找到预定义的基准，使用所有指数作为选项
    if not benchmark_options:
        benchmark_options = index_options
    
    # 初始化基准选择
    if 'selected_benchmark' not in st.session_state:
        st.session_state.selected_benchmark = "000001 - 上证指数"
    
    selected_benchmark = st.selectbox(
        "选择基准指数（用于计算相对涨幅）",
        options=benchmark_options,
        index=0 if "000001 - 上证指数" in benchmark_options else 0,
        key="benchmark_selector",
        help="选择基准指数，行业指数的表现将相对于该基准进行计算"
    )

with col2:
    if st.button("🔄 重置基准", help="重置为上证指数"):
        st.session_state.selected_benchmark = "000001 - 上证指数"
        st.rerun()

# 显示基准信息
benchmark_code = selected_benchmark.split(" - ")[0]
benchmark_name = selected_benchmark.split(" - ")[1]
st.info(f"🎯 当前基准：**{benchmark_name}** ({benchmark_code}) - 行业指数的表现将相对于该基准进行计算")

# 显示选择的指数信息
if selected_indices:
    st.info(f"🎯 已选择 {len(selected_indices)} 个指数进行分析：")
    for i, index_info in enumerate(selected_indices, 1):
        index_code = index_info.split(" - ")[0]
        index_name = index_info.split(" - ")[1]
        st.write(f"{i}. **{index_name}** ({index_code})")
else:
    st.info("请选择要分析的行业指数")

# 分析时间范围
col1, col2 = st.columns(2)
with col1:
    end_date = st.date_input("结束日期", value=datetime.now(), max_value=datetime.now())
with col2:
    time_period = st.selectbox(
        "分析时间范围", 
        options=["1年", "6个月", "3个月", "1个月"], 
        index=0,  # 默认选择"1年"
        help="选择分析的时间范围"
    )

# 根据选择的时间范围计算开始日期
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
run_btn = st.button("🚀 运行行业组合分析")

if run_btn:
    if not selected_indices:
        st.warning("请至少选择1个指数进行分析")
        st.stop()
    
    if len(selected_indices) > 15:
        st.warning("建议选择不超过15个指数进行分析，以确保分析质量")
        st.stop()
    
    # 开始分析
    st.subheader("📊 行业组合分析结果")
    
    analysis_results = []
    time_series_data = {}  # 收集时间序列数据用于趋势图
    
    # 进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 使用expander折叠数据获取日志
    with st.expander("🔍 数据获取进度（点击展开查看详情）", expanded=False):
        st.info("💡 使用中证指数专用接口，数据获取速度更快更稳定")
        
        for i, index_info in enumerate(selected_indices):
            index_code = index_info.split(" - ")[0]
            index_name = index_info.split(" - ")[1]
            
            status_text.text(f"正在分析 {index_name} ({index_code})...")
            
            with st.spinner(f"正在获取 {index_name} 数据..."):
                # 获取指数历史数据
                index_data = get_index_history(index_code, start_date_str, end_date_str)
                
                if index_data.empty:
                    st.warning(f"⚠️ {index_name} 数据获取失败，跳过")
                    continue
                
                # 计算相对于基准指数的涨跌幅
                # 获取基准指数数据
                benchmark_data = get_index_history(benchmark_code, start_date_str, end_date_str)
                
                if benchmark_data.empty:
                    st.warning(f"⚠️ {benchmark_name} 基准指数数据获取失败，无法计算相对涨幅")
                    continue
                
                # 确保两个数据集有相同的日期索引
                common_dates = index_data.index.intersection(benchmark_data.index)
                if len(common_dates) < 2:
                    st.warning(f"⚠️ {index_name} 与基准指数数据重叠不足，跳过")
                    continue
                
                # 筛选共同日期的数据
                index_data_common = index_data.loc[common_dates]
                benchmark_data_common = benchmark_data.loc[common_dates]
                
                # 计算相对涨幅
                index_data_common['相对涨幅'] = (
                    (index_data_common['收盘'] / index_data_common['收盘'].iloc[0]) /
                    (benchmark_data_common['收盘'] / benchmark_data_common['收盘'].iloc[0]) - 1
                ) * 100
                
                # 计算累计涨幅
                index_data_common['累计涨幅'] = (
                    index_data_common['收盘'] / index_data_common['收盘'].iloc[0] - 1
                ) * 100
                
                # 计算年化涨幅
                days = (end_date - start_date).days
                annual_return = ((index_data_common['收盘'].iloc[-1] / index_data_common['收盘'].iloc[0]) ** (365/days) - 1) * 100
                
                # 计算相对年化涨幅
                benchmark_annual_return = ((benchmark_data_common['收盘'].iloc[-1] / benchmark_data_common['收盘'].iloc[0]) ** (365/days) - 1) * 100
                relative_annual_return = annual_return - benchmark_annual_return
                
                # 收集时间序列数据用于趋势图
                time_series_data[index_name] = {
                    'dates': common_dates,
                    'relative_returns': index_data_common['相对涨幅'],
                    'absolute_returns': index_data_common['累计涨幅']
                }
                
                # 存储结果
                result = {
                    '指数代码': index_code,
                    '指数名称': index_name,
                    '累计涨幅(%)': round(index_data_common['累计涨幅'].iloc[-1], 2),
                    '相对涨幅(%)': round(index_data_common['相对涨幅'].iloc[-1], 2),
                    '年化涨幅(%)': round(annual_return, 2),
                    '相对年化涨幅(%)': round(relative_annual_return, 2),
                    '数据天数': len(common_dates)
                }
                
                analysis_results.append(result)
                st.success(f"✅ {index_name} 分析完成")
            
            # 更新进度条
            progress_bar.progress((i + 1) / len(selected_indices))
    
    # 添加基准（上证指数）数据
    if analysis_results:
        # 获取上证指数的累计涨幅和年化涨幅
        sh_annual_return = ((benchmark_data_common['收盘'].iloc[-1] / benchmark_data_common['收盘'].iloc[0]) ** (365/days) - 1) * 100
        sh_cumulative_return = (benchmark_data_common['收盘'].iloc[-1] / benchmark_data_common['收盘'].iloc[0] - 1) * 100
        
        # 添加基准行
        benchmark_result = {
            '指数代码': benchmark_code,
            '指数名称': f'{benchmark_name}（基准）',
            '累计涨幅(%)': round(sh_cumulative_return, 2),
            '相对涨幅(%)': 0.00,  # 基准相对自身为0
            '年化涨幅(%)': round(sh_annual_return, 2),
            '相对年化涨幅(%)': 0.00,  # 基准相对自身为0
            '数据天数': len(common_dates)
        }
        
        # 将基准插入到结果列表的开头
        analysis_results.insert(0, benchmark_result)
    
    status_text.text("分析完成！")
    progress_bar.empty()
    status_text.empty()
    
    if not analysis_results:
        st.error("没有成功获取到任何指数数据，请检查网络连接或选择其他指数")
        st.stop()
    
    # 显示分析结果
    st.subheader("📋 行业组合分析结果表格")
    
    # 创建结果DataFrame
    results_df = pd.DataFrame(analysis_results)
    
    # 格式化表格显示
    def color_returns(val, row_idx):
        # 基准行（第一行）使用特殊样式
        if row_idx == 0:
            return 'background-color: #f0f8ff; color: #000080; font-weight: bold'  # 蓝色背景，深蓝色文字，加粗
        
        # 其他行根据涨跌设置颜色
        if isinstance(val, (int, float)) and val > 0:
            return 'background-color: #f8d7da; color: #721c24'  # 红色背景（涨）
        elif isinstance(val, (int, float)) and val < 0:
            return 'background-color: #d4edda; color: #155724'  # 绿色背景（跌）
        else:
            return ''
    
    # 应用样式
    styled_df = results_df.style.apply(
        lambda x: [color_returns(val, idx) for idx, val in enumerate(x)], 
        subset=['累计涨幅(%)', '相对涨幅(%)', '年化涨幅(%)', '相对年化涨幅(%)']
    ).format({
        '累计涨幅(%)': '{:.2f}%',
        '相对涨幅(%)': '{:.2f}%',
        '年化涨幅(%)': '{:.2f}%',
        '相对年化涨幅(%)': '{:.2f}%'
    })
    
    st.dataframe(styled_df, use_container_width=True)
    
    # 快速统计
    st.subheader("📊 快速统计")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # 排除基准行计算平均相对涨幅
        non_benchmark_results = results_df.iloc[1:]  # 跳过第一行（基准）
        avg_relative = non_benchmark_results['相对涨幅(%)'].mean()
        st.metric(
            "平均相对涨幅", 
            f"{avg_relative:.2f}%",
            delta_color="normal" if avg_relative > 0 else "inverse"
        )
    
    with col2:
        # 排除基准行找出最佳相对表现
        best_relative = non_benchmark_results['相对涨幅(%)'].max()
        best_index = non_benchmark_results.loc[non_benchmark_results['相对涨幅(%)'].idxmax(), '指数名称']
        st.metric(
            "最佳相对表现", 
            f"{best_relative:.2f}%",
            best_index
        )
    
    with col3:
        # 排除基准行计算跑赢基准数量
        positive_count = sum(1 for x in non_benchmark_results['相对涨幅(%)'] if x > 0)
        st.metric(
            f"跑赢{benchmark_name}数量", 
            f"{positive_count}/{len(non_benchmark_results)}",
            f"{positive_count/len(non_benchmark_results)*100:.1f}%"
        )
    
    with col4:
        # 排除基准行找出最差相对表现
        worst_relative = non_benchmark_results['相对涨幅(%)'].min()
        worst_index = non_benchmark_results.loc[non_benchmark_results['相对涨幅(%)'].idxmin(), '指数名称']
        st.metric(
            "最差相对表现", 
            f"{worst_relative:.2f}%",
            worst_index
        )
    
    # 添加基准统计行
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        benchmark_return = results_df.iloc[0]['累计涨幅(%)']
        st.metric(
            "基准累计涨幅", 
            f"{benchmark_return:.2f}%",
            delta_color="normal" if benchmark_return > 0 else "inverse"
        )
    
    with col2:
        benchmark_annual = results_df.iloc[0]['年化涨幅(%)']
        st.metric(
            "基准年化涨幅", 
            f"{benchmark_annual:.2f}%",
            delta_color="normal" if benchmark_annual > 0 else "inverse"
        )
    
    with col3:
        # 计算相对于基准的表现分布
        outperforming_count = sum(1 for x in non_benchmark_results['累计涨幅(%)'] if x > benchmark_return)
        st.metric(
            "跑赢基准数量", 
            f"{outperforming_count}/{len(non_benchmark_results)}",
            f"{outperforming_count/len(non_benchmark_results)*100:.1f}%"
        )
    
    with col4:
        # 计算相对于基准的波动情况
        relative_volatility = non_benchmark_results['相对涨幅(%)'].std()
        st.metric(
            "相对表现波动", 
            f"{relative_volatility:.2f}%",
            "标准差"
        )
    
    # 可视化分析
    st.subheader(" 可视化分析 - 双重趋势图对比")
    
    # 第一行：相对涨幅趋势图（全宽）
    if time_series_data:
        st.subheader("📈 行业相对涨幅趋势图")
        
        # 创建相对涨幅趋势图
        fig_trend = go.Figure()
        
        # 定义颜色列表
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                 '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        # 按相对涨幅排序显示趋势线（跑赢大盘的行业在前）
        sorted_time_series = sorted(
            time_series_data.items(), 
            key=lambda x: x[1]['relative_returns'].iloc[-1], 
            reverse=True
        )
        
        for i, (index_name, data) in enumerate(sorted_time_series):
            # 确保日期格式正确
            dates = pd.to_datetime(data['dates'])
            relative_returns = data['relative_returns']
            
            # 添加趋势线
            fig_trend.add_trace(go.Scatter(
                x=dates,
                y=relative_returns,
                mode='lines',
                name=index_name,
                line=dict(color=colors[i % len(colors)], width=2),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '日期: %{x}<br>' +
                            '相对涨幅: %{y:.2f}%<extra></extra>'
            ))
        
        # 添加零线
        fig_trend.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        # 更新布局
        fig_trend.update_layout(
            title=f'行业指数相对{benchmark_name}涨幅趋势对比（按相对涨幅排序）',
            xaxis_title='时间',
            yaxis_title='相对涨幅 (%)',
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
        st.info(f"""
        **📊 趋势图说明：**
        - **横轴**：时间（支持缩放和拖动）
        - **纵轴**：相对涨幅（相对于{benchmark_name}的百分比变化）
        - **零线**：灰色虚线表示与基准持平状态
        - **正值**：跑赢基准（红色显示）
        - **负值**：跑输基准（绿色显示）
        - **排序规则**：按相对涨幅从高到低排序，跑赢基准的行业在前
        - **交互功能**：鼠标悬停查看详细数据，可缩放特定时间段
        - **分析价值**：排序后可以直观看出行业强弱顺序和相对表现差异
        """)
        
        # 第二行：自身涨幅趋势图（全宽）
        st.subheader("📈 行业自身涨幅趋势图")
        
        # 创建自身涨幅趋势图
        fig_absolute = go.Figure()
        
        # 定义颜色列表
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                 '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        # 使用相同的排序（按相对涨幅排序，保持与相对涨幅趋势图一致）
        for i, (index_name, data) in enumerate(sorted_time_series):
            # 确保日期格式正确
            dates = pd.to_datetime(data['dates'])
            absolute_returns = data['absolute_returns']
            
            # 添加趋势线
            fig_absolute.add_trace(go.Scatter(
                x=dates,
                y=absolute_returns,
                mode='lines',
                name=index_name,
                line=dict(color=colors[i % len(colors)], width=2),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '日期: %{x}<br>' +
                            '累计涨幅: %{y:.2f}%<extra></extra>'
            ))
        
        # 添加零线
        fig_absolute.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        # 更新布局
        fig_absolute.update_layout(
            title='行业指数自身累计涨幅趋势对比（按相对涨幅排序）',
            xaxis_title='时间',
            yaxis_title='累计涨幅 (%)',
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
        
        st.plotly_chart(fig_absolute, use_container_width=True)
        
        # 添加自身涨幅趋势图说明
        st.info("""
        **📊 自身涨幅趋势图说明：**
        - **横轴**：时间（支持缩放和拖动）
        - **纵轴**：累计涨幅（各行业指数自身的绝对涨幅）
        - **零线**：灰色虚线表示无涨跌状态
        - **正值**：上涨（红色显示）
        - **负值**：下跌（绿色显示）
        - **排序规则**：与相对涨幅趋势图保持一致，便于对比分析
        - **对比作用**：与相对涨幅图对比，了解绝对表现和相对表现
        - **分析价值**：排序后可以直观看出行业强弱顺序和表现差异
        """)
    else:
        st.info("⚠️ 时间序列数据不足，无法生成相对涨幅趋势图")
    
    # 第二行：相对涨幅对比分析
    st.subheader("📊 相对涨幅对比分析")
    
    # 对结果进行排序（排除基准行，按相对涨幅从高到低排序）
    sorted_results = results_df.iloc[1:].sort_values('相对涨幅(%)', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 相对涨幅对比柱状图
        fig_relative = go.Figure()
        
        # 根据相对涨幅值设置颜色：涨用红色，跌用绿色
        colors_relative = ['#d62728' if x > 0 else '#2ca02c' for x in sorted_results['相对涨幅(%)']]
        
        fig_relative.add_trace(go.Bar(
            x=sorted_results['指数名称'],
            y=sorted_results['相对涨幅(%)'],
            marker_color=colors_relative,
            hovertemplate='<b>%{x}</b><br>相对涨幅: %{y:.2f}%<extra></extra>',
            text=[f'{x:.2f}%' for x in sorted_results['相对涨幅(%)']],
            textposition='auto'
        ))
        
        fig_relative.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig_relative.update_layout(
            title=f'行业指数相对{benchmark_name}涨幅对比（按相对涨幅排序）',
            xaxis_title='行业指数',
            yaxis_title='相对涨幅 (%)',
            height=400,
            showlegend=False,
            hovermode='closest'
        )
        
        if len(sorted_results) > 6:
            fig_relative.update_xaxes(tickangle=45)
        
        st.plotly_chart(fig_relative, use_container_width=True)
    
    with col2:
        # 年化涨幅对比柱状图（保持与相对涨幅相同的排序）
        fig_annual = go.Figure()
        
        # 根据年化涨幅值设置颜色：涨用红色，跌用绿色
        colors_annual = ['#d62728' if x > 0 else '#2ca02c' for x in sorted_results['年化涨幅(%)']]
        
        fig_annual.add_trace(go.Bar(
            x=sorted_results['指数名称'],
            y=sorted_results['年化涨幅(%)'],
            marker_color=colors_annual,
            hovertemplate='<b>%{x}</b><br>年化涨幅: %{y:.2f}%<extra></extra>',
            text=[f'{x:.2f}%' for x in sorted_results['年化涨幅(%)']],
            textposition='auto'
        ))
        
        fig_annual.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig_annual.update_layout(
            title='行业指数年化涨幅对比（按相对涨幅排序）',
            xaxis_title='行业指数',
            yaxis_title='年化涨幅 (%)',
            height=400,
            showlegend=False,
            hovermode='closest'
        )
        
        if len(sorted_results) > 6:
            fig_annual.update_xaxes(tickangle=45)
        
        st.plotly_chart(fig_annual, use_container_width=True)
    
    # 添加排序说明
    st.info(f"""
    **📊 图表排序说明：**
    - **排序规则**：按相对涨幅从高到低排序（跑赢{benchmark_name}的行业在前）
    - **左图**：相对涨幅对比（相对于{benchmark_name}的表现）
    - **右图**：年化涨幅对比（保持相同排序，便于对比分析）
    - **颜色规则**：红色表示正值（涨），绿色表示负值（跌）
    - **分析价值**：排序后可以直观看出行业强弱顺序和相对表现差异
    """)
    
    # 投资建议
    st.subheader("💡 投资建议")
    
    # 找出表现最好和最差的指数（排除基准）
    best_index = max(analysis_results[1:], key=lambda x: x['相对涨幅(%)'])
    worst_index = min(analysis_results[1:], key=lambda x: x['相对涨幅(%)'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        **🏆 相对表现最佳：**
        - **指数：** {best_index['指数名称']} ({best_index['指数代码']})
        - **相对涨幅：** {best_index['相对涨幅(%)']:.2f}%
        - **年化涨幅：** {best_index['年化涨幅(%)']:.2f}%
        - **相对年化涨幅：** {best_index['相对年化涨幅(%)']:.2f}%
        """)
    
    with col2:
        st.markdown(f"""
        **📉 相对表现最差：**
        - **指数：** {worst_index['指数名称']} ({worst_index['指数代码']})
        - **相对涨幅：** {worst_index['相对涨幅(%)']:.2f}%
        - **年化涨幅：** {worst_index['年化涨幅(%)']:.2f}%
        - **相对年化涨幅：** {worst_index['相对年化涨幅(%)']:.2f}%
        """)
    
    # 添加基准表现信息
    benchmark_info = analysis_results[0]
    st.markdown(f"""
    **📊 基准表现：**
    - **基准指数：** {benchmark_info['指数名称']} ({benchmark_info['指数代码']})
    - **累计涨幅：** {benchmark_info['累计涨幅(%)']:.2f}%
    - **年化涨幅：** {benchmark_info['年化涨幅(%)']:.2f}%
    - **分析期间：** {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')} ({time_period})
    """)
    
    st.markdown(f"""
    **📊 整体分析：**
    - **分析指数数量：** {len(analysis_results)-1}个（不含基准）
    - **跑赢{benchmark_name}：** {sum(1 for r in analysis_results[1:] if r['相对涨幅(%)'] > 0)}个
    - **跑输{benchmark_name}：** {sum(1 for r in analysis_results[1:] if r['相对涨幅(%)'] < 0)}个
    - **跑赢基准：** {sum(1 for r in analysis_results[1:] if r['累计涨幅(%)'] > benchmark_info['累计涨幅(%)'])}个
    
    **💡 投资建议：**
    - **强势行业**：关注相对涨幅较高的行业，可能处于上升周期
    - **弱势行业**：相对涨幅较低的行业可能处于调整期，关注反转机会
    - **行业轮动**：通过趋势图观察行业轮动规律，把握投资时机
    - **分散配置**：建议配置不同相对表现的行业，分散投资风险
    - **双重分析**：结合相对涨幅和自身涨幅趋势图，全面判断行业表现
    - **绝对vs相对**：自身涨幅高但相对涨幅低的行业，可能是基准带动；自身涨幅低但相对涨幅高的行业，可能是抗跌性较强
    - **基准对比**：关注跑赢基准的行业，这些行业在绝对收益上表现更好
    """)
    
    # 下载功能
    st.subheader("💾 下载分析结果")
    col1, col2 = st.columns(2)
    
    with col1:
        # 下载CSV
        csv = results_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 下载CSV报告",
            data=csv,
            file_name=f"行业组合分析_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
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
                results_df.to_excel(writer, sheet_name='行业组合分析结果', index=False)
                
                # 获取工作表
                worksheet = writer.sheets['行业组合分析结果']
                
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
            st.download_button(
                label="📥 下载Excel报告",
                data=excel_data,
                file_name=f"行业组合分析_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except ImportError:
            st.info("💡 安装 openpyxl 可下载Excel格式报告")
