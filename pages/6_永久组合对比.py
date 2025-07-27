import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from data import get_etf_list
from portfolio import calculate_portfolio

# 永久组合对比页面

def calculate_all_permanent_portfolios(start_date, end_date, initial_investment, etf_list):
    """计算四种永久组合的指标"""
    portfolios = {
        "经典版（含纳指）": {
            '518880': '黄金ETF (25%)',
            '159941': '纳指ETF (25%)',
            '511260': '国债ETF (25%)',
            '511830': '货币ETF (25%)'
        },
        "创业板版（含创业板）": {
            '518880': '黄金ETF (25%)',
            '159915': '创业板ETF (25%)',
            '511260': '国债ETF (25%)',
            '511830': '货币ETF (25%)'
        },
        "红利低波版": {
            '518880': '黄金ETF (25%)',
            '512890': '红利低波ETF (25%)',
            '511260': '国债ETF (25%)',
            '511830': '货币ETF (25%)'
        },
        "激进版（含纳指+红利低波）": {
            '518880': '黄金ETF (25%)',
            '512890': '红利低波ETF (25%)',
            '159941': '纳指ETF (25%)',
            '511260': '国债ETF (25%)'
        }
    }
    
    results = {}
    weights = [25, 25, 25, 25]
    risk_free_rate = 3  # 假设无风险利率为3%
    
    for name, portfolio in portfolios.items():
        try:
            etf_symbols = list(portfolio.keys())
            portfolio_value, _, returns, _, _, _ = calculate_portfolio(
                etf_symbols, weights, start_date, end_date, etf_list, 
                initial_investment, False  # 不进行再平衡
            )
            
            if portfolio_value is not None:
                # 计算指标
                final_val = portfolio_value.iloc[-1]
                total_ret = (final_val / initial_investment - 1) * 100
                days = len(portfolio_value)
                annual_ret = ((final_val / initial_investment) ** (252/days) - 1) * 100
                
                # 最大回撤
                peak = portfolio_value.expanding().max()
                drawdown = (portfolio_value - peak) / peak * 100
                max_dd = drawdown.min()
                
                # 夏普比率
                returns_series = portfolio_value.pct_change().dropna()
                vol = returns_series.std() * np.sqrt(252) * 100
                sharpe = (annual_ret - risk_free_rate) / vol if vol > 0 else 0
                
                results[name] = {
                    '总收益率 (%)': total_ret,
                    '年化收益率 (%)': annual_ret,
                    '最大回撤 (%)': max_dd,
                    '年化波动率 (%)': vol,
                    '夏普比率': sharpe,
                    'portfolio_value': portfolio_value
                }
        except Exception as e:
            st.warning(f"计算{name}时出错: {e}")
            continue
    
    return results

