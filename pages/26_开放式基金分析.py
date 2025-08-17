import streamlit as st
import pandas as pd
import akshare as ak
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="开放式基金分析", page_icon="📊", layout="wide")

st.title("📊 开放式基金优秀基金筛选与分析")

st.markdown("""
本页面提供开放式基金的优秀基金筛选和深度分析，包括：
- **基金排行数据**：来自东方财富网-数据中心-开放式基金排行
- **基金业绩分析**：来自雪球基金数据
- **多维度筛选**：年化收益率、成立年限、各阶段收益等
- **深度分析**：单只基金的详细业绩表现
""")

# 侧边栏筛选条件
st.sidebar.header("🔍 筛选条件")

# 基金类型筛选
fund_types = ["全部", "股票型", "混合型", "债券型", "指数型", "QDII", "FOF"]
selected_type = st.sidebar.selectbox("基金类型", fund_types, index=0)

# 筛选优秀基金的条件
st.sidebar.header("🏆 优秀基金筛选条件")
min_annual_return = st.sidebar.number_input("最小年化收益率(%)", min_value=0.0, max_value=50.0, value=8.0, step=0.5)
min_years = st.sidebar.number_input("最小成立年限(年)", min_value=1.0, max_value=20.0, value=3.0, step=0.5)
min_1y_return = st.sidebar.number_input("最小近1年收益(%)", min_value=-50.0, max_value=100.0, value=5.0, step=1.0)
min_3y_return = st.sidebar.number_input("最小近3年收益(%)", min_value=-50.0, max_value=200.0, value=15.0, step=1.0)

# 数据获取函数
@st.cache_data(ttl=3600)
def get_open_fund_rank(fund_type="全部"):
    """获取开放式基金排行数据"""
    try:
        with st.spinner(f"正在获取{fund_type}基金排行数据..."):
            df = ak.fund_open_fund_rank_em(symbol=fund_type)
        st.success(f"成功获取 {len(df)} 只{fund_type}基金排行数据")
        return df
    except Exception as e:
        st.error(f"获取{fund_type}基金排行数据失败: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_fund_performance(symbol):
    """获取单只基金业绩数据"""
    try:
        return ak.fund_individual_achievement_xq(symbol=symbol)
    except:
        return pd.DataFrame()

# 获取数据
st.subheader("📊 优秀基金筛选")

# 获取开放式基金排行数据
rank_df = get_open_fund_rank(selected_type)

if rank_df.empty:
    st.error("无法获取基金排行数据，请稍后重试")
    st.stop()

# 数据预处理
st.subheader("📋 数据预处理")

# 处理基金排行数据
# 查找关键列
available_columns = rank_df.columns.tolist()

# 查找收益率相关列
return_columns = [col for col in available_columns if any(keyword in col for keyword in ['增长率', '近', '年', '月', '周', '今年来', '成立来'])]

# 处理数值列
for col in return_columns:
    if col in rank_df.columns:
        rank_df[col] = pd.to_numeric(rank_df[col], errors='coerce')

# 根据基金简称推断类型（简单分类）
def classify_fund_type(name):
    if pd.isna(name):
        return '其他'
    
    name_lower = str(name).lower()
    if any(keyword in name_lower for keyword in ['股票', '股基', '股票型']):
        return '股票型'
    elif any(keyword in name_lower for keyword in ['债券', '债基', '债券型', '纯债']):
        return '债券型'
    elif any(keyword in name_lower for keyword in ['混合', '混合型']):
        return '混合型'
    elif any(keyword in name_lower for keyword in ['指数', 'ETF', 'etf']):
        return '指数型'
    elif any(keyword in name_lower for keyword in ['货币', '货币型']):
        return '货币型'
    elif any(keyword in name_lower for keyword in ['qdii', 'QDII']):
        return 'QDII'
    elif any(keyword in name_lower for keyword in ['fof', 'FOF']):
        return 'FOF'
    else:
        return '其他'

rank_df['基金类型'] = rank_df['基金简称'].apply(classify_fund_type)

# 应用筛选条件
filtered_df = rank_df.copy()

# 筛选条件应用
if '成立来' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['成立来'] >= min_annual_return]

if '近1年' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['近1年'] >= min_1y_return]

if '近3年' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['近3年'] >= min_3y_return]

# 显示基本信息
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("总基金数", len(rank_df))
with col2:
    st.metric("筛选后基金数", len(filtered_df))
with col3:
    if '成立来' in filtered_df.columns:
        st.metric("平均成立来收益", f"{filtered_df['成立来'].mean():.2f}%")
    else:
        st.metric("平均成立来收益", "N/A")
