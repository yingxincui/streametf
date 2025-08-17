import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
import plotly.graph_objects as go
import plotly.express as px

st.title("基金溢价监控（QDII/LOF/ETF）")

st.markdown("""
本页用于监控QDII、LOF、ETF等基金的T-1日溢价率，数据来源：集思录。可自定义溢价率阈值，LOF优先展示。
""")

def fetch_qdii_data():
    try:
        qdii_data = ak.qdii_e_index_jsl()
        return qdii_data
    except Exception as e:
        st.error(f"获取数据失败: {e}")
        return None

def clean_data(data):
    if data is None:
        return None
    data = data.replace('-', np.nan)
    data['现价'] = pd.to_numeric(data['现价'], errors='coerce')
    # 处理溢价率字段 - 移除百分号并转为数值
    if 'T-1溢价率' in data.columns:
        data['T-1溢价率'] = data['T-1溢价率'].str.replace('%', '').astype(float)
    # 处理涨幅字段 - 移除百分号并转为数值
    if '涨幅' in data.columns:
        data['涨幅'] = data['涨幅'].str.replace('%', '').astype(float)
    # 处理指数涨幅字段 - 移除百分号并转为数值
    if 'T-1指数涨幅' in data.columns:
        data['T-1指数涨幅'] = data['T-1指数涨幅'].str.replace('%', '').astype(float)
    return data

def filter_and_monitor_premium_rate(data, threshold=1):
    if data is None:
        return None
    high_premium_funds = data[data['T-1溢价率'] > threshold]
    lof_funds = high_premium_funds[high_premium_funds['名称'].str.contains("LOF")]
    etf_funds = high_premium_funds[~high_premium_funds['名称'].str.contains("LOF")]
    result = pd.concat([lof_funds, etf_funds], ignore_index=True)
    return result

threshold = st.number_input("溢价率阈值(%)", min_value=0.0, max_value=10.0, value=1.0, step=0.1)

