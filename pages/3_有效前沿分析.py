import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from data import get_etf_list, fetch_etf_data_with_retry
from efficient_frontier import EfficientFrontier
from frontier_config import load_frontier_portfolios, add_frontier_portfolio, delete_frontier_portfolio
from ai_utils import ai_chat, get_api_key


def calculate_benchmark_portfolio(price_df, risk_free_rate):
    """
    计算基准投资组合的年化收益、波动率和夏普比率
    
    参数:
    price_df: 价格数据DataFrame
    risk_free_rate: 无风险利率
    
    返回:
    dict: 包含return, volatility, sharpe, weights的字典
    """
    # 先计算总收益率再推年化
    price_df = price_df.sort_index()
    first = price_df.iloc[0, 0]
    last = price_df.iloc[-1, 0]
    days = (price_df.index[-1] - price_df.index[0]).days
    years = days / 365.25 if days > 0 else 1
    
    if pd.isna(first) or pd.isna(last) or first == 0 or years <= 0:
        annual_return = 0
        total_return = 0
    else:
        total_return = (last / first) - 1
        annual_return = ((1 + total_return) ** (1/years) - 1) * 100
    
    # 计算年化波动率
    returns = price_df.iloc[:, 0].pct_change().dropna()
    annual_vol = returns.std() * np.sqrt(252)
    
    # 计算夏普比率
    sharpe = (annual_return - risk_free_rate) / annual_vol if annual_vol > 0 else 0
    
    return {
        'return': annual_return,
        'total_return': total_return,
        'volatility': annual_vol,
        'sharpe': sharpe,
        'weights': [1.0]
    }

# 有效前沿分析页面