with col4:
    if '近1年' in filtered_df.columns:
        st.metric("平均近1年收益", f"{filtered_df['近1年'].mean():.2f}%")
    else:
        st.metric("平均近1年收益", "N/A")

# 主要可视化分析
st.subheader("📊 主要分析图表")

# 1. 收益率分布
col1, col2 = st.columns(2)

with col1:
    if '成立来' in filtered_df.columns:
        st.write("**📈 成立来收益率分布**")
        
        fig_dist = go.Figure()
        
        fig_dist.add_trace(go.Histogram(
            x=filtered_df['成立来'],
            nbinsx=50,
            name='基金数量',
            marker_color='lightblue',
            opacity=0.7
        ))
        
        # 添加零线和平均线
        fig_dist.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="0%")
        fig_dist.add_vline(x=filtered_df['成立来'].mean(), line_dash="dash", line_color="blue", 
                           annotation_text=f"平均值: {filtered_df['成立来'].mean():.2f}%")
        
        fig_dist.update_layout(
            title="基金成立来收益率分布",
            xaxis_title="成立来收益率 (%)",
            yaxis_title="基金数量",
            height=400,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_dist, use_container_width=True)
    else:
        st.info("暂无成立来收益率数据")

with col2:
    st.write("**🏷️ 基金类型分布**")
    
    type_counts = filtered_df['基金类型'].value_counts()
    
    fig_pie = go.Figure(data=[go.Pie(
        labels=type_counts.index,
        values=type_counts.values,
        hole=0.3,
        textinfo='label+percent',
        textposition='inside'
    )])
    
    fig_pie.update_layout(
        title="基金类型分布",
        height=400
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

# 2. 各阶段收益率对比
if '近1月' in filtered_df.columns and '近3月' in filtered_df.columns and '近6月' in filtered_df.columns and '近1年' in filtered_df.columns:
    st.write("**📊 各阶段收益率对比**")
    
    # 计算各阶段平均收益率
    stage_returns = {
        '近1月': filtered_df['近1月'].mean(),
        '近3月': filtered_df['近3月'].mean(),
        '近6月': filtered_df['近6月'].mean(),
        '近1年': filtered_df['近1年'].mean()
    }
    
    fig_stage = go.Figure()
    
    colors = ['red' if x > 0 else 'green' for x in stage_returns.values()]
    
    fig_stage.add_trace(go.Bar(
        x=list(stage_returns.keys()),
        y=list(stage_returns.values()),
        marker_color=colors,
        opacity=0.8,
        hovertemplate='%{x}<br>平均收益率: %{y:.2f}%<extra></extra>'
    ))
    
    fig_stage.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="0%")
    
    fig_stage.update_layout(
        title="各阶段平均收益率对比",
        xaxis_title="时间段",
        yaxis_title="平均收益率 (%)",
        height=400,
        template='plotly_white'
    )
    
    st.plotly_chart(fig_stage, use_container_width=True)

# 3. 基金排行榜筛选
st.subheader("🏆 基金排行榜筛选")

# 筛选条件
col1, col2, col3, col4 = st.columns(4)
with col1:
    sort_by = st.selectbox("排序依据", ["成立来", "近1年", "近3年", "近6月", "近3月", "近1月"], index=0)
with col2:
    top_n = st.number_input("显示前N名", min_value=10, max_value=100, value=20, step=10)
with col3:
    ascending = st.checkbox("升序排列", value=False)
with col4:
    if sort_by in filtered_df.columns:
        min_val = filtered_df[sort_by].min()
        max_val = filtered_df[sort_by].max()
        min_threshold = st.number_input(f"最小{sort_by}(%)", min_value=float(min_val), max_value=float(max_val), value=float(min_val), step=0.1)

# 筛选数据
if sort_by in filtered_df.columns:
    filtered_df_sorted = filtered_df[filtered_df[sort_by] >= min_threshold].copy()
    sorted_df = filtered_df_sorted.sort_values(sort_by, ascending=ascending).head(top_n)
    
    # 横向柱状图
    fig_ranking = go.Figure()
    
    # 设置颜色
    colors = ['red' if x > 0 else 'green' if x < 0 else 'gray' for x in sorted_df[sort_by]]
    
    fig_ranking.add_trace(go.Bar(
        y=sorted_df['基金简称'].str[:25],
        x=sorted_df[sort_by],
        orientation='h',
        marker_color=colors,
        opacity=0.8,
        hovertemplate='%{y}<br>%{text}: %{x:.2f}%<extra></extra>',
        text=[sort_by] * len(sorted_df)
    ))
    
    fig_ranking.update_layout(
        title=f"基金{sort_by}排行榜（前{top_n}名，最小{sort_by}≥{min_threshold:.1f}%）",
        xaxis_title=f"{sort_by} (%)",
        yaxis_title="基金名称",
        height=max(400, len(sorted_df) * 20),
        template='plotly_white'
    )
    
    st.plotly_chart(fig_ranking, use_container_width=True)
    
    # 排行榜统计信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("筛选后基金数", len(filtered_df_sorted))
    with col2:
        st.metric("上榜基金数", len(sorted_df))
    with col3:
        avg_value = sorted_df[sort_by].mean()
        st.metric(f"上榜基金平均{sort_by}", f"{avg_value:.2f}%")
    
    # 显示排行榜表格
    st.write("**📋 排行榜详细数据**")
    display_cols = ['基金代码', '基金简称', '基金类型', '单位净值', '累计净值', '日增长率', sort_by]
    display_cols = [col for col in display_cols if col in sorted_df.columns]
    
    st.dataframe(
        sorted_df[display_cols].sort_values(sort_by, ascending=ascending),
        use_container_width=True,
        height=400
    )

