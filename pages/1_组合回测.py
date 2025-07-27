import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from data import get_etf_list, load_metadata, get_cache_file_path
from portfolio import calculate_portfolio, calculate_rebalance_comparison
from portfolio_config import load_portfolios, add_portfolio, delete_portfolio
from metrics import calculate_metrics
from utils import calculate_annual_returns
from pdf_export import create_portfolio_backtest_pdf, get_pdf_download_link
import os
from ai_utils import ai_chat, get_api_key

# 组合回测页面

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

def portfolio_backtest():
    # 设置页面配置
    st.set_page_config(
        page_title="ETF组合回测工具",
        page_icon="📊",
        layout="wide",  # 使用宽屏布局
        initial_sidebar_state="expanded"
    )
    
    st.title("ETF组合回测工具")

    global etf_list
    etf_list = get_etf_list()
    
    # 加载已保存的投资组合
    saved_portfolios = load_portfolios()
    portfolio_names = list(saved_portfolios.keys())
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_portfolio = st.selectbox("加载已保存的组合", ["无"] + portfolio_names)
    with col2:
        if selected_portfolio != "无":
            if st.button("删除", key=f"delete_{selected_portfolio}"):
                delete_portfolio(selected_portfolio)
                st.rerun()

    # 自动刷新ETF列表，保证options和default一致
    options = list(etf_list['symbol'].unique())
    if selected_portfolio != "无":
        portfolio_config = saved_portfolios[selected_portfolio]
        default_etfs = portfolio_config['etfs']
    else:
        default_etfs = []
    from utils import get_etf_options_with_favorites
    if any(c not in options for c in default_etfs):
        etf_list = get_etf_list(force_refresh=True)
        options = get_etf_options_with_favorites(etf_list)
    else:
        options = get_etf_options_with_favorites(etf_list)
    default_etfs = [c for c in default_etfs if c in options]
    selected_etfs = st.multiselect(
        "选择ETF (至少2只)",
        options=options,
        default=default_etfs,
        format_func=lambda x: f"{x} - {etf_list[etf_list['symbol'] == x]['name'].values[0] if not etf_list[etf_list['symbol'] == x].empty else x}"
    )

    if etf_list.empty:
        st.error("无法获取ETF列表，请检查网络连接或数据源是否可用")
        return

    # 创建左右两列布局
    left_col, right_col = st.columns([1, 2.5])

    with left_col:
        st.header("参数设置")
        
        # 缓存管理
        with st.expander("缓存管理"):
            st.write("当前缓存信息:")
            cache_info = get_cache_info()
            st.text(cache_info)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("清除所有缓存"):
                    clear_cache()
                    st.rerun()
            with col2:
                if st.button("刷新缓存信息"):
                    st.rerun()

        # 如果选择了已保存的组合，则使用其配置
        if selected_portfolio != "无":
            portfolio_config = saved_portfolios[selected_portfolio]
            default_etfs = portfolio_config['etfs']
            default_weights = portfolio_config['weights']
        else:
            default_etfs = []
            default_weights = []

        weights = []
        if len(selected_etfs) >= 2:
            st.write("设置各ETF权重 (总和为100%)")
            total = 0
            for i, etf in enumerate(selected_etfs):
                name = etf_list[etf_list['symbol'] == etf]['name'].values[0]
                initial_weight = default_weights[i] if selected_portfolio != "无" and i < len(default_weights) else 100 // len(selected_etfs)
                weight = st.slider(f"{etf} - {name}", 0, 100, initial_weight, key=f"weight_{etf}")
                weights.append(weight)
                total += weight
            if total != 100:
                st.warning(f"权重总和为{total}%，请调整为100%")
                st.stop()
            new_portfolio_name = st.text_input("输入组合名称以保存")
            if st.button("保存组合"):
                if new_portfolio_name:
                    add_portfolio(new_portfolio_name, selected_etfs, weights)
                    st.success(f"组合 '{new_portfolio_name}' 已保存!")
                    st.rerun()
                else:
                    st.warning("请输入组合名称")
        
        # 再平衡选项
        st.subheader("再平衡设置")
        rebalance_annually = st.checkbox("启用年度再平衡", value=False, 
                                       help="每年第一个交易日自动将组合权重调整回目标权重")
        
        if rebalance_annually:
            st.info("💡 年度再平衡说明：每年第一个交易日自动调整持仓权重，保持目标配置")
        
        end_date = datetime.now() - timedelta(days=1)
        start_date = datetime(2020, 1, 1)
        date_range = st.date_input(
            "回测时间范围",
            value=(start_date, end_date),
            min_value=datetime(2010, 1, 1),
            max_value=end_date
        )
        if len(date_range) != 2:
            st.error("请选择完整的日期范围")
            return
        initial_investment = st.number_input("初始投资金额 (元)", min_value=1000, value=10000)
        if st.button("运行回测"):
            with st.spinner("正在计算..."):
                try:
                    portfolio_value, benchmark_value, returns, etf_data, etf_names, portfolio_value_rebalance = calculate_portfolio(
                        selected_etfs, weights, date_range[0], date_range[1], etf_list, initial_investment, rebalance_annually
                    )
                    if portfolio_value is not None:
                        st.session_state.portfolio_value = portfolio_value
                        st.session_state.benchmark_value = benchmark_value
                        st.session_state.returns = returns
                        st.session_state.etf_data = etf_data
                        st.session_state.etf_names = etf_names
                        st.session_state.selected_etfs = selected_etfs
                        st.session_state.actual_etfs = returns.columns.tolist()
                        st.session_state.initial_investment = initial_investment
                        st.session_state.annual_returns = calculate_annual_returns(portfolio_value)
                        st.session_state.portfolio_value_rebalance = portfolio_value_rebalance
                        st.session_state.rebalance_annually = rebalance_annually
                        
                        # 计算再平衡对比
                        if rebalance_annually and portfolio_value_rebalance is not None:
                            st.session_state.rebalance_comparison = calculate_rebalance_comparison(
                                portfolio_value, portfolio_value_rebalance, returns
                            )
                        
                        st.success("✅ 回测计算完成！请查看右侧结果")
                    else:
                        st.error("❌ 无法获取足够的数据进行回测")
                except Exception as e:
                    st.error(f"❌ 回测过程中发生错误: {str(e)}")
    with right_col:
        if 'portfolio_value' in st.session_state:
            st.header("回测结果")
            if len(st.session_state.selected_etfs) > len(st.session_state.actual_etfs):
                st.info(f"📌 实际使用的ETF: {', '.join(st.session_state.actual_etfs)}")
            
            # 显示再平衡对比结果
            if st.session_state.get('rebalance_annually', False) and st.session_state.get('portfolio_value_rebalance') is not None:
                st.subheader("再平衡对比结果")
                comparison = st.session_state.get('rebalance_comparison')
                if comparison:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("不再平衡总收益率", f"{comparison['no_rebalance']['total_return']:.2f}%")
                        st.metric("不再平衡年化收益率", f"{comparison['no_rebalance']['annual_return']:.2f}%")
                        st.metric("不再平衡最大回撤", f"{comparison['no_rebalance']['max_drawdown']:.2f}%")
                    with col2:
                        st.metric("再平衡总收益率", f"{comparison['rebalance']['total_return']:.2f}%")
                        st.metric("再平衡年化收益率", f"{comparison['rebalance']['annual_return']:.2f}%")
                        st.metric("再平衡最大回撤", f"{comparison['rebalance']['max_drawdown']:.2f}%")
                    with col3:
                        diff_color = "normal" if comparison['difference']['total_return'] >= 0 else "inverse"
                        st.metric("收益率差异", f"{comparison['difference']['total_return']:+.2f}%", delta_color=diff_color)
                        st.metric("年化收益率差异", f"{comparison['difference']['annual_return']:+.2f}%", delta_color=diff_color)
                        st.metric("最大回撤差异", f"{comparison['difference']['max_drawdown']:+.2f}%", delta_color=diff_color)
            
            st.subheader("净值曲线")
            
            # 创建动态净值曲线图
            fig = go.Figure()
            
            # 绘制不再平衡的净值曲线
            fig.add_trace(go.Scatter(
                x=st.session_state.portfolio_value.index,
                y=st.session_state.portfolio_value / st.session_state.initial_investment,
                mode='lines',
                name='投资组合(不再平衡)',
                line=dict(color='black', width=3),
                hovertemplate='<b>%{x}</b><br>净值: %{y:.4f}<extra></extra>'
            ))
            
            # 如果启用了再平衡，绘制再平衡的净值曲线
            if st.session_state.get('rebalance_annually', False) and st.session_state.get('portfolio_value_rebalance') is not None:
                fig.add_trace(go.Scatter(
                    x=st.session_state.portfolio_value_rebalance.index,
                    y=st.session_state.portfolio_value_rebalance / st.session_state.initial_investment,
                    mode='lines',
                    name='投资组合(年度再平衡)',
                    line=dict(color='red', width=3, dash='dash'),
                    hovertemplate='<b>%{x}</b><br>净值: %{y:.4f}<extra></extra>'
                ))
            
            # 绘制各ETF净值曲线
            colors = px.colors.qualitative.Set3
            for i, col in enumerate(st.session_state.etf_data.columns):
                symbol = col.split('_')[0]
                color = colors[i % len(colors)]
                fig.add_trace(go.Scatter(
                    x=st.session_state.etf_data[col].index,
                    y=st.session_state.etf_data[col] / st.session_state.etf_data[col].iloc[0],
                    mode='lines',
                    name=f"{st.session_state.etf_names[symbol]}",
                    line=dict(color=color, width=1.5),
                    opacity=0.7,
                    hovertemplate='<b>%{x}</b><br>%{fullData.name}<br>净值: %{y:.4f}<extra></extra>'
                ))
            
            # 绘制基准
            if st.session_state.benchmark_value is not None:
                fig.add_trace(go.Scatter(
                    x=st.session_state.benchmark_value.index,
                    y=st.session_state.benchmark_value / st.session_state.initial_investment,
                    mode='lines',
                    name='等权重基准',
                    line=dict(color='gray', width=2, dash='dot'),
                    hovertemplate='<b>%{x}</b><br>基准净值: %{y:.4f}<extra></extra>'
                ))
            
            # 更新布局
            fig.update_layout(
                title=dict(
                    text="投资组合与各ETF净值走势（归一化）",
                    x=0.5,
                    font=dict(size=16, color='black')
                ),
                xaxis_title="日期",
                yaxis_title="净值倍数",
                hovermode='x unified',
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                ),
                margin=dict(l=50, r=200, t=80, b=50),
                height=600
            )
            
            # 添加网格
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 显示性能指标（基于不再平衡的结果）
            st.subheader("性能指标")
            metrics = calculate_metrics(st.session_state.returns.sum(axis=1), 
                                      st.session_state.portfolio_value)
            cols = st.columns(5)
            metric_names = ['总收益率 (%)', '年化收益率 (%)', '年化波动率 (%)', '夏普比率', '最大回撤 (%)']
            for i, metric in enumerate(metric_names):
                cols[i].metric(metric, f"{metrics[metric]:.2f}{'%' if '%' in metric else ''}")
            
            # 添加回撤分析图
            st.subheader("回撤分析")
            
            # 计算回撤
            portfolio_returns = st.session_state.returns.sum(axis=1)
            cumulative_returns = (1 + portfolio_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max * 100
            
            fig = go.Figure()
            
            # 添加回撤区域
            fig.add_trace(go.Scatter(
                x=drawdown.index,
                y=drawdown,
                fill='tonexty',
                fillcolor='rgba(255, 0, 0, 0.3)',
                line=dict(color='red', width=2),
                name='回撤',
                hovertemplate='<b>%{x}</b><br>回撤: %{y:.2f}%<extra></extra>'
            ))
            
            # 添加0线
            fig.add_hline(y=0, line_dash="solid", line_color="black", opacity=0.5)
            
            fig.update_layout(
                title=dict(
                    text="投资组合回撤分析",
                    x=0.5,
                    font=dict(size=14, color='black')
                ),
                xaxis_title="日期",
                yaxis_title="回撤 (%)",
                height=400,
                yaxis=dict(range=[drawdown.min() - 5, 5])
            )
            
            # 添加网格
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 添加滚动收益率分析
            st.subheader("滚动收益率分析")
            
            # 计算滚动收益率
            portfolio_returns = st.session_state.returns.sum(axis=1)
            rolling_1y = (1 + portfolio_returns).rolling(window=252).apply(lambda x: (x.prod() - 1) * 100)
            rolling_6m = (1 + portfolio_returns).rolling(window=126).apply(lambda x: (x.prod() - 1) * 100)
            rolling_3m = (1 + portfolio_returns).rolling(window=63).apply(lambda x: (x.prod() - 1) * 100)
            
            fig = go.Figure()
            
            # 添加不同周期的滚动收益率
            fig.add_trace(go.Scatter(
                x=rolling_1y.index,
                y=rolling_1y,
                mode='lines',
                name='滚动1年收益率',
                line=dict(color='blue', width=2),
                hovertemplate='<b>%{x}</b><br>1年收益率: %{y:.2f}%<extra></extra>'
            ))
            
            fig.add_trace(go.Scatter(
                x=rolling_6m.index,
                y=rolling_6m,
                mode='lines',
                name='滚动6个月收益率',
                line=dict(color='green', width=2),
                hovertemplate='<b>%{x}</b><br>6个月收益率: %{y:.2f}%<extra></extra>'
            ))
            
            fig.add_trace(go.Scatter(
                x=rolling_3m.index,
                y=rolling_3m,
                mode='lines',
                name='滚动3个月收益率',
                line=dict(color='orange', width=2),
                hovertemplate='<b>%{x}</b><br>3个月收益率: %{y:.2f}%<extra></extra>'
            ))
            
            # 添加0线
            fig.add_hline(y=0, line_dash="solid", line_color="black", opacity=0.5)
            
            fig.update_layout(
                title=dict(
                    text="滚动收益率分析",
                    x=0.5,
                    font=dict(size=14, color='black')
                ),
                xaxis_title="日期",
                yaxis_title="滚动收益率 (%)",
                height=400,
                hovermode='x unified'
            )
            
            # 添加网格
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 添加波动率分析
            st.subheader("波动率分析")
            
            # 计算滚动波动率
            portfolio_returns = st.session_state.returns.sum(axis=1)
            rolling_vol_1y = portfolio_returns.rolling(window=252).std() * np.sqrt(252) * 100
            rolling_vol_6m = portfolio_returns.rolling(window=126).std() * np.sqrt(252) * 100
            rolling_vol_3m = portfolio_returns.rolling(window=63).std() * np.sqrt(252) * 100
            
            fig = go.Figure()
            
            # 添加不同周期的滚动波动率
            fig.add_trace(go.Scatter(
                x=rolling_vol_1y.index,
                y=rolling_vol_1y,
                mode='lines',
                name='滚动1年波动率',
                line=dict(color='purple', width=2),
                hovertemplate='<b>%{x}</b><br>1年波动率: %{y:.2f}%<extra></extra>'
            ))
            
            fig.add_trace(go.Scatter(
                x=rolling_vol_6m.index,
                y=rolling_vol_6m,
                mode='lines',
                name='滚动6个月波动率',
                line=dict(color='brown', width=2),
                hovertemplate='<b>%{x}</b><br>6个月波动率: %{y:.2f}%<extra></extra>'
            ))
            
            fig.add_trace(go.Scatter(
                x=rolling_vol_3m.index,
                y=rolling_vol_3m,
                mode='lines',
                name='滚动3个月波动率',
                line=dict(color='pink', width=2),
                hovertemplate='<b>%{x}</b><br>3个月波动率: %{y:.2f}%<extra></extra>'
            ))
            
            fig.update_layout(
                title=dict(
                    text="滚动波动率分析",
                    x=0.5,
                    font=dict(size=14, color='black')
                ),
                xaxis_title="日期",
                yaxis_title="年化波动率 (%)",
                height=400,
                hovermode='x unified'
            )
            
            # 添加网格
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 添加夏普比率分析
            st.subheader("夏普比率分析")
            
            # 计算滚动夏普比率（假设无风险利率为3%）
            portfolio_returns = st.session_state.returns.sum(axis=1)
            risk_free_rate = 0.03  # 3%年化无风险利率
            daily_rf_rate = (1 + risk_free_rate) ** (1/252) - 1
            
            # 计算滚动夏普比率
            rolling_return_1y = portfolio_returns.rolling(window=252).mean() * 252
            rolling_vol_1y = portfolio_returns.rolling(window=252).std() * np.sqrt(252)
            sharpe_1y = (rolling_return_1y - risk_free_rate) / rolling_vol_1y
            
            rolling_return_6m = portfolio_returns.rolling(window=126).mean() * 252
            rolling_vol_6m = portfolio_returns.rolling(window=126).std() * np.sqrt(252)
            sharpe_6m = (rolling_return_6m - risk_free_rate) / rolling_vol_6m
            
            rolling_return_3m = portfolio_returns.rolling(window=63).mean() * 252
            rolling_vol_3m = portfolio_returns.rolling(window=63).std() * np.sqrt(252)
            sharpe_3m = (rolling_return_3m - risk_free_rate) / rolling_vol_3m
            
            fig = go.Figure()
            
            # 添加不同周期的滚动夏普比率
            fig.add_trace(go.Scatter(
                x=sharpe_1y.index,
                y=sharpe_1y,
                mode='lines',
                name='滚动1年夏普比率',
                line=dict(color='darkblue', width=2),
                hovertemplate='<b>%{x}</b><br>1年夏普比率: %{y:.3f}<extra></extra>'
            ))
            
            fig.add_trace(go.Scatter(
                x=sharpe_6m.index,
                y=sharpe_6m,
                mode='lines',
                name='滚动6个月夏普比率',
                line=dict(color='darkgreen', width=2),
                hovertemplate='<b>%{x}</b><br>6个月夏普比率: %{y:.3f}<extra></extra>'
            ))
            
            fig.add_trace(go.Scatter(
                x=sharpe_3m.index,
                y=sharpe_3m,
                mode='lines',
                name='滚动3个月夏普比率',
                line=dict(color='darkorange', width=2),
                hovertemplate='<b>%{x}</b><br>3个月夏普比率: %{y:.3f}<extra></extra>'
            ))
            
            # 添加0线和1线
            fig.add_hline(y=0, line_dash="solid", line_color="black", opacity=0.5)
            fig.add_hline(y=1, line_dash="dash", line_color="gray", opacity=0.5)
            
            fig.update_layout(
                title=dict(
                    text="滚动夏普比率分析",
                    x=0.5,
                    font=dict(size=14, color='black')
                ),
                xaxis_title="日期",
                yaxis_title="夏普比率",
                height=400,
                hovermode='x unified'
            )
            
            # 添加网格
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 添加资产配置饼图
            st.subheader("资产配置")
            
            # 创建饼图显示各ETF的权重
            fig = go.Figure(data=[go.Pie(
                labels=[f"{etf} - {st.session_state.etf_names[etf]}" for etf in st.session_state.selected_etfs],
                values=weights,
                hole=0.3,
                textinfo='label+percent',
                textposition='inside',
                hovertemplate='<b>%{label}</b><br>权重: %{value}%<br>占比: %{percent}<extra></extra>'
            )])
            
            fig.update_layout(
                title=dict(
                    text="投资组合资产配置",
                    x=0.5,
                    font=dict(size=14, color='black')
                ),
                height=400,
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 添加收益分布分析
            st.subheader("收益分布分析")
            
            # 计算日收益率分布
            portfolio_returns = st.session_state.returns.sum(axis=1)
            
            fig = go.Figure()
            
            # 添加直方图
            fig.add_trace(go.Histogram(
                x=portfolio_returns * 100,  # 转换为百分比
                nbinsx=50,
                name='日收益率分布',
                opacity=0.7,
                marker_color='lightblue',
                hovertemplate='<b>收益率区间</b><br>频次: %{y}<br>收益率: %{x:.2f}%<extra></extra>'
            ))
            
            # 添加正态分布拟合线
            mean_return = portfolio_returns.mean() * 100
            std_return = portfolio_returns.std() * 100
            x_norm = np.linspace(portfolio_returns.min() * 100, portfolio_returns.max() * 100, 100)
            y_norm = len(portfolio_returns) * (portfolio_returns.max() - portfolio_returns.min()) * 100 / 50 * \
                     (1 / (std_return * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_norm - mean_return) / std_return) ** 2)
            
            fig.add_trace(go.Scatter(
                x=x_norm,
                y=y_norm,
                mode='lines',
                name='正态分布拟合',
                line=dict(color='red', width=2),
                hovertemplate='<b>正态分布</b><br>收益率: %{x:.2f}%<br>密度: %{y:.1f}<extra></extra>'
            ))
            
            fig.update_layout(
                title=dict(
                    text="日收益率分布",
                    x=0.5,
                    font=dict(size=14, color='black')
                ),
                xaxis_title="日收益率 (%)",
                yaxis_title="频次",
                height=400,
                barmode='overlay'
            )
            
            # 添加网格
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 显示分布统计信息
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("平均日收益率", f"{mean_return:.4f}%")
            with col2:
                st.metric("日收益率标准差", f"{std_return:.4f}%")
            with col3:
                skewness = portfolio_returns.skew()
                st.metric("偏度", f"{skewness:.3f}")
            with col4:
                kurtosis = portfolio_returns.kurtosis()
                st.metric("峰度", f"{kurtosis:.3f}")
            
            st.subheader("年度收益率")
            if hasattr(st.session_state, 'annual_returns'):
                annual_returns = st.session_state.annual_returns
                
                # 创建年度收益可视化
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # 年度收益柱状图
                    years = annual_returns.index
                    returns = annual_returns.values
                    
                    # 设置颜色 - 涨用红色，跌用绿色
                    colors = ['red' if r >= 0 else 'green' for r in returns]
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Bar(
                        x=years,
                        y=returns,
                        marker_color=colors,
                        opacity=0.7,
                        text=[f'{r:.1f}%' for r in returns],
                        textposition='auto',
                        hovertemplate='<b>%{x}年</b><br>收益率: %{y:.2f}%<extra></extra>'
                    ))
                    
                    fig.update_layout(
                        title=dict(
                            text="投资组合年度收益率",
                            x=0.5,
                            font=dict(size=14, color='black')
                        ),
                        xaxis_title="年份",
                        yaxis_title="收益率 (%)",
                        showlegend=False,
                        height=400
                    )
                    
                    # 添加0线
                    fig.add_hline(y=0, line_dash="solid", line_color="black", opacity=0.5)
                    
                    # 添加网格
                    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
                    
                    st.plotly_chart(fig, use_container_width=True)
                
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
                
                # 添加颜色标识
                def style_annual_returns(df):
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
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("ETF相关性矩阵")
                corr_matrix = st.session_state.returns.corr()
                
                fig = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    colorscale='RdBu',
                    zmid=0,
                    text=corr_matrix.round(2).values,
                    texttemplate="%{text}",
                    textfont={"size": 10},
                    hovertemplate='<b>%{y} vs %{x}</b><br>相关性: %{z:.3f}<extra></extra>'
                ))
                
                fig.update_layout(
                    title=dict(
                        text="ETF相关性矩阵",
                        x=0.5,
                        font=dict(size=14, color='black')
                    ),
                    height=500,
                    xaxis_title="ETF",
                    yaxis_title="ETF"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.subheader("收益率统计")
                st.dataframe(st.session_state.returns.describe(), use_container_width=True)
            
            st.subheader("导出报告")
            if st.button("生成PDF报告", key="portfolio_pdf_btn"):
                with st.spinner("正在生成PDF报告..."):
                    try:
                        pdf_buffer = create_portfolio_backtest_pdf(
                            st.session_state.portfolio_value,
                            st.session_state.benchmark_value,
                            st.session_state.returns,
                            st.session_state.etf_data,
                            st.session_state.etf_names,
                            metrics,
                            st.session_state.annual_returns,
                            st.session_state.initial_investment,
                            st.session_state.selected_etfs
                        )
                        st.markdown(get_pdf_download_link(pdf_buffer, "ETF组合回测报告.pdf"), unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"❌ 生成PDF报告时发生错误: {str(e)}")

            # ====== AI智能分析区 ======
            st.markdown("---")
            st.subheader("🔎 AI智能分析")
            api_key = get_api_key()
            if not api_key:
                st.warning("未检测到API Key，请前往【API密钥配置】页面设置，否则无法使用AI分析功能。")
            else:
                if st.button("让AI分析本次回测结果", key="ai_analyze_backtest"):
                    # 组织回测主要结果数据
                    summary = "本次回测ETF配置：" + ", ".join(st.session_state.selected_etfs) + "\n"
                    summary += f"初始投资：{st.session_state.initial_investment}元\n"
                    if 'annual_returns' in st.session_state:
                        summary += "年度收益率：\n" + st.session_state.annual_returns.to_string() + "\n"
                    if 'portfolio_value' in st.session_state:
                        summary += f"最终资产：{st.session_state.portfolio_value[-1]:.2f}元\n"
                    if 'returns' in st.session_state:
                        total_return = (st.session_state.portfolio_value[-1] / st.session_state.initial_investment - 1) * 100
                        summary += f"总收益率：{total_return:.2f}%\n"
                    if 'benchmark_value' in st.session_state:
                        bm_return = (st.session_state.benchmark_value[-1] / st.session_state.initial_investment - 1) * 100
                        summary += f"基准收益率：{bm_return:.2f}%\n"
                    prompt = f"请分析以下ETF组合回测结果，简明总结收益、波动、回撤、配置优劣，并给出改进建议：\n{summary}"
                    with st.spinner("AI正在分析，请稍候..."):
                        result = ai_chat(prompt, api_key=api_key)
                    st.markdown("#### AI分析结果：")
                    st.write(result)

portfolio_backtest() 