def efficient_frontier_page():
    # 设置matplotlib为高分辨率模式
    import matplotlib
    matplotlib.rcParams['figure.dpi'] = 300
    matplotlib.rcParams['savefig.dpi'] = 300
    matplotlib.rcParams['savefig.format'] = 'svg'
    matplotlib.rcParams['font.size'] = 12
    matplotlib.rcParams['axes.titlesize'] = 14
    matplotlib.rcParams['axes.labelsize'] = 12
    
    st.title("📊 有效前沿分析")
    
    # 添加概念讲解
    with st.expander("🔍 什么是有效前沿分析？", expanded=False):
        st.markdown("""
        **有效前沿分析**是现代投资组合理论的核心概念，由诺贝尔经济学奖得主马科维茨提出。
        
        ### 🎯 核心思想
        在投资中，我们面临一个基本矛盾：**高收益往往伴随高风险，低风险通常意味着低收益**。
        有效前沿分析就是帮我们找到**在给定风险水平下收益最高，或在给定收益水平下风险最低**的投资组合。
        
        ### 📈 有效前沿曲线
        - **横轴**：投资组合的风险（波动率）
        - **纵轴**：投资组合的预期收益
        - **曲线**：有效前沿，代表最优的投资组合集合
        
        ### 🎯 关键组合类型
        1. **最大夏普比率组合**：风险调整后收益最佳的组合
        2. **最大收益组合**：收益最高但风险也最大的组合  
        3. **最小方差组合**：风险最低的组合
        4. **等权重组合**：各资产权重相等的简单组合
        
        ### 💡 实际应用
        - 帮助投资者根据风险偏好选择合适组合
        - 通过资产配置优化投资效果
        - 避免"把所有鸡蛋放在一个篮子里"
        """)
    
    # 添加使用指南
    with st.expander("📖 如何使用这个工具？", expanded=False):
        st.markdown("""
        ### 🚀 使用步骤
        1. **选择ETF**：至少选择2只ETF进行分析
        2. **设置参数**：调整回测时间、无风险利率等
        3. **运行分析**：点击"运行有效前沿分析"
        4. **查看结果**：对比不同组合的表现
        
        ### 📊 结果解读
        - **年化收益率**：一年内的预期收益百分比
        - **年化波动率**：收益的波动程度，数值越大风险越高
        - **夏普比率**：风险调整后收益，>1为优秀，>0为良好
        - **超额收益率**：相对于沪深300的超额收益
        
        ### 🎯 选择建议
        - **保守型**：选择最小方差组合
        - **平衡型**：选择最大夏普比率组合
        - **激进型**：选择最大收益组合
        - **简单型**：选择等权重组合
        """)
    
    etf_list = get_etf_list()
    if etf_list.empty:
        st.error("无法获取ETF列表，请检查网络连接或数据源是否可用")
        return
    left_col, right_col = st.columns([1, 2])
    with left_col:
        st.header("参数设置")
        saved_frontiers = load_frontier_portfolios()
        frontier_names = list(saved_frontiers.keys())
        selected_frontier = st.selectbox("加载已保存组合", ["无"] + frontier_names)
        # 默认ETF为513880和513000
        default_etfs = [513880, 513000]
        default_start = pd.to_datetime("2020-01-01")
        default_end = datetime.now() - timedelta(days=1)
        default_risk_free = 0.02
        default_num_portfolios = 5000
        default_weights = []
        if selected_frontier != "无":
            sel = saved_frontiers[selected_frontier]
            default_etfs = sel.get("etfs", default_etfs)
            # 确保default_etfs是整数列表（匹配etf_options的类型）
            if default_etfs and isinstance(default_etfs[0], str):
                default_etfs = [int(etf) for etf in default_etfs]
            default_start = pd.to_datetime(sel.get("date_range", ["2020-01-01", str(datetime.now().date())])[0])
            default_end = pd.to_datetime(sel.get("date_range", ["2020-01-01", str(datetime.now().date())])[1])
            default_risk_free = sel.get("risk_free_rate", 0.02)
            default_num_portfolios = sel.get("num_portfolios", 5000)
            default_weights = sel.get("weights", [])
        from utils import get_etf_options_with_favorites
        etf_options = get_etf_options_with_favorites(etf_list)
        # 过滤掉不在可用选项中的默认ETF
        default_etfs = [etf for etf in default_etfs if etf in etf_options]
        selected_etfs = st.multiselect(
            "选择ETF (至少2只)",
            options=etf_options,
            format_func=lambda x: f"{x} - {etf_list[etf_list['symbol'] == x]['name'].values[0]}",
            default=default_etfs
        )
        start_date = st.date_input("开始日期", value=default_start, min_value=pd.to_datetime("2010-01-01"))
        end_date = st.date_input("结束日期", value=default_end, min_value=start_date)
        risk_free_rate = st.number_input("无风险利率 (年化, 小数)", value=default_risk_free, step=0.001)
        num_portfolios = st.number_input("模拟组合数量", min_value=1000, max_value=20000, value=default_num_portfolios, step=1000)
        ai_analysis = st.checkbox("是否进行AI分析", value=True)
        if selected_frontier != "无":
            if st.button(f"删除组合: {selected_frontier}", key=f"delete_frontier_{selected_frontier}"):
                delete_frontier_portfolio(selected_frontier)
                st.success(f"组合 '{selected_frontier}' 已删除！")
                st.rerun()
        run_btn = st.button("运行有效前沿分析")
    with left_col:
        if run_btn:
            if len(selected_etfs) < 2:
                st.warning("请至少选择2只ETF")
                return
            with st.spinner("正在获取ETF历史数据..."):
                price_dfs = []
                etf_names = {}
                for symbol in selected_etfs:
                    df = fetch_etf_data_with_retry(symbol, start_date, end_date, etf_list)
                    if df.empty:
                        st.error(f"{symbol} 无法获取数据，终止分析")
                        return
                    price_dfs.append(df)
                    etf_names[symbol] = df.columns[0]
                price_df = pd.concat(price_dfs, axis=1, join='inner')
                if price_df.empty or price_df.shape[1] < 2:
                    st.error("数据不足，无法进行分析")
                    return
                st.success("数据获取完成，正在模拟...")
            
            ef = EfficientFrontier(price_df, risk_free_rate)
            ef.simulate_portfolios(num_portfolios)
            max_sharpe = ef.get_max_sharpe_portfolio()
            min_vol = ef.get_min_vol_portfolio()
            max_return = ef.get_max_return_portfolio()
            eq_port = ef.get_equal_weight_portfolio()
            # 获取沪深300数据作为基准
            try:
                hs300_df = fetch_etf_data_with_retry('510300', start_date, end_date, etf_list)
                if not hs300_df.empty:
                    # 使用封装的函数计算沪深300基准收益
                    hs300_portfolio = calculate_benchmark_portfolio(hs300_df, risk_free_rate)
                else:
                    hs300_portfolio = None
            except Exception as e:
                st.warning(f"无法获取沪深300数据: {e}")
                hs300_portfolio = None
            # 保存主要分析结果到session_state
            st.session_state.frontier_results = {
                'max_sharpe': max_sharpe,
                'min_vol': min_vol,
                'max_return': max_return,
                'eq_port': eq_port,
                'hs300_portfolio': hs300_portfolio,
                'start_date': start_date,
                'end_date': end_date,
                'ef': ef,
                'ai_analysis': ai_analysis
            }
            st.session_state.frontier_etf_names = etf_names
            # 自动生成AI分析结果（仅当勾选）
            api_key = get_api_key()
            ai_result = None
            if ai_analysis and api_key:
                def fmt(p):
                    return f"年化收益率: {p['return']*100:.2f}%, 年化波动率: {p['volatility']*100:.2f}%, 夏普比率: {p['sharpe']:.2f}, 权重: {', '.join([f'{w*100:.1f}%' for w in p['weights']])}"
                summary = f"最大夏普组合: {fmt(max_sharpe)}\n最小方差组合: {fmt(min_vol)}\n最大收益组合: {fmt(max_return)}\n等权重组合: {fmt(eq_port)}\n"
                if hs300_portfolio:
                    summary += f"沪深300基准: 年化收益率: {hs300_portfolio['return']*100:.2f}%, 年化波动率: {hs300_portfolio['volatility']*100:.2f}%, 夏普比率: {hs300_portfolio['sharpe']:.2f}\n"
                prompt = f"请分析以下ETF有效前沿分析结果，简明总结各主要组合的收益、风险、权重配置优劣，并给出投资建议：\n{summary}"
                with st.spinner("AI正在分析，请稍候..."):
                    ai_result = ai_chat(prompt, api_key=api_key)
                st.session_state.frontier_ai_result = ai_result
            else:
                st.session_state.frontier_ai_result = None
    
    with right_col:
        # 只要有分析结果就显示后续所有内容
        if 'frontier_results' in st.session_state and 'max_sharpe' in st.session_state.frontier_results:
            fr = st.session_state.frontier_results
            max_sharpe = fr['max_sharpe']
            min_vol = fr['min_vol']
            max_return = fr['max_return']
            eq_port = fr['eq_port']
            hs300_portfolio = fr['hs300_portfolio']
            etf_names = st.session_state.frontier_etf_names
            start_date = fr.get('start_date')
            end_date = fr.get('end_date')
            ef = fr.get('ef', None)
            ai_analysis = fr.get('ai_analysis', True)
            # 标的本身的价格趋势图
            st.subheader("📈 标的本身的价格趋势图")
            if 'price_df' in locals() and price_df is not None:
                import plotly.graph_objects as go
                
                fig_trend = go.Figure()
                
                # 添加每个ETF的价格趋势
                for col in price_df.columns:
                    # 计算涨跌幅
                    price_series = price_df[col]
                    returns = (price_series / price_series.iloc[0] - 1) * 100
                    fig_trend.add_trace(go.Scatter(
                        x=returns.index, y=returns,
                        mode='lines', name=f"{col}涨跌幅",
                        hovertemplate='日期: %{x}<br>涨跌幅: %{y:.2f}%'
                    ))
                
                fig_trend.update_layout(
                    title="标的涨跌幅趋势图",
                    xaxis_title="日期", yaxis_title="涨跌幅 (%)",
                    legend=dict(font=dict(size=12)),
                    hovermode='x unified'
                )
                st.plotly_chart(fig_trend, use_container_width=True)
            
            # 几种组合的走势图
            st.subheader("📊 几种组合的走势图")
            if 'price_df' in locals() and price_df is not None:
                fig_portfolio = go.Figure()
                
                # 计算各组合的累计收益
                portfolios = {
                    '最大夏普比率组合': max_sharpe,
                    '最大收益组合': max_return,
                    '最小方差组合': min_vol,
                    '等权重组合': eq_port
                }
                
                colors = ['red', 'orange', 'blue', 'green']
                
                for i, (name, portfolio) in enumerate(portfolios.items()):
                    weights = portfolio['weights']
                    # 计算组合的每日收益率
                    portfolio_returns = (price_df.pct_change().dropna() * weights).sum(axis=1)
                    # 计算累计收益
                    cumulative_returns = (1 + portfolio_returns).cumprod() - 1
                    cumulative_returns = cumulative_returns * 100  # 转换为百分比
                    
                    fig_portfolio.add_trace(go.Scatter(
                        x=cumulative_returns.index, y=cumulative_returns,
                        mode='lines', name=name, line=dict(color=colors[i], width=2),
                        hovertemplate='日期: %{x}<br>累计收益: %{y:.2f}%'
                    ))
                
                # 添加沪深300基准
                if hs300_portfolio:
                    hs300_returns = (price_df.iloc[:, 0] / price_df.iloc[:, 0].iloc[0] - 1) * 100
                    fig_portfolio.add_trace(go.Scatter(
                        x=hs300_returns.index, y=hs300_returns,
                        mode='lines', name='沪深300基准', line=dict(color='purple', width=2, dash='dash'),
                        hovertemplate='日期: %{x}<br>累计收益: %{y:.2f}%'
                    ))
                
                fig_portfolio.update_layout(
                    title="各组合累计收益走势对比",
                    xaxis_title="日期", yaxis_title="累计收益 (%)",
                    legend=dict(font=dict(size=12)),
                    hovermode='x unified'
                )
                st.plotly_chart(fig_portfolio, use_container_width=True)
            
            # --- 恢复有效前沿图 ---
            if ef is not None:
                st.subheader(f"📈 有效前沿图（可交互）  |  回测区间：{str(start_date)} ~ {str(end_date)}")
                st.markdown("""
                > 🎯 **图表解读**：
                > - **散点**：每个点代表一个模拟的投资组合
                > - **红色曲线**：有效前沿，代表最优组合集合
                > - **橙色星号**：最大夏普比率组合（风险调整后收益最佳）
                > - **蓝色叉号**：最小方差组合（风险最低）
                > - **紫色菱形**：最大收益组合（收益最高）
                > - **颜色深浅**：代表夏普比率高低
                """)
                fig = ef.plotly_frontier_figure()
                fig.update_layout(width=1000, height=600, font=dict(size=12))
                st.plotly_chart(fig, use_container_width=True)
            # --- 输出AI分析结果 ---
            if ai_analysis and st.session_state.get('frontier_ai_result'):
                st.markdown("---")
                st.subheader("🤖 AI分析结果")
                st.write(st.session_state['frontier_ai_result'])
            # --- 其余分析结论、图表、饼图等全部放在此块内 ---
            st.markdown("---")
            st.subheader("📊 分析结论")
            st.markdown(f"**本次回测区间：{str(start_date)} ~ {str(end_date)}**")
            
            # 添加结论解读说明
            st.markdown("""
            > 📋 **结论解读**：下表对比了不同投资策略的表现，帮助您根据风险偏好选择合适组合。
            > 颜色编码：🟢绿色=优秀，🟠橙色=良好，🔴红色=需注意
            """)
            
            # 创建结论对比表格
            conclusion_data = {
                '组合类型': ['最大夏普比率组合', '最大收益组合', '最小方差组合', '等权重组合']
            }
            
            # 添加配置比例
            def format_weights(weights, asset_names):
                if len(weights) == 1:  # 沪深300
                    return "100%"
                weight_pairs = []
                for i, weight in enumerate(weights):
                    if weight > 0.01:  # 只显示权重大于1%的资产
                        asset_name = asset_names[i] if i < len(asset_names) else f"资产{i+1}"
                        weight_pairs.append(f"{asset_name}({weight*100:.0f}%)")
                return ", ".join(weight_pairs)
            
            conclusion_data['配置比例'] = [
                format_weights(max_sharpe['weights'], list(etf_names.values())),
                format_weights(max_return['weights'], list(etf_names.values())),
                format_weights(min_vol['weights'], list(etf_names.values())),
                format_weights(eq_port['weights'], list(etf_names.values()))
            ]
            
            # 计算总收益率
            def calculate_total_return(portfolio, price_df):
                weights = portfolio['weights']
                # 计算组合的每日收益率
                portfolio_returns = (price_df.pct_change().dropna() * weights).sum(axis=1)
                # 计算总收益率
                total_return = (1 + portfolio_returns).prod() - 1
                return total_return
            
            # 计算每个组合的总收益率
            max_sharpe_total_return = calculate_total_return(max_sharpe, price_df)
            max_return_total_return = calculate_total_return(max_return, price_df)
            min_vol_total_return = calculate_total_return(min_vol, price_df)
            eq_port_total_return = calculate_total_return(eq_port, price_df)
            
            # 添加基本指标
            conclusion_data['总收益率 (%)'] = [
                f"{max_sharpe_total_return*100:.2f}",
                f"{max_return_total_return*100:.2f}",
                f"{min_vol_total_return*100:.2f}",
                f"{eq_port_total_return*100:.2f}"
            ]
            
            conclusion_data['年化收益率 (%)'] = [
                f"{max_sharpe['return']*100:.2f}",
                f"{max_return['return']*100:.2f}",
                f"{min_vol['return']*100:.2f}",
                f"{eq_port['return']*100:.2f}"
            ]
            
            conclusion_data['年化波动率 (%)'] = [
                f"{max_sharpe['volatility']*100:.2f}",
                f"{max_return['volatility']*100:.2f}",
                f"{min_vol['volatility']*100:.2f}",
                f"{eq_port['volatility']*100:.2f}"
            ]
            
            conclusion_data['夏普比率'] = [
                f"{max_sharpe['sharpe']:.2f}",
                f"{max_return['sharpe']:.2f}",
                f"{min_vol['sharpe']:.2f}",
                f"{eq_port['sharpe']:.2f}"
            ]
            
            # 添加沪深300对比
            if hs300_portfolio:
                conclusion_data['组合类型'].append('沪深300基准')
                conclusion_data['总收益率 (%)'].append(f"{hs300_portfolio['total_return']*100:.2f}")
                conclusion_data['年化收益率 (%)'].append(f"{hs300_portfolio['return']:.2f}")
                conclusion_data['年化波动率 (%)'].append(f"{hs300_portfolio['volatility']*100:.2f}")
                conclusion_data['夏普比率'].append(f"{hs300_portfolio['sharpe']:.2f}")
                conclusion_data['配置比例'].append("沪深300(100%)")
                
                # 计算超额收益
                conclusion_data['超额收益率 (%)'] = [
                    f"{(max_sharpe['return'] - hs300_portfolio['return'])*100:.2f}",
                    f"{(max_return['return'] - hs300_portfolio['return'])*100:.2f}",
                    f"{(min_vol['return'] - hs300_portfolio['return'])*100:.2f}",
                    f"{(eq_port['return'] - hs300_portfolio['return'])*100:.2f}",
                    "0.00"  # 沪深300自身
                ]
            else:
                conclusion_data['超额收益率 (%)'] = ["N/A", "N/A", "N/A", "N/A"]
            
            conclusion_data['主要特点'] = [
                '风险调整后收益最佳，适合追求收益与风险平衡的投资者',
                '收益最高但风险也最大，适合激进型投资者',
                '风险最低，适合极度厌恶风险的投资者',
                '等权重基准，便于对比主动优化的效果'
            ]
            
            if hs300_portfolio:
                conclusion_data['主要特点'].append('市场基准，代表大盘整体表现')
            
            conclusion_df = pd.DataFrame(conclusion_data)
            
            # 样式化表格
            def style_conclusion_table(df):
                def highlight_metrics(val, col_name):
                    if col_name == '年化收益率 (%)':
                        try:
                            val_float = float(val.replace('%', ''))
                            if val_float > 0:
                                return 'background-color: rgba(255, 0, 0, 0.2); color: darkred; font-weight: bold'
                            else:
                                return 'background-color: rgba(0, 255, 0, 0.2); color: darkgreen; font-weight: bold'
                        except:
                            return ''
                    elif col_name == '年化波动率 (%)':
                        try:
                            val_float = float(val.replace('%', ''))
                            if val_float < 15:  # 低波动率
                                return 'background-color: rgba(0, 255, 0, 0.2); color: darkgreen; font-weight: bold'
                            elif val_float > 25:  # 高波动率
                                return 'background-color: rgba(255, 0, 0, 0.2); color: darkred; font-weight: bold'
                            else:
                                return 'background-color: rgba(255, 165, 0, 0.2); color: orange; font-weight: bold'
                        except:
                            return ''
                    elif col_name == '夏普比率':
                        try:
                            val_float = float(val)
                            if val_float > 1:
                                return 'background-color: rgba(255, 0, 0, 0.2); color: darkred; font-weight: bold'
                            elif val_float > 0:
                                return 'background-color: rgba(255, 165, 0, 0.2); color: orange; font-weight: bold'
                            else:
                                return 'background-color: rgba(0, 255, 0, 0.2); color: darkgreen; font-weight: bold'
                        except:
                            return ''
                    elif col_name == '超额收益率 (%)':
                        try:
                            if val == "N/A":
                                return ''
                            val_float = float(val)
                            if val_float > 0:
                                return 'background-color: rgba(255, 0, 0, 0.2); color: darkred; font-weight: bold'
                            elif val_float < 0:
                                return 'background-color: rgba(0, 255, 0, 0.2); color: darkgreen; font-weight: bold'
                            else:
                                return 'background-color: rgba(128, 128, 128, 0.2); color: gray; font-weight: bold'
                        except:
                            return ''
                    return ''
                
                return df.style.apply(lambda x: [highlight_metrics(v, x.name) for v in x])
            
            st.dataframe(style_conclusion_table(conclusion_df), use_container_width=True)
            
            # 创建动态交互式饼图
            import plotly.graph_objects as go
            col1, col2 = st.columns(2)
            def plot_pie(weights, asset_names, title):
                labels = []
                values = []
                for i, w in enumerate(weights):
                    if w > 0.01:
                        asset_name = asset_names[i] if i < len(asset_names) else f"资产{i+1}"
                        labels.append(asset_name)
                        values.append(w)
                fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3)])
                fig.update_traces(textinfo='label+percent', hoverinfo='label+percent+value')
                fig.update_layout(title=title, legend=dict(font=dict(size=12)))
                return fig
            with col1:
                st.plotly_chart(plot_pie(max_sharpe['weights'], list(etf_names.values()), "最大夏普比率组合配置比例"), use_container_width=True)
                st.plotly_chart(plot_pie(max_return['weights'], list(etf_names.values()), "最大收益组合配置比例"), use_container_width=True)
            with col2:
                st.plotly_chart(plot_pie(min_vol['weights'], list(etf_names.values()), "最小方差组合配置比例"), use_container_width=True)
                st.plotly_chart(plot_pie(eq_port['weights'], list(etf_names.values()), "等权重组合配置比例"), use_container_width=True)
            
            # 沪深300基准说明
            if hs300_portfolio:
                st.markdown("""
                > 📊 **沪深300基准**：单一资产配置，100%投资于沪深300ETF，代表市场整体表现。
                """)
            
            # 主要资产分析
            main_assets = sorted(zip(list(etf_names.values()), max_sharpe['weights']), key=lambda x: -x[1])[:3]
            main_assets_str = ', '.join([f"{name}（{w*100:.2f}%）" for name, w in main_assets])
            
            st.info(f"**主要资产分析**：最大夏普比率组合的主要资产为：{main_assets_str}。")
            
            # 添加投资建议说明
            st.markdown("""
            > 💡 **投资建议说明**：以下建议基于历史数据分析，实际投资时请结合个人情况综合考虑。
            """)
            
            # 投资建议
            st.subheader("🎯 投资建议")
            advice_col1, advice_col2 = st.columns(2)
            
            with advice_col1:
                st.markdown("""
                **🎯 最大夏普比率组合**
                - 适合：追求收益与风险平衡的投资者
                - 特点：风险调整后收益最佳
                - 建议：可作为核心配置
                """)
                
                st.markdown("""
                **🚀 最大收益组合**
                - 适合：激进型投资者
                - 特点：收益最高但风险也最大
                - 建议：适合风险承受能力强的投资者
                """)
                
                st.markdown("""
                **🛡️ 最小方差组合**
                - 适合：极度厌恶风险的投资者
                - 特点：波动率最低，风险最小
                - 建议：适合保守型投资者
                """)
            
            with advice_col2:
                st.markdown("""
                **⚖️ 等权重组合**
                - 适合：希望简单配置的投资者
                - 特点：各资产权重相等
                - 建议：可作为基准对比
                """)
                
                if hs300_portfolio:
                    st.markdown("""
                    **📊 沪深300基准**
                    - 适合：希望跟踪大盘的投资者
                    - 特点：代表市场整体表现
                    - 建议：可作为业绩比较基准
                    """)
                
                st.markdown("""
                **💡 配置建议**
                - 根据风险偏好选择合适组合
                - 可考虑组合配置降低风险
                - 定期再平衡保持目标权重
                - 关注超额收益表现
                """)
            st.markdown("---")
            st.subheader("保存本次分析组合")
            save_col1, save_col2 = st.columns([2,1])
            with save_col1:
                combo_name = st.text_input("输入组合名称以保存", key="frontier_save_name")
            with save_col2:
                save_disabled = len(selected_etfs) < 2 or not combo_name or start_date is None or end_date is None
                if st.button("保存组合", key="frontier_save_btn", disabled=save_disabled):
                    weights = list(max_sharpe['weights']) if 'weights' in max_sharpe else []
                    if weights and abs(sum(weights) - 1.0) > 1e-6:
                        st.warning("最大夏普组合权重总和必须为1，请调整！")
                        st.stop()
                    try:
                        add_frontier_portfolio(
                            combo_name,
                            selected_etfs,
                            weights,
                            [str(start_date), str(end_date)],
                            risk_free_rate,
                            num_portfolios
                        )
                        st.success(f"组合 '{combo_name}' 已保存！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存组合时发生错误: {e}")
            
            # 添加总结说明
            st.markdown("---")
            with st.expander("📚 学习要点总结", expanded=False):
                st.markdown("""
                ### 🎓 有效前沿分析的核心价值
                
                **1. 科学配置资产**
                - 不是简单平均分配，而是基于历史数据优化
                - 考虑资产间的相关性，实现风险分散
                
                **2. 个性化投资选择**
                - 保守型：最小方差组合
                - 平衡型：最大夏普比率组合  
                - 激进型：最大收益组合
                
                **3. 持续优化**
                - 定期重新分析，调整配置
                - 关注市场变化，动态管理
                
                ### ⚠️ 重要提醒
                - 历史表现不代表未来收益
                - 投资有风险，入市需谨慎
                - 建议结合个人风险承受能力
                - 可考虑分散投资，不要孤注一掷
                
                ### 🔄 下一步行动
                1. 根据分析结果选择合适组合
                2. 制定投资计划和风险控制策略
                3. 定期回顾和调整投资组合
                4. 持续学习投资知识
                """)
            st.markdown("---")
            
            # （AI分析区和按钮已移除）

efficient_frontier_page()