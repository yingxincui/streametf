import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
import datetime
import plotly.graph_objects as go
import plotly.express as px
from ai_utils import ai_chat, get_api_key, set_api_key

st.set_page_config(page_title="ETF排行榜", page_icon="🏆", layout="wide")
st.title("🏆 ETF排行榜")

st.markdown("本页展示场内交易基金近一月涨幅排名前50和后50的品种，数据来源：东方财富网，供快速筛选强弱势基金参考。")

def get_today_str():
    return datetime.date.today().strftime('%Y-%m-%d')

@st.cache_data
def get_etf_rank_data(today_str):
    return ak.fund_exchange_rank_em()

today_str = get_today_str()

# --- AI Key输入与保存 ---
# （已移除API Key输入区）

with st.spinner("正在获取场内基金排行数据..."):
    try:
        df = get_etf_rank_data(today_str)
        st.write(f"数据获取成功，共{len(df)}条记录")
        # 确保近1月字段存在且为数值型
        if '近1月' in df.columns:
            df['近1月'] = pd.to_numeric(df['近1月'], errors='coerce')
            df = df.dropna(subset=['近1月'])
            # 按近1月涨幅排序
            df_sorted = df.sort_values('近1月', ascending=False).reset_index(drop=True)
            # 显示主要字段
            display_columns = ['基金代码', '基金简称', '类型', '单位净值', '近1月', '近3月', '近1年', '成立日期']
            available_columns = [col for col in display_columns if col in df_sorted.columns]
            st.subheader("近一月涨幅前50名基金")
            st.dataframe(
                df_sorted.head(50)[available_columns].style.format({
                    '单位净值': '{:.4f}',
                    '近1月': '{:.2f}%',
                    '近3月': '{:.2f}%',
                    '近1年': '{:.2f}%'
                }), 
                use_container_width=True
            )
            st.subheader("近一月涨幅后50名基金")
            st.dataframe(
                df_sorted.tail(50).sort_values('近1月')[available_columns].style.format({
                    '单位净值': '{:.4f}',
                    '近1月': '{:.2f}%',
                    '近3月': '{:.2f}%',
                    '近1年': '{:.2f}%'
                }), 
                use_container_width=True
            )
            # 显示统计信息
            st.subheader("统计信息")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("平均涨幅", f"{df_sorted['近1月'].mean():.2f}%")
            with col2:
                st.metric("最高涨幅", f"{df_sorted['近1月'].max():.2f}%")
            with col3:
                st.metric("最低涨幅", f"{df_sorted['近1月'].min():.2f}%")
            
            # 添加可视化图表
            st.subheader("📊 数据可视化分析")
            
            # 1. 涨幅分布直方图
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📈 近1月涨幅分布**")
                fig_dist = go.Figure()
                
                # 创建直方图
                fig_dist.add_trace(go.Histogram(
                    x=df_sorted['近1月'],
                    nbinsx=30,
                    name='基金数量',
                    marker_color='lightblue',
                    opacity=0.7,
                    hovertemplate='涨幅区间: %{x:.1f}%<br>基金数量: %{y}<extra></extra>'
                ))
                
                # 添加平均线
                mean_return = df_sorted['近1月'].mean()
                fig_dist.add_vline(x=mean_return, line_dash="dash", line_color="red", 
                                 annotation_text=f"平均值: {mean_return:.2f}%")
                
                fig_dist.update_layout(
                    title="近1月涨幅分布直方图",
                    xaxis_title="涨幅 (%)",
                    yaxis_title="基金数量",
                    height=400,
                    showlegend=False,
                    template='plotly_white'
                )
                
                st.plotly_chart(fig_dist, use_container_width=True)
            
            with col2:
                st.write("**🏆 前20名基金涨幅对比**")
                
                # 获取前20名基金数据
                top_20 = df_sorted.head(20)
                
                # 创建水平柱状图
                fig_top20 = go.Figure()
                
                # 设置颜色：正收益红色，负收益绿色
                colors = ['red' if x >= 0 else 'green' for x in top_20['近1月']]
                
                fig_top20.add_trace(go.Bar(
                    y=top_20['基金简称'].str[:15],  # 截取前15个字符
                    x=top_20['近1月'],
                    orientation='h',
                    marker_color=colors,
                    opacity=0.8,
                    hovertemplate='%{y}<br>涨幅: %{x:.2f}%<extra></extra>'
                ))
                
                fig_top20.update_layout(
                    title="前20名基金涨幅对比",
                    xaxis_title="涨幅 (%)",
                    yaxis_title="基金名称",
                    height=400,
                    showlegend=False,
                    template='plotly_white'
                )
                
                st.plotly_chart(fig_top20, use_container_width=True)
            
            # 2. 涨幅区间统计饼图
            st.write("**📊 涨幅区间分布**")
            
            # 创建涨幅区间
            def create_return_ranges(returns):
                ranges = []
                for ret in returns:
                    if ret >= 20:
                        ranges.append('≥20%')
                    elif ret >= 10:
                        ranges.append('10%-20%')
                    elif ret >= 0:
                        ranges.append('0%-10%')
                    elif ret >= -10:
                        ranges.append('-10%-0%')
                    elif ret >= -20:
                        ranges.append('-20%--10%')
                    else:
                        ranges.append('<-20%')
                return ranges
            
            df_sorted['涨幅区间'] = create_return_ranges(df_sorted['近1月'])
            range_counts = df_sorted['涨幅区间'].value_counts()
            
            # 创建饼图
            fig_pie = go.Figure(data=[go.Pie(
                labels=range_counts.index,
                values=range_counts.values,
                hole=0.3,
                textinfo='label+percent',
                textposition='inside',
                hovertemplate='<b>%{label}</b><br>基金数量: %{value}<br>占比: %{percent}<extra></extra>'
            )])
            
            fig_pie.update_layout(
                title="近1月涨幅区间分布",
                height=400,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # 3. 前10名vs后10名对比图
            st.write("**⚖️ 前10名vs后10名对比**")
            
            top_10 = df_sorted.head(10)
            bottom_10 = df_sorted.tail(10).sort_values('近1月')
            
            fig_comparison = go.Figure()
            
            # 前10名
            fig_comparison.add_trace(go.Bar(
                name='前10名',
                x=top_10['基金简称'].str[:12],
                y=top_10['近1月'],
                marker_color='red',
                opacity=0.8,
                hovertemplate='%{x}<br>涨幅: %{y:.2f}%<extra></extra>'
            ))
            
            # 后10名
            fig_comparison.add_trace(go.Bar(
                name='后10名',
                x=bottom_10['基金简称'].str[:12],
                y=bottom_10['近1月'],
                marker_color='green',
                opacity=0.8,
                hovertemplate='%{x}<br>涨幅: %{y:.2f}%<extra></extra>'
            ))
            
            fig_comparison.update_layout(
                title="前10名vs后10名基金涨幅对比",
                xaxis_title="基金名称",
                yaxis_title="涨幅 (%)",
                height=500,
                barmode='group',
                template='plotly_white',
                xaxis=dict(tickangle=45)
            )
            
            st.plotly_chart(fig_comparison, use_container_width=True)
            
            # 4. 涨幅趋势散点图（如果有时间数据）
            if '近3月' in df_sorted.columns and '近1年' in df_sorted.columns:
                st.write("**📈 短期vs长期表现散点图**")
                
                fig_scatter = go.Figure()
                
                # 创建散点图
                fig_scatter.add_trace(go.Scatter(
                    x=df_sorted['近3月'],
                    y=df_sorted['近1年'],
                    mode='markers',
                    marker=dict(
                        size=8,
                        color=df_sorted['近1月'],
                        colorscale='RdYlGn',
                        showscale=True,
                        colorbar=dict(title="近1月涨幅")
                    ),
                    text=df_sorted['基金简称'],
                    hovertemplate='<b>%{text}</b><br>近3月: %{x:.2f}%<br>近1年: %{y:.2f}%<br>近1月: %{marker.color:.2f}%<extra></extra>'
                ))
                
                # 添加参考线
                fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
                fig_scatter.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
                
                fig_scatter.update_layout(
                    title="短期vs长期表现对比（颜色表示近1月涨幅）",
                    xaxis_title="近3月涨幅 (%)",
                    yaxis_title="近1年涨幅 (%)",
                    height=500,
                    template='plotly_white'
                )
                
                st.plotly_chart(fig_scatter, use_container_width=True)
            
            # 5. 基金类型分布分析
            if '类型' in df_sorted.columns:
                st.write("**🏷️ 基金类型分布分析**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # 类型分布饼图
                    type_counts = df_sorted['类型'].value_counts()
                    
                    fig_type_pie = go.Figure(data=[go.Pie(
                        labels=type_counts.index,
                        values=type_counts.values,
                        hole=0.3,
                        textinfo='label+percent',
                        textposition='inside',
                        hovertemplate='<b>%{label}</b><br>数量: %{value}<br>占比: %{percent}<extra></extra>'
                    )])
                    
                    fig_type_pie.update_layout(
                        title="基金类型分布",
                        height=400,
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig_type_pie, use_container_width=True)
                
                with col2:
                    # 各类型平均涨幅对比
                    type_avg = df_sorted.groupby('类型')['近1月'].agg(['mean', 'count']).reset_index()
                    type_avg = type_avg.sort_values('mean', ascending=False)
                    
                    fig_type_bar = go.Figure()
                    
                    fig_type_bar.add_trace(go.Bar(
                        x=type_avg['类型'],
                        y=type_avg['mean'],
                        marker_color='lightcoral',
                        opacity=0.8,
                        hovertemplate='%{x}<br>平均涨幅: %{y:.2f}%<br>基金数量: %{text}<extra></extra>',
                        text=type_avg['count']
                    ))
                    
                    fig_type_bar.update_layout(
                        title="各类型基金平均涨幅对比",
                        xaxis_title="基金类型",
                        yaxis_title="平均涨幅 (%)",
                        height=400,
                        template='plotly_white',
                        xaxis=dict(tickangle=45)
                    )
                    
                    st.plotly_chart(fig_type_bar, use_container_width=True)
            
            # --- AI智能分析按钮 ---
            st.markdown("---")
            api_key = get_api_key()
            if st.button("让AI分析涨幅排行有什么规律"):
                if not api_key:
                    st.warning("未检测到API Key，请前往【API密钥配置】页面设置，否则无法使用AI分析功能。")
                else:
                    prompt = "请分析以下ETF近一月涨幅排行前20的数据，指出行业、风格、主题等特征和投资机会，简明总结规律：\n" + df_sorted.head(20).to_csv(index=False)
                    with st.spinner("AI正在分析，请稍候..."):
                        result = ai_chat(prompt, api_key=api_key)
                    st.markdown("#### AI分析结果：")
                    st.write(result)
        else:
            st.error("数据中未找到'近1月'字段")
            st.write("可用字段：", df.columns.tolist())
    except Exception as e:
        st.error(f"获取数据失败: {e}")
        st.write("请检查网络连接或稍后重试") 