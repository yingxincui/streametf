# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data import get_etf_list, fetch_etf_data_with_retry
import plotly.graph_objects as go
from utils import get_etf_options_with_favorites

def black_thursday_analysis():
    st.set_page_config(page_title="黑色星期四效应分析", page_icon="📅", layout="wide")
    
    st.title("📅 黑色星期四效应分析")
    st.markdown("验证黑色星期四效应：分析周一到周五的涨跌趋势")
    
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
        
        if st.button("开始分析", type="primary"):
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
                    
                    # 添加星期几信息
                    df['weekday'] = df.index.weekday
                    df['weekday_cn'] = df['weekday'].map({
                        0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五'
                    })
                    
                    # 按星期几分组统计
                    weekday_stats = df.groupby('weekday_cn')['pct_change'].agg([
                        'count', 'mean', 'std',
                        lambda x: (x > 0).sum(),  # 上涨天数
                        lambda x: (x < 0).sum()   # 下跌天数
                    ]).round(4)
                    
                    weekday_stats.columns = ['交易天数', '平均收益率', '标准差', '上涨天数', '下跌天数']
                    weekday_stats['胜率'] = (weekday_stats['上涨天数'] / weekday_stats['交易天数'] * 100).round(2)
                    weekday_stats['平均收益率(%)'] = (weekday_stats['平均收益率'] * 100).round(4)
                    
                    # 获取ETF名称
                    etf_name = etf_list[etf_list['symbol'] == selected_etf]['name'].values[0]
                    
                    # 存储结果
                    st.session_state.black_thursday_results = {
                        'df': df,
                        'weekday_stats': weekday_stats,
                        'selected_etf': selected_etf,
                        'etf_name': etf_name,
                        'start_date': start_date,
                        'end_date': end_date
                    }
                    
                    st.success("✅ 分析完成！")
                    
                except Exception as e:
                    st.error(f"❌ 分析过程中发生错误: {str(e)}")
    
    with right_col:
        if 'black_thursday_results' in st.session_state:
            results = st.session_state.black_thursday_results
            
            st.header("黑色星期四效应分析结果")
            
            # 主要统计指标
            st.subheader("📊 周内各交易日统计")
            
            # 重新排序列
            weekday_order = ['周一', '周二', '周三', '周四', '周五']
            stats_display = results['weekday_stats'].reindex(weekday_order)
            
            # 显示统计表格
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**基础统计指标**")
                basic_stats = stats_display[['交易天数', '平均收益率(%)', '胜率']].copy()
                basic_stats['胜率'] = basic_stats['胜率'].astype(str) + '%'
                basic_stats['平均收益率(%)'] = basic_stats['平均收益率(%)'].astype(str) + '%'
                st.dataframe(basic_stats, use_container_width=True)
            
            with col2:
                st.markdown("**涨跌统计**")
                extreme_stats = stats_display[['上涨天数', '下跌天数', '标准差']].copy()
                extreme_stats['标准差'] = (extreme_stats['标准差'] * 100).round(2).astype(str) + '%'
                st.dataframe(extreme_stats, use_container_width=True)
            
            # 可视化分析
            st.subheader("📈 周内趋势可视化")
            
            # 1. 平均收益率柱状图
            fig_avg_return = go.Figure()
            
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            
            fig_avg_return.add_trace(go.Bar(
                x=stats_display.index,
                y=stats_display['平均收益率(%)'],
                marker_color=colors,
                text=stats_display['平均收益率(%)'].round(4).astype(str) + '%',
                textposition='auto',
                name='平均收益率'
            ))
            
            fig_avg_return.update_layout(
                title=f"周内各交易日平均收益率 - {results['etf_name']}",
                xaxis_title="星期",
                yaxis_title="平均收益率 (%)",
                showlegend=False
            )
            
            st.plotly_chart(fig_avg_return, use_container_width=True)
            
            # 2. 胜率对比图
            fig_win_rate = go.Figure()
            
            fig_win_rate.add_trace(go.Bar(
                x=stats_display.index,
                y=stats_display['胜率'],
                marker_color=colors,
                text=stats_display['胜率'].astype(str) + '%',
                textposition='auto',
                name='胜率'
            ))
            
            # 添加50%基准线
            fig_win_rate.add_hline(y=50, line_dash="dash", line_color="red", 
                                 annotation_text="50%基准线")
            
            fig_win_rate.update_layout(
                title=f"周内各交易日胜率对比 - {results['etf_name']}",
                xaxis_title="星期",
                yaxis_title="胜率 (%)",
                showlegend=False
            )
            
            st.plotly_chart(fig_win_rate, use_container_width=True)
            
            # 3. 累计涨跌幅趋势图
            st.subheader("累计涨跌幅趋势图")
            
            # 计算各交易日的累计收益
            fig_cumulative = go.Figure()
            
            for i, day in enumerate(weekday_order):
                day_data = results['df'][results['df']['weekday_cn'] == day]
                if not day_data.empty:
                    # 计算累计收益
                    cumulative_return = (1 + day_data['pct_change']).cumprod()
                    cumulative_pct = (cumulative_return - 1) * 100
                    
                    fig_cumulative.add_trace(go.Scatter(
                        x=day_data.index,
                        y=cumulative_pct,
                        mode='lines',
                        name=day,
                        line=dict(color=colors[i], width=2),
                        hovertemplate=f'{day}<br>日期: %{{x}}<br>累计收益: %{{y:.2f}}%'
                    ))
            
            fig_cumulative.update_layout(
                title=f"周内各交易日累计涨跌幅趋势 - {results['etf_name']}",
                xaxis_title="日期",
                yaxis_title="累计收益率 (%)",
                hovermode='x unified',
                legend=dict(font=dict(size=12))
            )
            
            st.plotly_chart(fig_cumulative, use_container_width=True)
            
            # 4. 箱线图显示分布
            st.subheader("收益率分布箱线图")
            
            # 准备箱线图数据
            box_data = []
            for day in weekday_order:
                day_data = results['df'][results['df']['weekday_cn'] == day]['pct_change'] * 100
                if not day_data.empty:
                    box_data.append(go.Box(
                        y=day_data,
                        name=day,
                        boxpoints='outliers',
                        jitter=0.3,
                        pointpos=-1.8
                    ))
            
            fig_box = go.Figure(data=box_data)
            fig_box.update_layout(
                title=f"周内各交易日收益率分布 - {results['etf_name']}",
                yaxis_title="日收益率 (%)",
                showlegend=False
            )
            
            st.plotly_chart(fig_box, use_container_width=True)
            
            # 关键发现和结论
            st.subheader("🔍 关键发现")
            
            # 找出表现最好和最差的交易日
            best_day = stats_display['平均收益率(%)'].idxmax()
            worst_day = stats_display['平均收益率(%)'].idxmin()
            best_return = stats_display.loc[best_day, '平均收益率(%)']
            worst_return = stats_display.loc[worst_day, '平均收益率(%)']
            
            # 找出胜率最高和最低的交易日
            best_win_day = stats_display['胜率'].idxmax()
            worst_win_day = stats_display['胜率'].idxmin()
            best_win_rate = stats_display.loc[best_win_day, '胜率']
            worst_win_rate = stats_display.loc[worst_win_day, '胜率']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**收益率表现**")
                st.info(f"""
                🏆 **最佳交易日**: {best_day} ({best_return:.4f}%)
                
                📉 **最差交易日**: {worst_day} ({worst_return:.4f}%)
                
                📊 **差异**: {best_return - worst_return:.4f}%
                """)
            
            with col2:
                st.markdown("**胜率表现**")
                st.info(f"""
                🎯 **最高胜率**: {best_win_day} ({best_win_rate:.1f}%)
                
                ❌ **最低胜率**: {worst_win_day} ({worst_win_rate:.1f}%)
                
                📊 **差异**: {best_win_rate - worst_win_rate:.1f}%
                """)
            
            # 黑色星期四效应验证
            st.subheader("🖤 黑色星期四效应验证")
            
            thursday_stats = stats_display.loc['周四']
            avg_thursday_return = thursday_stats['平均收益率(%)']
            thursday_win_rate = thursday_stats['胜率']
            
            # 计算周四相对于其他天的表现
            other_days_avg = stats_display[stats_display.index != '周四']['平均收益率(%)'].mean()
            other_days_win_rate = stats_display[stats_display.index != '周四']['胜率'].mean()
            
            thursday_rank = stats_display['平均收益率(%)'].rank(ascending=False).loc['周四']
            total_days = len(stats_display)
            
            st.info(f"""
            **周四表现分析：**
            
            📈 **平均收益率**: {avg_thursday_return:.4f}% (排名: {thursday_rank:.0f}/{total_days})
            
            🎯 **胜率**: {thursday_win_rate:.1f}%
            
            📊 **相对表现**:
            - 收益率 vs 其他日平均: {avg_thursday_return - other_days_avg:.4f}%
            - 胜率 vs 其他日平均: {thursday_win_rate - other_days_win_rate:.1f}%
            
            💡 **结论**: {'存在黑色星期四效应' if avg_thursday_return < other_days_avg else '不存在明显的黑色星期四效应'}
            """)
            
            # 投资建议
            st.subheader("💡 投资建议")
            
            if avg_thursday_return < other_days_avg:
                st.warning("""
                **基于分析结果的投资建议：**
                
                🚨 **周四效应存在**：周四平均收益率低于其他交易日
                
                📋 **策略建议**：
                - 避免在周四进行大额买入操作
                - 考虑在周四进行定投，利用可能的低点
                - 周四适合进行技术分析和观察市场情绪
                - 其他交易日（特别是表现较好的交易日）更适合主动投资
                """)
            else:
                st.success("""
                **基于分析结果的投资建议：**
                
                ✅ **周四效应不明显**：周四表现与其他交易日相当或更好
                
                📋 **策略建议**：
                - 可以正常在周四进行投资操作
                - 关注整体市场趋势而非特定交易日
                - 保持长期投资策略，避免过度关注短期波动
                """)

if __name__ == "__main__":
    black_thursday_analysis()
