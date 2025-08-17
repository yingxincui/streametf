import streamlit as st
import pandas as pd
import akshare as ak
import plotly.graph_objects as go
import plotly.express as px

st.title("场内基金筛选（东方财富网）")

st.markdown("""
本页可筛选场内交易基金，默认条件：成立超5年，年化收益率（成立来）大于10%。数据来源：东方财富网。
""")

@st.cache_data(ttl=3600)
def get_exchange_fund():
    return ak.fund_exchange_rank_em()

df = get_exchange_fund()

# 筛选条件
min_years = st.number_input("最短成立年限(年)", min_value=0, max_value=30, value=5)
min_cagr = st.number_input("最低年化收益率(%)", min_value=0.0, max_value=100.0, value=10.0, step=0.1)

df = df.copy()
df['成立来'] = pd.to_numeric(df['成立来'], errors='coerce')
df['成立日期'] = pd.to_datetime(df['成立日期'], errors='coerce')
df['成立年限'] = (pd.to_datetime('today') - df['成立日期']).dt.days / 365.25
# 用成立来总收益和成立年限算年化收益率（CAGR）
def calc_cagr(total_return, years):
    try:
        if pd.isna(total_return) or pd.isna(years) or years <= 0:
            return None
        total_return = total_return / 100
        if total_return <= -1:
            return None
        cagr = (1 + total_return) ** (1/years) - 1
        return cagr * 100
    except:
        return None
df['成立来年化(%)'] = df.apply(lambda row: calc_cagr(row['成立来'], row['成立年限']), axis=1)

filtered = df[(df['成立年限'] >= min_years) & (df['成立来年化(%)'] >= min_cagr) & (~df['成立来年化(%)'].isna())]

st.info(f"共筛选出 {len(filtered)} 只场内基金，满足：成立超{min_years}年，年化收益率大于{min_cagr}%")

cols_to_show = ['基金代码','基金简称','类型','成立年限','成立来','成立来年化(%)','单位净值','累计净值','近1年','近3年','手续费']
cols_exist = [col for col in cols_to_show if col in filtered.columns]
st.dataframe(filtered[cols_exist]
    .sort_values('成立来年化(%)', ascending=False)
    .style.format({'成立年限': '{:.1f}','成立来': '{:.2f}%','成立来年化(%)': '{:.2f}%','单位净值': '{:.3f}','累计净值': '{:.3f}','近1年': '{:.2f}%','近3年': '{:.2f}%'}),
    use_container_width=True)