# 默认渲染数据
with st.spinner("正在获取QDII/LOF/ETF溢价数据..."):
    raw_data = fetch_qdii_data()
    data = clean_data(raw_data)
    result = filter_and_monitor_premium_rate(data, threshold)
    if result is None or result.empty:
        st.info("暂无溢价率高于阈值的基金。")
    else:
        # 显示主要字段
        display_columns = ['代码', '名称', '现价', '涨幅', 'T-1溢价率', 'T-1估值', '净值日期', '基金公司']
        available_columns = [col for col in display_columns if col in result.columns]
        st.dataframe(result[available_columns].sort_values('T-1溢价率', ascending=False), use_container_width=True)
        
        # 添加溢价率可视化图表
        st.subheader("📊 溢价率可视化分析")
        
        # 1. 溢价率排行榜（横向柱状图）
        st.write("**🏆 溢价率排行榜**")
        
        # 获取前30名基金（避免图表过长）
        top_30_premium = result.nlargest(30, 'T-1溢价率')
        
        fig_premium = go.Figure()
        
        # 设置颜色：根据溢价率设置渐变色
        colors = ['red' if x >= 5 else 'orange' if x >= 3 else 'gold' if x >= 1 else 'lightblue' for x in top_30_premium['T-1溢价率']]
        
        fig_premium.add_trace(go.Bar(
            y=top_30_premium['名称'].str[:25],  # 截取前25个字符
            x=top_30_premium['T-1溢价率'],
            orientation='h',
            marker_color=colors,
            opacity=0.8,
            hovertemplate='%{y}<br>溢价率: %{x:.2f}%<br>现价: %{text:.3f}<extra></extra>',
            text=top_30_premium['现价']
        ))
        
        fig_premium.update_layout(
            title=f"溢价率排行榜（前30名，阈值>{threshold}%）",
            xaxis_title="溢价率 (%)",
            yaxis_title="基金名称",
            height=600,
            showlegend=False,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_premium, use_container_width=True)
        
        # 2. 溢价率分布直方图
        st.write("**📈 溢价率分布**")
        
        fig_dist = go.Figure()
        
        fig_dist.add_trace(go.Histogram(
            x=result['T-1溢价率'],
            nbinsx=20,
            name='基金数量',
            marker_color='lightcoral',
            opacity=0.7,
            hovertemplate='溢价率区间: %{x:.1f}%<br>基金数量: %{y}<extra></extra>'
        ))
        
        # 添加平均线和阈值线
        mean_premium = result['T-1溢价率'].mean()
        fig_dist.add_vline(x=mean_premium, line_dash="dash", line_color="blue", 
                          annotation_text=f"平均值: {mean_premium:.2f}%")
        fig_dist.add_vline(x=threshold, line_dash="dash", line_color="red", 
                          annotation_text=f"阈值: {threshold}%")
        
        fig_dist.update_layout(
            title="溢价率分布直方图",
            xaxis_title="溢价率 (%)",
            yaxis_title="基金数量",
            height=400,
            showlegend=False,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_dist, use_container_width=True)
        
        # 3. 基金类型分析
        st.write("**🏷️ 基金类型分析**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 基金类型分布饼图
            result['基金类型'] = result['名称'].apply(lambda x: 'LOF' if 'LOF' in x else ('ETF' if 'ETF' in x else 'QDII'))
            type_counts = result['基金类型'].value_counts()
            
            fig_type_pie = go.Figure(data=[go.Pie(
                labels=type_counts.index,
                values=type_counts.values,
                hole=0.3,
                textinfo='label+percent',
                textposition='inside',
                hovertemplate='<b>%{label}</b><br>数量: %{value}<br>占比: %{percent}<extra></extra>'
            )])
            
            fig_type_pie.update_layout(
                title="高溢价基金类型分布",
                height=400,
                showlegend=True
            )
            
            st.plotly_chart(fig_type_pie, use_container_width=True)
        
        with col2:
            # 各类型平均溢价率对比
            type_avg = result.groupby('基金类型')['T-1溢价率'].agg(['mean', 'count']).reset_index()
            type_avg = type_avg.sort_values('mean', ascending=False)
            
            fig_type_bar = go.Figure()
            
            fig_type_bar.add_trace(go.Bar(
                x=type_avg['基金类型'],
                y=type_avg['mean'],
                marker_color='lightcoral',
                opacity=0.8,
                hovertemplate='%{x}<br>平均溢价率: %{y:.2f}%<br>基金数量: %{text}<extra></extra>',
                text=type_avg['count']
            ))
            
            fig_type_bar.update_layout(
                title="各类型基金平均溢价率",
                xaxis_title="基金类型",
                yaxis_title="平均溢价率 (%)",
                height=400,
                template='plotly_white'
            )
            
            st.plotly_chart(fig_type_bar, use_container_width=True)
        
        # 4. 溢价率vs涨幅散点图
        if '涨幅' in result.columns:
            st.write("**📈 溢价率vs涨幅关系**")
            
            fig_scatter = go.Figure()
            
            fig_scatter.add_trace(go.Scatter(
                x=result['涨幅'],
                y=result['T-1溢价率'],
                mode='markers',
                marker=dict(
                    size=8,
                    color=result['T-1溢价率'],
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(title="溢价率")
                ),
                text=result['名称'],
                hovertemplate='<b>%{text}</b><br>涨幅: %{x:.2f}%<br>溢价率: %{y:.2f}%<extra></extra>'
            ))
            
            # 添加参考线
            fig_scatter.add_hline(y=threshold, line_dash="dash", line_color="red", 
                                annotation_text=f"溢价率阈值: {threshold}%")
            fig_scatter.add_vline(x=0, line_dash="dash", line_color="gray", 
                                annotation_text="涨幅0%线")
            
            fig_scatter.update_layout(
                title="溢价率vs涨幅散点图（颜色表示溢价率）",
                xaxis_title="涨幅 (%)",
                yaxis_title="溢价率 (%)",
                height=500,
                template='plotly_white'
            )
            
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        # 5. 统计信息卡片
        st.write("**📊 统计信息**")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("监控基金数量", len(result))
        
        with col2:
            st.metric("平均溢价率", f"{mean_premium:.2f}%")
        
        with col3:
            max_premium = result['T-1溢价率'].max()
            st.metric("最高溢价率", f"{max_premium:.2f}%")
        
        with col4:
            min_premium = result['T-1溢价率'].min()
            st.metric("最低溢价率", f"{min_premium:.2f}%")

# 添加刷新按钮
if st.button("刷新监控数据"):
    st.rerun() 