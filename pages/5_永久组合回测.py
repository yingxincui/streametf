import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from data import get_etf_list, load_metadata
from portfolio import calculate_portfolio
import os

# 永久组合回测页面

def clear_cache():
    """清除所有缓存"""
    import shutil
    cache_dir = "data_cache"
    if os.path.exists(cache_dir):
        try:
            # 删除目录中的所有文件
            for file in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            st.success("缓存已清除")
        except Exception as e:
            st.error(f"清除缓存失败: {e}")
    else:
        st.info("缓存目录不存在")

def get_cache_info():
    """获取缓存信息"""
    metadata = load_metadata()
    if not metadata:
        return "无缓存数据"
    
    info = []
    for symbol, data in metadata.items():
        info.append(f"{symbol}: {data['date']} ({data['rows']}行)")
    return "\n".join(info)

def calculate_permanent_portfolio():
    """计算永久组合"""
    # 设置页面配置
    st.set_page_config(
        page_title="永久组合回测",
        page_icon="🛡️",
        layout="wide",  # 使用宽屏布局
        initial_sidebar_state="expanded"
    )
    
    st.title("🛡️ 永久组合回测")
    st.markdown("**永久组合（Permanent Portfolio）**：由Harry Browne提出的经典投资组合，旨在在任何经济环境下都能获得稳定收益。")

    # 组合版本选择
    combo_version = st.radio(
        "选择永久组合版本",
        ("经典版（含纳指）", "创业板版（含创业板）", "红利低波版（不含创业板，含红利低波）", "激进版（含纳指+红利低波）"),
        horizontal=True
    )

    # 四种配置
    if combo_version == "经典版（含纳指）":
        PERMANENT_PORTFOLIO = {
            '518880': '黄金ETF (25%)',
            '159941': '纳指ETF (25%)',
            '511260': '国债ETF (25%)',
            '511830': '货币ETF (25%)'
        }
    elif combo_version == "创业板版（含创业板）":
        PERMANENT_PORTFOLIO = {
            '518880': '黄金ETF (25%)',
            '159915': '创业板ETF (25%)',
            '511260': '国债ETF (25%)',
            '511830': '货币ETF (25%)'
        }
    elif combo_version == "红利低波版（不含创业板，含红利低波）":
        PERMANENT_PORTFOLIO = {
            '518880': '黄金ETF (25%)',
            '512890': '红利低波ETF (25%)',
            '511260': '国债ETF (25%)',
            '511830': '货币ETF (25%)'
        }
    else:  # 激进版
        PERMANENT_PORTFOLIO = {
            '518880': '黄金ETF (25%)',
            '512890': '红利低波ETF (25%)',
            '159941': '纳指ETF (25%)',
            '511260': '国债ETF (25%)'
        }
    
    # 固定权重
    PERMANENT_WEIGHTS = [25, 25, 25, 25]  # 等权重分配
    
    global etf_list
    etf_list = get_etf_list()
    
    if etf_list.empty:
        st.error("无法获取ETF列表，请检查网络连接或数据源是否可用")
        return
    
    # 创建左右两列布局
    left_col, right_col = st.columns([1, 2.5])
    
    with left_col:
        st.header("组合配置")
        
        # 缓存管理
        with st.expander("缓存管理"):
            st.write("当前缓存信息:")
            cache_info = get_cache_info()
            st.text(cache_info)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("清除所有缓存", key="permanent_clear_cache"):
                    clear_cache()
                    st.rerun()
            with col2:
                if st.button("刷新缓存信息", key="permanent_refresh_cache"):
                    st.rerun()
        
        # 显示永久组合配置
        st.subheader("永久组合配置")
        for symbol, description in PERMANENT_PORTFOLIO.items():
            st.write(f"• {description}")
        
        st.info("💡 **永久组合理念**：\n"
                "• 黄金：对抗通胀和货币贬值\n"
                "• 股票：经济增长时的收益（纳指/创业板/红利低波）\n"
                "• 国债：通货紧缩时的保护\n"
                "• 现金：提供流动性和稳定性")
        
        # 根据选择的版本显示具体说明
        if combo_version == "经典版（含纳指）":
            st.success("🎯 **经典版特点**：纳指代表全球科技龙头，长期增长潜力强，是Harry Browne原始理念的现代演绎")
        elif combo_version == "创业板版（含创业板）":
            st.info("📈 **创业板版特点**：聚焦中国成长股，适合看好中国科技创新的投资者")
        elif combo_version == "红利低波版（不含创业板，含红利低波）":
            st.info("🛡️ **红利低波版特点**：追求稳定分红，波动率较低，适合稳健型投资者")
        else:  # 激进版
            st.info("🚀 **激进版特点**：包含黄金、红利低波、纳指、国债四大资产，适合风险偏好较高的投资者")
        
        # 回测参数设置
        st.subheader("回测参数")
        end_date = datetime.now() - timedelta(days=1)
        start_date = datetime(2018, 1, 1)  # 从2018年开始，确保所有ETF都有数据
        
        date_range = st.date_input(
            "回测时间范围",
            value=(start_date, end_date),
            min_value=datetime(2015, 1, 1),
            max_value=end_date
        )
        
        if len(date_range) != 2:
            st.error("请选择完整的日期范围")
            return
            
        initial_investment = st.number_input("初始投资金额 (元)", min_value=1000, value=100000)
        
        # 再平衡选项
        st.subheader("再平衡设置")
        rebalance_annually = st.checkbox("启用年度再平衡", value=True, 
                                       help="每年第一个交易日自动将组合权重调整回25%")
        
        if rebalance_annually:
            st.info("💡 年度再平衡：保持永久组合的经典配置")
        
        if st.button("运行永久组合回测"):
            with st.spinner("正在计算永久组合回测..."):
                try:
                    # 获取ETF代码列表
                    etf_symbols = list(PERMANENT_PORTFOLIO.keys())
                    
                    # 计算永久组合
                    portfolio_value, benchmark_value, returns, etf_data, etf_names, portfolio_value_rebalance = calculate_portfolio(
                        etf_symbols, PERMANENT_WEIGHTS, date_range[0], date_range[1], etf_list, initial_investment, rebalance_annually
                    )
                    
                    if portfolio_value is not None:
                        st.session_state.permanent_portfolio_value = portfolio_value
                        st.session_state.permanent_benchmark_value = benchmark_value
                        st.session_state.permanent_returns = returns
                        st.session_state.permanent_etf_data = etf_data
                        st.session_state.permanent_etf_names = etf_names
                        st.session_state.permanent_initial_investment = initial_investment
                        st.session_state.permanent_portfolio_value_rebalance = portfolio_value_rebalance
                        st.session_state.permanent_rebalance_annually = rebalance_annually
                        st.session_state.permanent_date_range = date_range
                        st.session_state.permanent_combo_version = combo_version
                        
                        # 计算年度收益
                        st.session_state.permanent_annual_returns = calculate_annual_returns(portfolio_value)
                        
                        st.success("✅ 永久组合回测计算完成！请查看右侧结果")
                    else:
                        st.error("❌ 无法获取足够的数据进行回测")
                except Exception as e:
                    st.error(f"❌ 回测过程中发生错误: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    
    with right_col:
        if 'permanent_portfolio_value' in st.session_state:
            st.header("永久组合回测结果")
            st.markdown(f"**当前组合版本：** {st.session_state.get('permanent_combo_version', '经典版（含纳指）')}")
            
            # 显示基本信息
            final_value = st.session_state.permanent_portfolio_value.iloc[-1]
            total_return = (final_value / st.session_state.permanent_initial_investment - 1) * 100
            
            # 计算年化收益率
            days = len(st.session_state.permanent_portfolio_value)
            annual_return = ((final_value / st.session_state.permanent_initial_investment) ** (252/days) - 1) * 100
            
            # 计算最大回撤
            peak = st.session_state.permanent_portfolio_value.expanding().max()
            drawdown = (st.session_state.permanent_portfolio_value - peak) / peak * 100
            max_drawdown = drawdown.min()
            
            # 计算夏普比率
            returns_series = st.session_state.permanent_portfolio_value.pct_change().dropna()
            volatility = returns_series.std() * np.sqrt(252) * 100
            risk_free_rate = 3  # 假设无风险利率为3%
            sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            # 显示关键指标
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总收益率", f"{total_return:.2f}%")
            with col2:
                st.metric("年化收益率", f"{annual_return:.2f}%")
            with col3:
                st.metric("最大回撤", f"{max_drawdown:.2f}%")
            with col4:
                st.metric("夏普比率", f"{sharpe_ratio:.3f}")
            
            # 显示再平衡对比结果
            if st.session_state.get('permanent_rebalance_annually', False) and st.session_state.get('permanent_portfolio_value_rebalance') is not None:
                st.subheader("再平衡对比结果")
                rebalance_value = st.session_state.permanent_portfolio_value_rebalance.iloc[-1]
                rebalance_return = (rebalance_value / st.session_state.permanent_initial_investment - 1) * 100
                return_diff = rebalance_return - total_return
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("不再平衡总收益率", f"{total_return:.2f}%")
                with col2:
                    st.metric("再平衡总收益率", f"{rebalance_return:.2f}%")
                with col3:
                    diff_color = "normal" if return_diff >= 0 else "inverse"
                    st.metric("收益率差异", f"{return_diff:+.2f}%", delta_color=diff_color)
            
            # 净值曲线
            st.subheader("净值曲线")
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # 绘制永久组合净值曲线
            ax.plot(st.session_state.permanent_portfolio_value.index, 
                   st.session_state.permanent_portfolio_value / st.session_state.permanent_initial_investment,
                   label='永久组合(不再平衡)', linewidth=3, color='black')
            
            # 如果启用了再平衡，绘制再平衡的净值曲线
            if st.session_state.get('permanent_rebalance_annually', False) and st.session_state.get('permanent_portfolio_value_rebalance') is not None:
                ax.plot(st.session_state.permanent_portfolio_value_rebalance.index, 
                       st.session_state.permanent_portfolio_value_rebalance / st.session_state.permanent_initial_investment,
                       label='永久组合(年度再平衡)', linewidth=3, color='red', linestyle='--')
            
            # 绘制各ETF净值曲线
            colors = ['red', 'blue', 'orange', 'green']
            for i, col in enumerate(st.session_state.permanent_etf_data.columns):
                symbol = col.split('_')[0]
                # 优先用etf_names中的名称，否则用代码
                etf_name = st.session_state.permanent_etf_names.get(symbol, symbol)
                color = colors[i] if i < len(colors) else 'gray'
                ax.plot(st.session_state.permanent_etf_data[col].index,
                       st.session_state.permanent_etf_data[col] / st.session_state.permanent_etf_data[col].iloc[0],
                       label=f"{etf_name}", 
                       alpha=0.7, linewidth=1.5, color=color)
            
            # 绘制基准
            if st.session_state.permanent_benchmark_value is not None:
                ax.plot(st.session_state.permanent_benchmark_value.index, 
                       st.session_state.permanent_benchmark_value / st.session_state.permanent_initial_investment,
                       label='等权重基准', linestyle=':', linewidth=2, color='gray')
            
            ax.set_title("永久组合与各资产净值走势（归一化）", fontsize=16, fontweight='bold')
            ax.set_xlabel("日期", fontsize=14)
            ax.set_ylabel("净值倍数", fontsize=14)
            ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='both', which='major', labelsize=12)
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            
            # 年度收益分析
            st.subheader("年度收益分析")
            if hasattr(st.session_state, 'permanent_annual_returns'):
                annual_returns = st.session_state.permanent_annual_returns
                
                # 创建年度收益可视化
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # 年度收益柱状图
                    fig, ax = plt.subplots(figsize=(12, 6))
                    years = annual_returns.index
                    returns = annual_returns.values
                    
                    # 设置颜色 - 涨用红色，跌用绿色
                    colors = ['red' if r >= 0 else 'green' for r in returns]
                    
                    bars = ax.bar(years, returns, color=colors, alpha=0.7, edgecolor='black', linewidth=1)
                    
                    # 添加数值标签
                    for bar, return_val in zip(bars, returns):
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height + (0.5 if height >= 0 else -1.5),
                               f'{return_val:.1f}%', ha='center', va='bottom' if height >= 0 else 'top',
                               fontweight='bold', fontsize=10)
                    
                    ax.set_title("永久组合年度收益率", fontsize=14, fontweight='bold')
                    ax.set_xlabel("年份", fontsize=12)
                    ax.set_ylabel("收益率 (%)", fontsize=12)
                    ax.grid(True, alpha=0.3, axis='y')
                    ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
                    
                    # 设置y轴范围，确保0线可见
                    max_return = max(returns) if len(returns) > 0 else 10
                    min_return = min(returns) if len(returns) > 0 else -10
                    ax.set_ylim(min_return - 2, max_return + 3)
                    
                    plt.tight_layout()
                    st.pyplot(fig, use_container_width=True)
                
                with col2:
                    # 年度收益统计
                    st.write("**年度收益统计**")
                    
                    # 计算统计指标
                    positive_years = sum(1 for r in returns if r > 0)
                    negative_years = sum(1 for r in returns if r < 0)
                    total_years = len(returns)
                    avg_return = np.mean(returns)
                    best_year = max(returns) if len(returns) > 0 else 0
                    worst_year = min(returns) if len(returns) > 0 else 0
                    
                    # 显示统计信息
                    st.metric("平均年收益率", f"{avg_return:.2f}%")
                    st.metric("正收益年份", f"{positive_years}/{total_years}")
                    st.metric("最佳年份", f"{best_year:.2f}%")
                    st.metric("最差年份", f"{worst_year:.2f}%")
                    
                    # 胜率
                    win_rate = (positive_years / total_years * 100) if total_years > 0 else 0
                    st.metric("胜率", f"{win_rate:.1f}%")
                
                # 年度收益详细表格
                st.write("**年度收益详情**")
                annual_df = pd.DataFrame({
                    '年份': annual_returns.index,
                    '收益率 (%)': annual_returns.values.round(2)
                })
                
                # 添加颜色标识和进度条
                def style_annual_returns(df):
                    # 创建样式 - 涨用红色，跌用绿色
                    def color_returns(val):
                        if pd.isna(val):
                            return ''
                        if val > 0:
                            return 'background-color: rgba(255, 0, 0, 0.3); color: darkred; font-weight: bold'
                        elif val < 0:
                            return 'background-color: rgba(0, 255, 0, 0.3); color: darkgreen; font-weight: bold'
                        else:
                            return 'background-color: rgba(128, 128, 128, 0.3); color: gray; font-weight: bold'
                    
                    return df.style.applymap(color_returns, subset=['收益率 (%)'])
                
                st.dataframe(style_annual_returns(annual_df.set_index('年份')), use_container_width=True)
                
                # 年度收益进度条可视化
                st.write("**年度收益进度条**")
                for year, return_val in zip(annual_returns.index, annual_returns.values):
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        st.write(f"**{year}年**")
                    with col2:
                        # 创建进度条 - 涨用红色，跌用绿色
                        if return_val >= 0:
                            st.progress(return_val / 50, text=f"{return_val:.2f}%")  # 假设最大50%
                        else:
                            # 对于负收益，使用绿色进度条
                            st.markdown(f"""
                            <div style="background-color: #f0f0f0; border-radius: 10px; padding: 10px; margin: 5px 0;">
                                <div style="background-color: #4CAF50; width: {abs(return_val)/20:.1f}%; height: 20px; border-radius: 5px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                                    {return_val:.2f}%
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    with col3:
                        if return_val >= 0:
                            st.success(f"📈 +{return_val:.2f}%")
                        else:
                            st.error(f"📉 {return_val:.2f}%")
            
            # 资产配置分析
            st.subheader("资产配置分析")
            col1, col2 = st.columns(2)
            
            with col1:
                # 相关性矩阵
                st.write("**资产相关性矩阵**")
                corr_fig, corr_ax = plt.subplots(figsize=(8, 6))
                import seaborn as sns
                sns.heatmap(st.session_state.permanent_returns.corr(), 
                           annot=True, cmap='coolwarm', center=0, ax=corr_ax, fmt='.2f')
                plt.title("永久组合资产相关性", fontsize=12, fontweight='bold')
                plt.tight_layout()
                st.pyplot(corr_fig, use_container_width=True)
            
            with col2:
                # 收益率统计
                st.write("**各资产收益率统计**")
                returns_stats = st.session_state.permanent_returns.describe()
                st.dataframe(returns_stats, use_container_width=True)
            
            # 风险收益分析
            st.subheader("风险收益分析")
            
            # 计算各资产的风险收益指标
            assets_metrics = []
            for col in st.session_state.permanent_returns.columns:
                symbol = col.split('_')[0]
                asset_returns = st.session_state.permanent_returns[col]
                
                # 计算指标
                total_return = (st.session_state.permanent_etf_data[col].iloc[-1] / st.session_state.permanent_etf_data[col].iloc[0] - 1) * 100
                annual_return = ((st.session_state.permanent_etf_data[col].iloc[-1] / st.session_state.permanent_etf_data[col].iloc[0]) ** (252/days) - 1) * 100
                volatility = asset_returns.std() * np.sqrt(252) * 100
                sharpe = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
                
                assets_metrics.append({
                    '资产': st.session_state.permanent_etf_names[symbol],
                    '总收益率 (%)': total_return,
                    '年化收益率 (%)': annual_return,
                    '年化波动率 (%)': volatility,
                    '夏普比率': sharpe
                })
            
            metrics_df = pd.DataFrame(assets_metrics)
            st.dataframe(metrics_df.set_index('资产'), use_container_width=True)
            
            # 永久组合优势分析
            st.subheader("永久组合优势分析")
            
            advantages = [
                "🛡️ **多元化配置**：黄金、股票、债券、现金四大类资产全覆盖",
                "📈 **抗通胀**：黄金和股票在通胀环境下表现良好",
                "📉 **抗通缩**：债券和现金在通缩环境下提供保护",
                "⚖️ **风险分散**：不同经济环境下的风险相互对冲",
                "🔄 **再平衡收益**：定期再平衡捕捉各类资产的轮动机会",
                "💎 **长期稳定**：历史表现证明在各种市场环境下都能获得稳定收益"
            ]
            
            for advantage in advantages:
                st.write(advantage)

def calculate_annual_returns(portfolio_value):
    """计算年度收益率"""
    try:
        # 按年份分组计算收益率
        portfolio_df = pd.DataFrame({'value': portfolio_value})
        portfolio_df['year'] = portfolio_df.index.year
        
        annual_returns = {}
        for year in portfolio_df['year'].unique():
            year_data = portfolio_df[portfolio_df['year'] == year]
            if len(year_data) > 1:
                start_value = year_data['value'].iloc[0]
                end_value = year_data['value'].iloc[-1]
                annual_return = (end_value / start_value - 1) * 100
                annual_returns[year] = annual_return
        
        return pd.Series(annual_returns)
    except Exception as e:
        st.warning(f"计算年度收益率失败: {e}")
        return pd.Series()

calculate_permanent_portfolio() 