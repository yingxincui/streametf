import streamlit as st
import pandas as pd
import akshare as ak
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="红利基金筛选", page_icon="💰", layout="wide")

st.title("红利基金筛选（场内，东方财富网）")

st.markdown("""
本页筛选场内红利基金（名称含“红利”），默认条件：成立超5年，年化收益率（成立来）大于10%。数据来源：东方财富网。
""")

@st.cache_data(ttl=3600)
def get_exchange_fund():
    return ak.fund_exchange_rank_em()

df = get_exchange_fund()

# 只保留名称含“红利”的基金
df = df[df['基金简称'].str.contains('红利', na=False)]

# 筛选条件
min_years = st.number_input("最短成立年限(年)", min_value=0, max_value=30, value=5)
min_cagr = st.number_input("最低年化收益率(%)", min_value=0.0, max_value=100.0, value=10.0, step=0.1)

df = df.copy()
df['成立来'] = pd.to_numeric(df['成立来'], errors='coerce')
df['成立日期'] = pd.to_datetime(df['成立日期'], errors='coerce')
df['成立年限'] = (pd.to_datetime('today') - df['成立日期']).dt.days / 365.25

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

st.info(f"共筛选出 {len(filtered)} 只红利基金，满足：成立超{min_years}年，年化收益率大于{min_cagr}%")

cols_to_show = ['基金代码','基金简称','类型','成立年限','成立来','成立来年化(%)','单位净值','累计净值','近1年','近3年','手续费']
cols_exist = [col for col in cols_to_show if col in filtered.columns]
st.dataframe(filtered[cols_exist]
    .sort_values('成立来年化(%)', ascending=False)
    .style.format({'成立年限': '{:.1f}','成立来': '{:.2f}%','成立来年化(%)': '{:.2f}%','单位净值': '{:.3f}','累计净值': '{:.3f}','近1年': '{:.2f}%','近3年': '{:.2f}%'}),
    use_container_width=True)

