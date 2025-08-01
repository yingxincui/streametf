import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from data import get_etf_list, fetch_etf_data_with_retry
import plotly.graph_objects as go
import plotly.express as px
from utils import get_etf_options_with_favorites

def extreme_value_analysis():
    st.set_page_config(page_title="极值分析", page_icon="📈", layout="wide")
    
    st.title("📈 极值分析 - 错过最佳交易日的影响")
    st.markdown("分析如果错过历史涨幅最大的N天，对一次性投资总收益的影响")
    
    # 获取ETF列表
    etf_list = get_etf_list()
    if etf_list.empty:
        st.error("无法获取ETF列表")
        return
    
    # 创建左右两列布局
    left_col, right_col = st.columns([1, 2.5])
    
    with left_col:
        st.header("分析参数设置")
        
        # ETF选择
        etf_options = get_etf_options_with_favorites(etf_list)
        selected_etf = st.selectbox(
            "选择ETF",
            options=etf_options,
            format_func=lambda x: f"{x} - {etf_list[etf_list['symbol'] == x]['name'].values[0]}"
        )
        
        # 时间范围选择
        period = st.radio(
            "选择分析区间",
            ["近三年", "近五年", "近十年", "全部数据"],
            index=1,
            horizontal=True
        )
        
        end_date = datetime.now() - timedelta(days=1)
        min_start = datetime(2010, 1, 1)
        
        if selected_etf:
            df = fetch_etf_data_with_retry(selected_etf, min_start, end_date, etf_list)
            if not df.empty:
                min_start = max(df.index.min(), datetime(2010, 1, 1))
        
        if period == "近三年":
            start_date = max(end_date - timedelta(days=365*3), min_start)
        elif period == "近五年":
            start_date = max(end_date - timedelta(days=365*5), min_start)
        elif period == "近十年":
            start_date = max(end_date - timedelta(days=365*10), min_start)
        else:
            start_date = min_start
            
        st.info(f"分析区间：{start_date.date()} ~ {end_date.date()}")
        
        # 错过天数设置
        missed_days = st.slider("错过涨幅最大的天数", 1, 50, 10)
        
        # 初始投资金额
        initial_investment = st.number_input("初始投资金额 (元)", min_value=1000, value=10000, step=1000)
        
        if st.button("开始极值分析", type="primary"):
            with st.spinner("正在分析..."):
                try:
                    # 获取数据
                    df = fetch_etf_data_with_retry(selected_etf, start_date, end_date, etf_list)
                    if df.empty:
                        st.error("无法获取数据")
                        return
                    
                    # 计算日收益率
                    df['pct_change'] = df.iloc[:, 0].pct_change()
                    df = df.dropna()
                    
                    # 找出涨幅最大的N天
                    top_gain_days = df['pct_change'].nlargest(missed_days)
                    
                    # 计算正常持有收益
                    start_price = df.iloc[0, 0]
                    end_price = df.iloc[-1, 0]
                    normal_return = (end_price / start_price - 1) * 100
                    normal_value = initial_investment * (1 + normal_return / 100)
                    
                    # 模拟错过N天的收益
                    df_sim = df.copy()
                    df_sim.loc[top_gain_days.index, 'pct_change'] = 0
                    df_sim['cumulative_return'] = (1 + df_sim['pct_change']).cumprod()
                    sim_end_price = start_price * df_sim['cumulative_return'].iloc[-1]
                    sim_return = (sim_end_price / start_price - 1) * 100
                    sim_value = initial_investment * (1 + sim_return / 100)
                    
                    # 计算差异
                    return_diff = normal_return - sim_return
                    value_diff = normal_value - sim_value
                    
                    # 存储结果
                    st.session_state.extreme_analysis_results = {
                        'df': df,
                        'top_gain_days': top_gain_days,
                        'normal_return': normal_return,
                        'sim_return': sim_return,
                        'return_diff': return_diff,
                        'normal_value': normal_value,
                        'sim_value': sim_value,
                        'value_diff': value_diff,
                        'initial_investment': initial_investment,
                        'missed_days': missed_days,
                        'selected_etf': selected_etf,
                        'start_date': start_date,
                        'end_date': end_date
                    }
                    
                    st.success("✅ 极值分析完成！")
                    
                except Exception as e:
                    st.error(f"❌ 分析过程中发生错误: {str(e)}")
    
    with right_col:
        if 'extreme_analysis_results' in st.session_state:
            results = st.session_state.extreme_analysis_results
            
            st.header("极值分析结果")
            
            # 主要指标展示
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("正常持有总收益率", f"{results['normal_return']:.2f}%")
            with col2:
                st.metric(f"错过{results['missed_days']}天总收益率", 
                         f"{results['sim_return']:.2f}%",
                         delta=f"-{results['return_diff']:.2f}%",
                         delta_color="inverse")
            with col3:
                st.metric("收益损失", f"{results['return_diff']:.2f}%")
            
            # 投资价值对比
            st.subheader("投资价值对比")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("正常持有最终价值", f"{results['normal_value']:,.2f} 元")
            with col2:
                st.metric(f"错过{results['missed_days']}天最终价值", 
                         f"{results['sim_value']:,.2f} 元",
                         delta=f"-{results['value_diff']:,.2f} 元",
                         delta_color="inverse")
            with col3:
                st.metric("价值损失", f"{results['value_diff']:,.2f} 元")
            
            # 涨幅最大的N天详情
            st.subheader(f"涨幅最大的{results['missed_days']}天详情")
            top_days_df = pd.DataFrame({
                '日期': results['top_gain_days'].index,
                '涨幅(%)': results['top_gain_days'].values * 100
            }).sort_values('涨幅(%)', ascending=False)
            
            top_days_df['日期'] = pd.to_datetime(top_days_df['日期']).dt.strftime('%Y-%m-%d')
            top_days_df['涨幅(%)'] = top_days_df['涨幅(%)'].round(2)
            
            st.dataframe(top_days_df.style.format({'涨幅(%)': '{:.2f}%'}), use_container_width=True)
            
            # 累计收益对比图
            st.subheader("累计收益对比")
            
            # 计算正常累计收益
            normal_cumulative = (1 + results['df']['pct_change']).cumprod()
            
            # 计算错过N天的累计收益
            sim_df = results['df'].copy()
            sim_df.loc[results['top_gain_days'].index, 'pct_change'] = 0
            sim_cumulative = (1 + sim_df['pct_change']).cumprod()
            
            fig_cumulative = go.Figure()
            
            # 正常累计收益
            fig_cumulative.add_trace(go.Scatter(
                x=normal_cumulative.index,
                y=(normal_cumulative - 1) * 100,
                mode='lines',
                name='正常持有',
                line=dict(color='blue', width=2)
            ))
            
            # 错过N天的累计收益
            fig_cumulative.add_trace(go.Scatter(
                x=sim_cumulative.index,
                y=(sim_cumulative - 1) * 100,
                mode='lines',
                name=f'错过{results["missed_days"]}天',
                line=dict(color='red', width=2, dash='dash')
            ))
            
            # 标记涨幅最大的N天
            fig_cumulative.add_trace(go.Scatter(
                x=results['top_gain_days'].index,
                y=(normal_cumulative.loc[results['top_gain_days'].index] - 1) * 100,
                mode='markers',
                name=f'涨幅最大的{results["missed_days"]}天',
                marker=dict(color='red', size=8, symbol='star')
            ))
            
            fig_cumulative.update_layout(
                title="累计收益对比",
                xaxis_title="日期",
                yaxis_title="累计收益率 (%)",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_cumulative, use_container_width=True)
            
            # 关键结论
            st.subheader("关键结论")
            st.info(f"""
            📊 **分析结论：**
            
            • 如果错过涨幅最大的 **{results['missed_days']}天**，总收益率将从 **{results['normal_return']:.2f}%** 降至 **{results['sim_return']:.2f}%**
            
            • 收益损失高达 **{results['return_diff']:.2f}%**，相当于损失 **{results['value_diff']:,.2f}元**
            
            • 这{results['missed_days']}天仅占总交易日的 **{results['missed_days']/len(results['df'])*100:.1f}%**，但贡献了巨大的收益
            
            💡 **投资启示：**
            
            • 市场择时极其困难，错过少数关键交易日可能导致收益大幅下降
            • 长期持有策略比频繁交易更可靠
            • 分散投资可以降低错过单日大涨的风险
            """)

if __name__ == "__main__":
    extreme_value_analysis() 