# 4. 基金业绩深度分析（选择特定基金）
st.subheader("🔍 基金业绩深度分析")

# 基金选择
if not filtered_df.empty:
    fund_options = filtered_df['基金简称'].tolist()
    selected_fund = st.selectbox("选择要分析的基金", fund_options, index=0)
    
    if selected_fund:
        # 获取基金代码
        fund_code = filtered_df[filtered_df['基金简称'] == selected_fund]['基金代码'].iloc[0]
        
        # 获取业绩数据
        performance_df = get_fund_performance(fund_code)
        
        if not performance_df.empty:
            st.write(f"**📊 {selected_fund} 业绩分析**")
            
            # 年度业绩分析
            annual_perf = performance_df[performance_df['业绩类型'] == '年度业绩'].copy()
            if not annual_perf.empty:
                annual_perf['本产品区间收益'] = pd.to_numeric(annual_perf['本产品区间收益'], errors='coerce')
                
                # 过滤掉成立以来的数据，只保留具体年份
                annual_perf_filtered = annual_perf[annual_perf['周期'] != '成立以来'].copy()
                
                if not annual_perf_filtered.empty:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # 年度收益横向柱状图
                        fig_annual = go.Figure()
                        
                        # 设置颜色：正收益红色，负收益绿色
                        colors = ['red' if x > 0 else 'green' for x in annual_perf_filtered['本产品区间收益']]
                        
                        fig_annual.add_trace(go.Bar(
                            y=annual_perf_filtered['周期'],  # Y轴为年份
                            x=annual_perf_filtered['本产品区间收益'],  # X轴为收益率
                            orientation='h',  # 横向柱状图
                            marker_color=colors,
                            opacity=0.8,
                            hovertemplate='年份: %{y}<br>收益率: %{x:.2f}%<extra></extra>'
                        ))
                        
                        fig_annual.update_layout(
                            title="年度收益率表现",
                            yaxis_title="年份",
                            xaxis_title="收益率 (%)",
                            height=400,
                            template='plotly_white'
                        )
                        
                        st.plotly_chart(fig_annual, use_container_width=True)
                    
                    with col2:
                        # 年度收益趋势线图
                        fig_trend = go.Figure()
                        
                        fig_trend.add_trace(go.Scatter(
                            x=annual_perf_filtered['周期'],
                            y=annual_perf_filtered['本产品区间收益'],
                            mode='lines+markers',
                            line=dict(width=3, color='blue'),
                            marker=dict(size=8, color=colors),
                            name='年度收益率',
                            hovertemplate='年份: %{x}<br>收益率: %{y:.2f}%<extra></extra>'
                        ))
                        
                        # 添加零线
                        fig_trend.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="0%")
                        
                        fig_trend.update_layout(
                            title="年度收益率趋势",
                            xaxis_title="年份",
                            yaxis_title="收益率 (%)",
                            height=400,
                            template='plotly_white',
                            xaxis=dict(tickangle=45)
                        )
                        
                        st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.info("暂无有效的年度业绩数据")
            
            # 阶段业绩分析
            stage_perf = performance_df[performance_df['业绩类型'] == '阶段业绩'].copy()
            if not stage_perf.empty:
                stage_perf['本产品区间收益'] = pd.to_numeric(stage_perf['本产品区间收益'], errors='coerce')
                
                st.write("**📈 阶段业绩表现**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # 阶段业绩横向柱状图
                    fig_stage = go.Figure()
                    
                    # 设置颜色：正收益红色，负收益绿色
                    colors = ['red' if x > 0 else 'green' for x in stage_perf['本产品区间收益']]
                    
                    fig_stage.add_trace(go.Bar(
                        y=stage_perf['周期'],  # Y轴为时间段
                        x=stage_perf['本产品区间收益'],  # X轴为收益率
                        orientation='h',  # 横向柱状图
                        marker_color=colors,
                        opacity=0.8,
                        hovertemplate='时间段: %{y}<br>收益率: %{x:.2f}%<extra></extra>'
                    ))
                    
                    fig_stage.update_layout(
                        title="阶段业绩表现",
                        yaxis_title="时间段",
                        xaxis_title="收益率 (%)",
                        height=400,
                        template='plotly_white'
                    )
                    
                    st.plotly_chart(fig_stage, use_container_width=True)
                
                with col2:
                    # 阶段业绩雷达图
                    fig_radar = go.Figure()
                    
                    fig_radar.add_trace(go.Scatterpolar(
                        r=stage_perf['本产品区间收益'],
                        theta=stage_perf['周期'],
                        fill='toself',
                        name='阶段收益',
                        line_color='blue',
                        hovertemplate='%{theta}<br>收益率: %{r:.2f}%<extra></extra>'
                    ))
                    
                    fig_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[stage_perf['本产品区间收益'].min() - 5, 
                                       stage_perf['本产品区间收益'].max() + 5]
                            )),
                        title="阶段业绩雷达图",
                        height=400,
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_radar, use_container_width=True)
            
            # 业绩统计摘要
            st.write("**📊 业绩统计摘要**")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if not annual_perf.empty:
                    best_year = annual_perf.loc[annual_perf['本产品区间收益'].idxmax()]
                    st.metric("最佳年度", f"{best_year['周期']}", f"{best_year['本产品区间收益']:.2f}%")
            
            with col2:
                if not annual_perf.empty:
                    worst_year = annual_perf.loc[annual_perf['本产品区间收益'].idxmin()]
                    st.metric("最差年度", f"{worst_year['周期']}", f"{worst_year['本产品区间收益']:.2f}%")
            
            with col3:
                if not stage_perf.empty:
                    best_stage = stage_perf.loc[stage_perf['本产品区间收益'].idxmax()]
                    st.metric("最佳阶段", f"{best_stage['周期']}", f"{best_stage['本产品区间收益']:.2f}%")
            
            with col4:
                if not stage_perf.empty:
                    worst_stage = stage_perf.loc[stage_perf['本产品区间收益'].idxmin()]
                    st.metric("最差阶段", f"{worst_stage['周期']}", f"{worst_stage['本产品区间收益']:.2f}%")
            
            # 显示详细业绩数据
            st.write("**📋 详细业绩数据**")
            st.dataframe(performance_df, use_container_width=True)
            
        else:
            st.warning(f"无法获取 {selected_fund} 的业绩数据")