# 添加年化收益率可视化图表
if len(filtered) > 0:
    st.subheader("📊 年化收益率可视化分析")
    
    # 1. 年化收益率排行榜（横向柱状图）
    st.write("**🏆 年化收益率排行榜**")
    
    # 获取所有基金（红利基金通常数量不多）
    sorted_funds = filtered.sort_values('成立来年化(%)', ascending=False)
    
    fig_cagr = go.Figure()
    
    # 设置颜色：根据年化收益率设置渐变色
    colors = ['red' if x >= 20 else 'orange' if x >= 15 else 'gold' if x >= 10 else 'lightblue' for x in sorted_funds['成立来年化(%)']]
    
    fig_cagr.add_trace(go.Bar(
        y=sorted_funds['基金简称'].str[:25],  # 截取前25个字符
        x=sorted_funds['成立来年化(%)'],
        orientation='h',
        marker_color=colors,
        opacity=0.8,
        hovertemplate='%{y}<br>年化收益率: %{x:.2f}%<br>成立年限: %{text:.1f}年<extra></extra>',
        text=sorted_funds['成立年限']
    ))
    
    fig_cagr.update_layout(
        title=f"红利基金年化收益率排行榜（阈值>{min_cagr}%）",
        xaxis_title="年化收益率 (%)",
        yaxis_title="基金名称",
        height=max(400, len(sorted_funds) * 25),  # 根据基金数量动态调整高度
        showlegend=False,
        template='plotly_white'
    )
    
    st.plotly_chart(fig_cagr, use_container_width=True)
    
    # 2. 年化收益率分布直方图
    st.write("**📈 年化收益率分布**")
    
    fig_dist = go.Figure()
    
    fig_dist.add_trace(go.Histogram(
        x=filtered['成立来年化(%)'],
        nbinsx=min(15, len(filtered)),  # 根据基金数量调整bins
        name='基金数量',
        marker_color='lightcoral',
        opacity=0.7,
        hovertemplate='收益率区间: %{x:.1f}%<br>基金数量: %{y}<extra></extra>'
    ))
    
    # 添加平均线和阈值线
    mean_cagr = filtered['成立来年化(%)'].mean()
    fig_dist.add_vline(x=mean_cagr, line_dash="dash", line_color="blue", 
                       annotation_text=f"平均值: {mean_cagr:.2f}%")
    fig_dist.add_vline(x=min_cagr, line_dash="dash", line_color="red", 
                       annotation_text=f"阈值: {min_cagr}%")
    
    fig_dist.update_layout(
        title="年化收益率分布直方图",
        xaxis_title="年化收益率 (%)",
        yaxis_title="基金数量",
        height=400,
        showlegend=False,
        template='plotly_white'
    )
    
    st.plotly_chart(fig_dist, use_container_width=True)
    
    # 3. 基金类型分析
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
                title="筛选后红利基金类型分布",
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
                title="各类型红利基金平均年化收益率",
                xaxis_title="基金类型",
                yaxis_title="平均年化收益率 (%)",
                height=400,
                template='plotly_white',
                xaxis=dict(tickangle=45)
            )
            
            st.plotly_chart(fig_type_bar, use_container_width=True)
    
    # 4. 成立年限vs年化收益率散点图
    st.write("**📈 成立年限vs年化收益率关系**")
    
    fig_scatter = go.Figure()
    
    fig_scatter.add_trace(go.Scatter(
        x=filtered['成立年限'],
        y=filtered['成立来年化(%)'],
        mode='markers',
        marker=dict(
            size=10,
            color=filtered['成立来年化(%)'],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="年化收益率")
        ),
        text=filtered['基金简称'],
        hovertemplate='<b>%{text}</b><br>成立年限: %{x:.1f}年<br>年化收益率: %{y:.2f}%<extra></extra>'
    ))
    
    # 添加参考线
    fig_scatter.add_hline(y=min_cagr, line_dash="dash", line_color="red", 
                          annotation_text=f"筛选阈值: {min_cagr}%")
    
    fig_scatter.update_layout(
        title="成立年限vs年化收益率散点图（颜色表示年化收益率）",
        xaxis_title="成立年限（年）",
        yaxis_title="年化收益率 (%)",
        height=500,
        template='plotly_white'
    )
    
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    # 5. 统计信息卡片
    st.write("**📊 统计信息**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("筛选基金数量", len(filtered))
    
    with col2:
        st.metric("平均年化收益率", f"{mean_cagr:.2f}%")
    
    with col3:
        max_cagr = filtered['成立来年化(%)'].max()
        st.metric("最高年化收益率", f"{max_cagr:.2f}%")
    
    with col4:
        min_cagr_filtered = filtered['成立来年化(%)'].min()
        st.metric("最低年化收益率", f"{min_cagr_filtered:.2f}%")
    
    # 6. 红利基金特色分析
    st.write("**💎 红利基金特色分析**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 成立年限分布
        st.write("**⏰ 成立年限分布**")
        
        fig_years = go.Figure()
        
        fig_years.add_trace(go.Histogram(
            x=filtered['成立年限'],
            nbinsx=min(10, len(filtered)),
            name='基金数量',
            marker_color='lightgreen',
            opacity=0.7,
            hovertemplate='年限区间: %{x:.1f}年<br>基金数量: %{y}<extra></extra>'
        ))
        
        fig_years.update_layout(
            title="红利基金成立年限分布",
            xaxis_title="成立年限（年）",
            yaxis_title="基金数量",
            height=300,
            showlegend=False,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_years, use_container_width=True)
    
    with col2:
        # 近1年表现（如果有数据）
        if '近1年' in filtered.columns:
            st.write("**📈 近1年表现分布**")
            
            # 处理近1年数据
            filtered['近1年'] = pd.to_numeric(filtered['近1年'], errors='coerce')
            valid_1y = filtered.dropna(subset=['近1年'])
            
            if len(valid_1y) > 0:
                fig_1y = go.Figure()
                
                # 设置颜色：正收益红色，负收益绿色
                colors = ['red' if x >= 0 else 'green' for x in valid_1y['近1年']]
                
                fig_1y.add_trace(go.Bar(
                    x=valid_1y['基金简称'].str[:20],
                    y=valid_1y['近1年'],
                    marker_color=colors,
                    opacity=0.8,
                    hovertemplate='%{x}<br>近1年涨幅: %{y:.2f}%<extra></extra>'
                ))
                
                fig_1y.update_layout(
                    title="红利基金近1年表现",
                    xaxis_title="基金名称",
                    yaxis_title="近1年涨幅 (%)",
                    height=300,
                    template='plotly_white',
                    xaxis=dict(tickangle=45)
                )
                
                st.plotly_chart(fig_1y, use_container_width=True)
            else:
                st.info("暂无有效的近1年数据")
        else:
            st.info("数据中未包含近1年字段")
else:
    st.warning("没有找到满足筛选条件的红利基金，请调整筛选条件") 