# 添加排行榜图表
if len(filtered) > 0:
    st.subheader("📊 排行榜可视化分析")
    
    # 1. 年化收益率排行榜（前20名）
    st.write("**🏆 年化收益率排行榜（前20名）**")
    
    top_20_cagr = filtered.nlargest(20, '成立来年化(%)')
    
    fig_cagr = go.Figure()
    
    # 设置颜色：根据年化收益率设置渐变色
    colors = ['red' if x >= 20 else 'orange' if x >= 15 else 'gold' if x >= 10 else 'lightblue' for x in top_20_cagr['成立来年化(%)']]
    
    fig_cagr.add_trace(go.Bar(
        y=top_20_cagr['基金简称'].str[:20],  # 截取前20个字符
        x=top_20_cagr['成立来年化(%)'],
        orientation='h',
        marker_color=colors,
        opacity=0.8,
        hovertemplate='%{y}<br>年化收益率: %{x:.2f}%<br>成立年限: %{text:.1f}年<extra></extra>',
        text=top_20_cagr['成立年限']
    ))
    
    fig_cagr.update_layout(
        title="年化收益率排行榜（前20名）",
        xaxis_title="年化收益率 (%)",
        yaxis_title="基金名称",
        height=500,
        showlegend=False,
        template='plotly_white'
    )
    
    st.plotly_chart(fig_cagr, use_container_width=True)
    
    # 2. 成立年限排行榜（前20名）
    st.write("**⏰ 成立年限排行榜（前20名）**")
    
    top_20_years = filtered.nlargest(20, '成立年限')
    
    fig_years = go.Figure()
    
    fig_years.add_trace(go.Bar(
        y=top_20_years['基金简称'].str[:20],
        x=top_20_years['成立年限'],
        orientation='h',
        marker_color='lightgreen',
        opacity=0.8,
        hovertemplate='%{y}<br>成立年限: %{x:.1f}年<br>年化收益率: %{text:.2f}%<extra></extra>',
        text=top_20_years['成立来年化(%)']
    ))
    
    fig_years.update_layout(
        title="成立年限排行榜（前20名）",
        xaxis_title="成立年限（年）",
        yaxis_title="基金名称",
        height=500,
        showlegend=False,
        template='plotly_white'
    )
    
    st.plotly_chart(fig_years, use_container_width=True)
    
    # 3. 近1年表现排行榜（前20名）
    if '近1年' in filtered.columns:
        st.write("**📈 近1年表现排行榜（前20名）**")
        
        # 处理近1年数据
        filtered['近1年'] = pd.to_numeric(filtered['近1年'], errors='coerce')
        top_20_1y = filtered.nlargest(20, '近1年').dropna(subset=['近1年'])
        
        if len(top_20_1y) > 0:
            fig_1y = go.Figure()
            
            # 设置颜色：正收益红色，负收益绿色
            colors = ['red' if x >= 0 else 'green' for x in top_20_1y['近1年']]
            
            fig_1y.add_trace(go.Bar(
                y=top_20_1y['基金简称'].str[:20],
                x=top_20_1y['近1年'],
                orientation='h',
                marker_color=colors,
                opacity=0.8,
                hovertemplate='%{y}<br>近1年涨幅: %{x:.2f}%<br>年化收益率: %{text:.2f}%<extra></extra>',
                text=top_20_1y['成立来年化(%)']
            ))
            
            fig_1y.update_layout(
                title="近1年表现排行榜（前20名）",
                xaxis_title="近1年涨幅 (%)",
                yaxis_title="基金名称",
                height=500,
                showlegend=False,
                template='plotly_white'
            )
            
            st.plotly_chart(fig_1y, use_container_width=True)
    
    # 4. 近3年表现排行榜（前20名）
    if '近3年' in filtered.columns:
        st.write("**📊 近3年表现排行榜（前20名）**")
        
        # 处理近3年数据
        filtered['近3年'] = pd.to_numeric(filtered['近3年'], errors='coerce')
        top_20_3y = filtered.nlargest(20, '近3年').dropna(subset=['近3年'])
        
        if len(top_20_3y) > 0:
            fig_3y = go.Figure()
            
            # 设置颜色：正收益红色，负收益绿色
            colors = ['red' if x >= 0 else 'green' for x in top_20_3y['近3年']]
            
            fig_3y.add_trace(go.Bar(
                y=top_20_3y['基金简称'].str[:20],
                x=top_20_3y['近3年'],
                orientation='h',
                marker_color=colors,
                opacity=0.8,
                hovertemplate='%{y}<br>近3年涨幅: %{x:.2f}%<br>年化收益率: %{text:.2f}%<extra></extra>',
                text=top_20_3y['成立来年化(%)']
            ))
            
            fig_3y.update_layout(
                title="近3年表现排行榜（前20名）",
                xaxis_title="近3年涨幅 (%)",
                yaxis_title="基金名称",
                height=500,
                showlegend=False,
                template='plotly_white'
            )
            
            st.plotly_chart(fig_3y, use_container_width=True)
    
    # 5. 基金类型分布分析
    if '类型' in filtered.columns:
        st.write("**🏷️ 基金类型分析**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 类型分布饼图
            type_counts = filtered['类型'].value_counts()
            
            fig_type_pie = go.Figure(data=[go.Pie(
                labels=type_counts.index,
                values=type_counts.values,
                hole=0.3,
                textinfo='label+percent',
                textposition='inside',
                hovertemplate='<b>%{label}</b><br>数量: %{value}<br>占比: %{percent}<extra></extra>'
            )])
            
            fig_type_pie.update_layout(
                title="筛选后基金类型分布",
                height=400,
                showlegend=True
            )
            
            st.plotly_chart(fig_type_pie, use_container_width=True)
        
        with col2:
            # 各类型平均年化收益率对比
            type_avg = filtered.groupby('类型')['成立来年化(%)'].agg(['mean', 'count']).reset_index()
            type_avg = type_avg.sort_values('mean', ascending=False)
            
            fig_type_bar = go.Figure()
            
            fig_type_bar.add_trace(go.Bar(
                x=type_avg['类型'],
                y=type_avg['mean'],
                marker_color='lightcoral',
                opacity=0.8,
                hovertemplate='%{x}<br>平均年化收益率: %{y:.2f}%<br>基金数量: %{text}<extra></extra>',
                text=type_avg['count']
            ))
            
            fig_type_bar.update_layout(
                title="各类型基金平均年化收益率",
                xaxis_title="基金类型",
                yaxis_title="平均年化收益率 (%)",
                height=400,
                template='plotly_white',
                xaxis=dict(tickangle=45)
            )
            
            st.plotly_chart(fig_type_bar, use_container_width=True)
    
    # 6. 年化收益率分布直方图
    st.write("**📊 年化收益率分布**")
    
    fig_hist = go.Figure()
    
    fig_hist.add_trace(go.Histogram(
        x=filtered['成立来年化(%)'],
        nbinsx=20,
        name='基金数量',
        marker_color='lightblue',
        opacity=0.7,
        hovertemplate='收益率区间: %{x:.1f}%<br>基金数量: %{y}<extra></extra>'
    ))
    
    # 添加平均线
    mean_cagr = filtered['成立来年化(%)'].mean()
    fig_hist.add_vline(x=mean_cagr, line_dash="dash", line_color="red", 
                       annotation_text=f"平均值: {mean_cagr:.2f}%")
    
    fig_hist.update_layout(
        title="年化收益率分布直方图",
        xaxis_title="年化收益率 (%)",
        yaxis_title="基金数量",
        height=400,
        showlegend=False,
        template='plotly_white'
    )
    
    st.plotly_chart(fig_hist, use_container_width=True)
    
    # 7. 成立年限vs年化收益率散点图
    st.write("**📈 成立年限vs年化收益率关系**")
    
    fig_scatter = go.Figure()
    
    fig_scatter.add_trace(go.Scatter(
        x=filtered['成立年限'],
        y=filtered['成立来年化(%)'],
        mode='markers',
        marker=dict(
            size=8,
            color=filtered['成立来年化(%)'],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="年化收益率")
        ),
        text=filtered['基金简称'],
        hovertemplate='<b>%{text}</b><br>成立年限: %{x:.1f}年<br>年化收益率: %{y:.2f}%<extra></extra>'
    ))
    
    # 添加参考线
    fig_scatter.add_hline(y=min_cagr, line_dash="dash", line_color="orange", 
                          annotation_text=f"筛选阈值: {min_cagr}%")
    
    fig_scatter.update_layout(
        title="成立年限vs年化收益率散点图（颜色表示年化收益率）",
        xaxis_title="成立年限（年）",
        yaxis_title="年化收益率 (%)",
        height=500,
        template='plotly_white'
    )
    
    st.plotly_chart(fig_scatter, use_container_width=True)
else:
    st.warning("没有找到满足筛选条件的基金，请调整筛选条件") 