def permanent_portfolio_comparison():
    """永久组合对比分析"""
    # 设置页面配置
    st.set_page_config(
        page_title="永久组合对比分析",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("📊 永久组合对比分析")
    st.markdown("**四种永久组合的全面对比分析**：经典版、创业板版、红利低波版、激进版")
    
    # 获取ETF列表
    etf_list = get_etf_list()
    if etf_list.empty:
        st.error("无法获取ETF列表，请检查网络连接或数据源是否可用")
        return
    
    # 参数设置
    st.header("参数设置")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        end_date = datetime.now() - timedelta(days=1)
        start_date = datetime(2018, 1, 1)
        date_range = st.date_input(
            "回测时间范围",
            value=(start_date, end_date),
            min_value=datetime(2015, 1, 1),
            max_value=end_date
        )
    
    with col2:
        initial_investment = st.number_input("初始投资金额 (元)", min_value=1000, value=100000)
    
    with col3:
        st.write("")
        st.write("")
        if st.button("开始对比分析", type="primary"):
            if len(date_range) != 2:
                st.error("请选择完整的日期范围")
                return
            
            with st.spinner("正在计算四种永久组合对比..."):
                all_portfolio_results = calculate_all_permanent_portfolios(
                    date_range[0], date_range[1], initial_investment, etf_list
                )
                
                if all_portfolio_results:
                    st.session_state.comparison_results = all_portfolio_results
                    st.session_state.comparison_date_range = date_range
                    st.session_state.comparison_initial_investment = initial_investment
                    st.success("✅ 对比分析计算完成！")
                else:
                    st.error("❌ 无法计算任何组合，请检查参数设置")
    
    # 显示对比结果
    if 'comparison_results' in st.session_state:
        st.header("四种永久组合对比结果")
        
        # 创建对比表格
        comparison_df = pd.DataFrame({
            name: {k: v for k, v in data.items() if k != 'portfolio_value'} 
            for name, data in st.session_state.comparison_results.items()
        }).T
        
        # 保留2位小数
        comparison_df = comparison_df.round(2)
        
        # 显示对比表格
        st.subheader("指标对比表格")
        
        # 使用pandas的style功能来格式化表格
        def style_comparison_table(df):
            def highlight_metrics(val, metric_name):
                if pd.isna(val):
                    return ''
                
                if '收益率' in metric_name:
                    if val > 0:
                        return 'background-color: rgba(255, 0, 0, 0.2); color: darkred; font-weight: bold'
                    else:
                        return 'background-color: rgba(0, 255, 0, 0.2); color: darkgreen; font-weight: bold'
                elif '回撤' in metric_name or '波动率' in metric_name:
                    if val < 0:
                        return 'background-color: rgba(0, 255, 0, 0.2); color: darkgreen; font-weight: bold'
                    else:
                        return 'background-color: rgba(255, 0, 0, 0.2); color: darkred; font-weight: bold'
                elif '夏普比率' in metric_name:
                    if val > 1:
                        return 'background-color: rgba(255, 0, 0, 0.2); color: darkred; font-weight: bold'
                    elif val > 0:
                        return 'background-color: rgba(255, 165, 0, 0.2); color: orange; font-weight: bold'
                    else:
                        return 'background-color: rgba(0, 255, 0, 0.2); color: darkgreen; font-weight: bold'
                return ''
            
            # 格式化数值显示为2位小数
            styled_df = df.style.format({
                '总收益率 (%)': '{:.2f}',
                '年化收益率 (%)': '{:.2f}',
                '最大回撤 (%)': '{:.2f}',
                '年化波动率 (%)': '{:.2f}',
                '夏普比率': '{:.2f}'
            }).apply(lambda x: [highlight_metrics(v, x.name) for v in x])
            
            return styled_df
        
        styled_df = style_comparison_table(comparison_df)
        st.dataframe(styled_df, use_container_width=True)
        
        # 创建对比图表
        st.subheader("可视化对比")
        
        # 年化收益率对比
        col1, col2 = st.columns(2)
        
        with col1:
            fig, ax = plt.subplots(figsize=(10, 6))
            names = list(st.session_state.comparison_results.keys())
            annual_returns = [st.session_state.comparison_results[name]['年化收益率 (%)'] for name in names]
            colors = ['red' if r >= 0 else 'green' for r in annual_returns]
            
            bars = ax.bar(names, annual_returns, color=colors, alpha=0.7, edgecolor='black', linewidth=1)
            
            # 添加数值标签
            for bar, return_val in zip(bars, annual_returns):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + (0.5 if height >= 0 else -1.5),
                       f'{return_val:.1f}%', ha='center', va='bottom' if height >= 0 else 'top',
                       fontweight='bold', fontsize=10)
            
            ax.set_title("四种永久组合年化收益率对比", fontsize=14, fontweight='bold')
            ax.set_ylabel("年化收益率 (%)", fontsize=12)
            ax.grid(True, alpha=0.3, axis='y')
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
        
        with col2:
            # 最大回撤对比
            fig, ax = plt.subplots(figsize=(10, 6))
            max_drawdowns = [st.session_state.comparison_results[name]['最大回撤 (%)'] for name in names]
            colors = ['green' if d >= 0 else 'red' for d in max_drawdowns]  # 回撤越小越好
            
            bars = ax.bar(names, max_drawdowns, color=colors, alpha=0.7, edgecolor='black', linewidth=1)
            
            # 添加数值标签
            for bar, dd_val in zip(bars, max_drawdowns):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + (0.5 if height >= 0 else -1.5),
                       f'{dd_val:.1f}%', ha='center', va='bottom' if height >= 0 else 'top',
                       fontweight='bold', fontsize=10)
            
            ax.set_title("四种永久组合最大回撤对比", fontsize=14, fontweight='bold')
            ax.set_ylabel("最大回撤 (%)", fontsize=12)
            ax.grid(True, alpha=0.3, axis='y')
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
        
        # 夏普比率对比
        st.write("**夏普比率对比**")
        fig, ax = plt.subplots(figsize=(12, 6))
        sharpe_ratios = [st.session_state.comparison_results[name]['夏普比率'] for name in names]
        colors = ['red' if s > 1 else 'orange' if s > 0 else 'green' for s in sharpe_ratios]
        
        bars = ax.bar(names, sharpe_ratios, color=colors, alpha=0.7, edgecolor='black', linewidth=1)
        
        # 添加数值标签
        for bar, sharpe_val in zip(bars, sharpe_ratios):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                   f'{sharpe_val:.2f}', ha='center', va='bottom',
                   fontweight='bold', fontsize=10)
        
        ax.set_title("四种永久组合夏普比率对比", fontsize=14, fontweight='bold')
        ax.set_ylabel("夏普比率", fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax.axhline(y=1, color='red', linestyle='--', alpha=0.5, label='优秀线(>1)')
        plt.xticks(rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        
        # 净值曲线对比
        st.subheader("净值曲线对比")
        fig, ax = plt.subplots(figsize=(14, 8))
        
        colors = ['red', 'blue', 'green', 'orange']
        for i, (name, data) in enumerate(st.session_state.comparison_results.items()):
            portfolio_value = data['portfolio_value']
            color = colors[i] if i < len(colors) else 'gray'
            ax.plot(portfolio_value.index,
                   portfolio_value / st.session_state.comparison_initial_investment,
                   label=name, linewidth=2, color=color)
        
        ax.set_title("四种永久组合净值走势对比（归一化）", fontsize=16, fontweight='bold')
        ax.set_xlabel("日期", fontsize=14)
        ax.set_ylabel("净值倍数", fontsize=14)
        ax.legend(fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='both', which='major', labelsize=12)
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        
        # 组合特点总结
        st.subheader("四种永久组合特点总结")
        summary_col1, summary_col2 = st.columns(2)
        
        with summary_col1:
            st.markdown("""
            **🎯 经典版（含纳指）**
            - 纳指代表全球科技龙头
            - 长期增长潜力强
            - 适合追求全球科技收益的投资者
            
            **📈 创业板版（含创业板）**
            - 聚焦中国成长股
            - 适合看好中国科技创新的投资者
            - 波动相对较大
            """)
        
        with summary_col2:
            st.markdown("""
            **🛡️ 红利低波版**
            - 追求稳定分红
            - 波动率较低
            - 适合稳健型投资者
            
            **🚀 激进版（含纳指+红利低波）**
            - 双重股票配置
            - 去掉了货币ETF
            - 适合风险偏好较高的投资者
            """)
        
        # 最佳组合推荐
        st.subheader("最佳组合推荐")
        
        # 找出各项指标的最佳组合
        best_annual_return = max(st.session_state.comparison_results.items(), 
                               key=lambda x: x[1]['年化收益率 (%)'])
        best_sharpe = max(st.session_state.comparison_results.items(), 
                         key=lambda x: x[1]['夏普比率'])
        best_drawdown = min(st.session_state.comparison_results.items(), 
                           key=lambda x: x[1]['最大回撤 (%)'])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("最佳年化收益", best_annual_return[0], 
                     f"{best_annual_return[1]['年化收益率 (%)']:.2f}%")
        with col2:
            st.metric("最佳夏普比率", best_sharpe[0], 
                     f"{best_sharpe[1]['夏普比率']:.3f}")
        with col3:
            st.metric("最小回撤", best_drawdown[0], 
                     f"{best_drawdown[1]['最大回撤 (%)']:.2f}%")

permanent_portfolio_comparison() 