# 5. 风险分析
st.subheader("⚠️ 风险分析")

# 计算风险指标
if '成立来' in filtered_df.columns:
    risk_metrics = filtered_df.groupby('基金类型').agg({
        '成立来': ['mean', 'std', 'min', 'max']
    }).round(4)
    
    risk_metrics.columns = ['平均成立来收益', '成立来收益标准差', '最小成立来收益', '最大成立来收益']
    risk_metrics['变异系数'] = (risk_metrics['成立来收益标准差'] / abs(risk_metrics['平均成立来收益'])).round(4)
    
    # 风险指标表格
    st.write("**📊 各类型基金风险指标**")
    st.dataframe(risk_metrics, use_container_width=True)
    
    # 风险收益散点图
    fig_risk = go.Figure()
    
    for fund_type in filtered_df['基金类型'].unique():
        type_data = filtered_df[filtered_df['基金类型'] == fund_type]
        
        # 计算该类型的标准差和平均值
        std_val = type_data['成立来'].std()
        mean_val = type_data['成立来'].mean()
        
        # 确保数据有效
        if pd.notna(std_val) and pd.notna(mean_val):
            fig_risk.add_trace(go.Scatter(
                x=[std_val],  # 使用列表包装单个值
                y=[mean_val],  # 使用列表包装单个值
                mode='markers',
                name=fund_type,
                marker=dict(size=15),
                text=[fund_type],
                hovertemplate='%{text}<br>标准差: %{x:.4f}<br>平均成立来收益: %{y:.4f}%<extra></extra>'
            ))
    
    fig_risk.update_layout(
        title="风险收益分析（标准差 vs 平均成立来收益）",
        xaxis_title="成立来收益标准差",
        yaxis_title="平均成立来收益 (%)",
        height=500,
        template='plotly_white'
    )
    
    st.plotly_chart(fig_risk, use_container_width=True)

# 页脚信息
st.markdown("---")
st.markdown("""
**数据说明：**
- 数据来源：东方财富网-数据中心-开放式基金排行、雪球基金
- 更新频率：每个交易日更新
- 基金类型：基于基金简称的智能分类
- 风险提示：基金投资有风险，投资需谨慎
""")
