import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from data import get_etf_list, load_metadata
from dca import calculate_dca
from portfolio_config import load_portfolios
import os
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

# 定投回测页面

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

def dca_backtest():
    # 设置页面配置
    st.set_page_config(
        page_title="ETF定投回测工具",
        page_icon="💰",
        layout="wide",  # 使用宽屏布局
        initial_sidebar_state="expanded"
    )
    
    st.title("ETF定投回测工具")
    global etf_list
    etf_list = get_etf_list()
    if etf_list.empty:
        st.error("无法获取ETF列表，请检查网络连接或数据源是否可用")
        return
    
    # 创建左右两列布局，调整比例
    left_col, right_col = st.columns([1, 2.5])
    
    with left_col:
        st.header("定投参数设置")
        
        # 缓存管理
        with st.expander("缓存管理"):
            st.write("当前缓存信息:")
            cache_info = get_cache_info()
            st.text(cache_info)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("清除所有缓存", key="dca_clear_cache"):
                    clear_cache()
                    st.rerun()
            with col2:
                if st.button("刷新缓存信息", key="dca_refresh_cache"):
                    st.rerun()
        
        from utils import get_etf_options_with_favorites
        etf_options = get_etf_options_with_favorites(etf_list)
        # 默认值可根据实际业务逻辑设定，这里假设无默认值
        raw_default = []
        if etf_options and raw_default:
            default = [type(etf_options[0])(x) for x in raw_default]
            default = [x for x in default if x in etf_options]
        else:
            default = []
        selected_etfs = st.multiselect(
            "选择ETF (至少1只)",
            options=etf_options,
            format_func=lambda x: f"{x} - {etf_list[etf_list['symbol'] == x]['name'].values[0]}",
            default=default
        )
        weights = []
        if len(selected_etfs) >= 1:
            st.write("设置各ETF权重 (总和为100%)")
            total = 0
            for i, etf in enumerate(selected_etfs):
                name = etf_list[etf_list['symbol'] == etf]['name'].values[0]
                weight = st.slider(f"{etf} - {name}", 0, 100, 100//len(selected_etfs), key=f"dca_weight_{i}")
                weights.append(weight)
                total += weight
            if total != 100:
                st.warning(f"权重总和为{total}%，请调整为100%")
                st.stop()
        # 定投时间范围快捷选择
        st.write("定投时间范围")
        period = st.radio(
            "选择回测区间",
            ["近三年", "近五年", "近十年", "全部数据"],
            index=0,
            horizontal=True
        )
        end_date = datetime.now() - timedelta(days=1)
        # 计算所有选中ETF的最早可用数据日期
        min_start = datetime(2010, 1, 1)
        if len(selected_etfs) >= 1:
            from data import fetch_etf_data_with_retry
            min_dates = []
            for etf in selected_etfs:
                df = fetch_etf_data_with_retry(etf, min_start, end_date, etf_list)
                if not df.empty:
                    min_dates.append(df.index.min())
            if min_dates:
                min_start = max(min(min_dates), datetime(2010, 1, 1))
        if period == "近三年":
            start_date = max(end_date - timedelta(days=365*3), min_start)
        elif period == "近五年":
            start_date = max(end_date - timedelta(days=365*5), min_start)
        elif period == "近十年":
            start_date = max(end_date - timedelta(days=365*10), min_start)
        else:
            start_date = min_start
        st.info(f"回测区间：{start_date.date()} ~ {end_date.date()} (如数据不足则自动从最早可用日期开始)")
        monthly_amount = st.number_input("每月定投金额 (元)", min_value=100, value=1000)
        invest_day = st.slider("每月定投日", 1, 31, 1)
        if st.button("运行定投回测"):
            with st.spinner("正在计算..."):
                try:
                    portfolio_value, total_invested, returns, etf_data, annualized_return = calculate_dca(
                        selected_etfs, weights, start_date, end_date, monthly_amount, invest_day, etf_list
                    )
                    if portfolio_value is not None:
                        st.session_state.dca_portfolio_value = portfolio_value
                        st.session_state.dca_total_invested = total_invested
                        st.session_state.dca_returns = returns
                        st.session_state.dca_etf_data = etf_data
                        st.session_state.dca_selected_etfs = selected_etfs
                        st.session_state.dca_annualized_return = annualized_return
                        st.success("✅ 定投回测计算完成！请查看右侧结果")
                    else:
                        st.error("❌ 无法获取足够的数据进行回测")
                except Exception as e:
                    st.error(f"❌ 定投回测过程中发生错误: {str(e)}")
    with right_col:
        if 'dca_portfolio_value' in st.session_state:
            st.header("定投回测结果")
            final_value = st.session_state.dca_portfolio_value.iloc[-1]
            total_invested = st.session_state.dca_total_invested.iloc[-1]
            total_return = (final_value / total_invested - 1) * 100
            # 统计累计定投月数
            invest_months = len(st.session_state.dca_portfolio_value)
            start_dt = st.session_state.dca_portfolio_value.index[0]
            end_dt = st.session_state.dca_portfolio_value.index[-1]
            # 收益指标
            rf = 0.02  # 无风险利率2%
            monthly_returns = st.session_state.dca_portfolio_value.pct_change().dropna()
            annual_volatility = monthly_returns.std() * np.sqrt(12)
            sharpe = (st.session_state.dca_annualized_return/100 - rf) / annual_volatility if annual_volatility > 0 else np.nan
            downside = monthly_returns[monthly_returns < 0]
            downside_vol = downside.std() * np.sqrt(12)
            sortino = (st.session_state.dca_annualized_return/100 - rf) / downside_vol if downside_vol > 0 else np.nan
            # 一次性投资对比（修正：用标的本身价格或加权组合价格）
            if 'dca_etf_data' in st.session_state and st.session_state.dca_etf_data is not None:
                etf_data = st.session_state.dca_etf_data
                if etf_data.shape[1] == 1:
                    # 单一ETF，直接用其价格
                    price_series = etf_data.iloc[:, 0]
                else:
                    # 多ETF，按初始权重加权
                    weights_arr = np.array(weights)
                    weights_arr = weights_arr / weights_arr.sum()  # 归一化
                    price_matrix = etf_data.values
                    price_series = price_matrix @ weights_arr
                    price_series = pd.Series(price_series, index=etf_data.index)
                start_price = price_series.iloc[0]
                end_price = price_series.iloc[-1]
                lump_sum_return = (end_price / start_price - 1) * 100
            else:
                # 兜底，仍用原有方式
                start_price = st.session_state.dca_portfolio_value.iloc[0]
                end_price = st.session_state.dca_portfolio_value.iloc[-1]
                lump_sum_return = (end_price / start_price - 1) * 100
            # 胜率分析
            win_rate = (monthly_returns > 0).sum() / len(monthly_returns) if len(monthly_returns) > 0 else np.nan
            # 年度收益
            annual_returns = st.session_state.dca_portfolio_value.resample('Y').last().pct_change().dropna() * 100
            # 最大回撤计算
            max_value = st.session_state.dca_portfolio_value.cummax()
            drawdown = (st.session_state.dca_portfolio_value - max_value) / max_value
            max_drawdown = drawdown.min() * 100
            # 结论总结用数字图标卡美化展示（两行对齐）
            total_days = (end_dt - start_dt).days
            simple_annual_return = ((final_value / total_invested) ** (365 / total_days) - 1) * 100
            st.markdown("---")
            st.markdown("<h4 style='text-align:center;'>结论总结</h4>", unsafe_allow_html=True)
            # 第一行（4列）
            row1 = [
                ("累计投入金额", f"{total_invested:,.2f} 元"),
                ("当前价值", f"{final_value:,.2f} 元"),
                ("总收益率", f"{total_return:.2f}%"),
                ("年化收益率(XIRR)", f"{st.session_state.dca_annualized_return:.2f}%")
            ]
            cols1 = st.columns(4, gap="large")
            for i, (label, value) in enumerate(row1):
                with cols1[i]:
                    st.metric(label, value)
            # 第二行（4列，最后一个空）
            row2 = [
                ("年化收益率(简单)", f"{simple_annual_return:.2f}%"),
                ("波动率(年化)", f"{annual_volatility*100:.2f}%"),
                ("一次性投资总收益率", f"{lump_sum_return:.2f}%")
            ]
            cols2 = st.columns(4, gap="large")
            for i, (label, value) in enumerate(row2):
                with cols2[i]:
                    st.metric(label, value)

            st.markdown("---")
            # 详细计算过程可继续用expander展开
            with st.expander("详细计算过程"):
                st.markdown(f"""
- 总收益率 = (当前价值 / 累计投入金额 - 1) × 100%
- 年化收益率（XIRR）：用现金流序列计算内部收益率（XIRR）
- 年化收益率（简单）= (期末价值/期初投入)^(365/投资天数) - 1
- 波动率（年化）= 月收益率标准差 × √12
- 一次性投资总收益率 = (期末价格 / 起始价格 - 1) × 100%
- 最大回撤 = 从历史最高点到最低点的最大跌幅百分比
""")

            # 标的本身的趋势图（提前展示）
            st.subheader("标的本身的价格趋势图")
            if 'dca_etf_data' in st.session_state and st.session_state.dca_etf_data is not None:
                etf_data = st.session_state.dca_etf_data.copy()
                fig_etf = go.Figure()
                for col in etf_data.columns:
                    # 计算涨跌幅
                    price_series = etf_data[col]
                    returns = (price_series / price_series.iloc[0] - 1) * 100
                    fig_etf.add_trace(go.Scatter(
                        x=returns.index, y=returns,
                        mode='lines', name=f"{col}涨跌幅",
                        hovertemplate='日期: %{x}<br>涨跌幅: %{y:.2f}%'
                    ))
                # 添加定投收益率曲线
                dca_returns = (st.session_state.dca_portfolio_value / st.session_state.dca_total_invested - 1) * 100
                fig_etf.add_trace(go.Scatter(
                    x=dca_returns.index, y=dca_returns,
                    mode='lines', name='定投收益率', line=dict(width=3, color='red', dash='dash'),
                    hovertemplate='日期: %{x}<br>定投收益率: %{y:.2f}%'
                ))
                fig_etf.update_layout(
                    title="标的涨跌幅趋势图",
                    xaxis_title="日期", yaxis_title="涨跌幅 (%)",
                    legend=dict(font=dict(size=12)),
                    hovermode='x unified'
                )
                st.plotly_chart(fig_etf, use_container_width=True)

            # 投入与盈利分解面积图
            st.subheader("投入与盈利分解（交互式）")
            profit = st.session_state.dca_portfolio_value - st.session_state.dca_total_invested
            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(
                x=st.session_state.dca_portfolio_value.index, y=st.session_state.dca_total_invested,
                fill='tozeroy', mode='none', name='累计投入', fillcolor='rgba(0,200,0,0.4)',
                hovertemplate='日期: %{x}<br>累计投入: %{y:,.2f} 元'
            ))
            fig5.add_trace(go.Scatter(
                x=st.session_state.dca_portfolio_value.index, y=st.session_state.dca_portfolio_value,
                fill='tonexty', mode='none', name='盈利部分', fillcolor='rgba(0,0,200,0.4)',
                hovertemplate='日期: %{x}<br>总资产: %{y:,.2f} 元'
            ))
            fig5.add_trace(go.Scatter(
                x=st.session_state.dca_portfolio_value.index, y=st.session_state.dca_portfolio_value,
                mode='lines', name='总资产', line=dict(width=2, color='black'),
                hovertemplate='日期: %{x}<br>总资产: %{y:,.2f} 元'
            ))
            fig5.update_layout(
                title="累计投入与盈利分解",
                xaxis_title="日期", yaxis_title="金额 (元)",
                legend=dict(font=dict(size=12)),
                hovermode='x unified'
            )
            st.plotly_chart(fig5, use_container_width=True)
            
            st.subheader("定投记录")
            records_df = pd.DataFrame({
                '定投日期': st.session_state.dca_portfolio_value.index,
                '累计投入 (元)': st.session_state.dca_total_invested,
                '当前价值 (元)': st.session_state.dca_portfolio_value,
                '收益率 (%)': st.session_state.dca_returns
            }).set_index('定投日期')
            st.dataframe(records_df.style.format({
                '累计投入 (元)': '{:,.2f}',
                '当前价值 (元)': '{:,.2f}',
                '收益率 (%)': '{:.2f}'
            }), use_container_width=True)

            # 交易明细表格
            st.subheader("定投交易明细")
            # 需从dca.py返回dca_records，假设已在st.session_state.dca_records
            if hasattr(st.session_state, 'dca_records'):
                records_df = pd.DataFrame(st.session_state.dca_records)
                st.dataframe(records_df, use_container_width=True)

            # 年度收益表现（表格展示，修正算法）
            st.subheader("年度收益表现")
            # 定投年度收益（年末市值/年初市值-1）
            dca_yearly_value = st.session_state.dca_portfolio_value.resample('Y').last()
            dca_annual_returns = dca_yearly_value.pct_change().dropna() * 100
            # 标的本身年度收益
            if 'dca_etf_data' in st.session_state and st.session_state.dca_etf_data is not None:
                etf_data = st.session_state.dca_etf_data
                if etf_data.shape[1] == 1:
                    price_series = etf_data.iloc[:, 0]
                    etf_annual_returns = price_series.resample('Y').last().pct_change().dropna() * 100
                else:
                    weights_arr = np.array(weights)
                    weights_arr = weights_arr / weights_arr.sum()
                    price_matrix = etf_data.values
                    weighted_prices = price_matrix @ weights_arr
                    weighted_series = pd.Series(weighted_prices, index=etf_data.index)
                    etf_annual_returns = weighted_series.resample('Y').last().pct_change().dropna() * 100
                # 合并为表格
                annual_df = pd.DataFrame({
                    '定投年度收益(%)': dca_annual_returns,
                    '标的年度收益(%)': etf_annual_returns
                })
                annual_df.index = annual_df.index.year
                st.dataframe(annual_df.style.format('{:.2f}'), use_container_width=True)
            else:
                st.dataframe(dca_annual_returns.to_frame('定投年度收益(%)').style.format('{:.2f}'), use_container_width=True)

            st.subheader("标的本身月度收益热力图")
            # 计算标的本身的价格序列
            if 'dca_etf_data' in st.session_state and st.session_state.dca_etf_data is not None:
                etf_data = st.session_state.dca_etf_data
                if etf_data.shape[1] == 1:
                    price_series = etf_data.iloc[:, 0]
                else:
                    weights_arr = np.array(weights)
                    weights_arr = weights_arr / weights_arr.sum()
                    price_matrix = etf_data.values
                    weighted_prices = price_matrix @ weights_arr
                    price_series = pd.Series(weighted_prices, index=etf_data.index)
                # 计算月度收益率
                monthly_price = price_series.resample('M').last()
                monthly_ret = monthly_price.pct_change() * 100
                heatmap_df = monthly_ret.to_frame(name='收益率').reset_index()
                heatmap_df['年'] = heatmap_df['日期'].dt.year
                heatmap_df['月'] = heatmap_df['日期'].dt.month
                heatmap_pivot = heatmap_df.pivot(index='年', columns='月', values='收益率').fillna(0)
                import plotly.figure_factory as ff
                fig_heat = ff.create_annotated_heatmap(
                    z=heatmap_pivot.values,
                    x=[str(m) for m in heatmap_pivot.columns],
                    y=[str(y) for y in heatmap_pivot.index],
                    annotation_text=np.round(heatmap_pivot.values, 2),
                    colorscale='RdBu', showscale=True, reversescale=True
                )
                fig_heat.update_layout(title="标的本身月度收益热力图", xaxis_title="月份", yaxis_title="年份")
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.info("暂无标的价格数据，无法绘制热力图。")

            # 收益对比雷达图
            st.subheader("收益对比雷达图")
            radar_metrics = {
                '总收益率': total_return,
                '年化收益率': st.session_state.dca_annualized_return,
                '波动率': annual_volatility*100,
                'Sharpe比率': sharpe,
                'Sortino比率': sortino,
                '一次性投资收益率': lump_sum_return
            }
            radar_labels = list(radar_metrics.keys())
            radar_values = [radar_metrics[k] for k in radar_labels]
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=radar_values,
                theta=radar_labels,
                fill='toself',
                name='定投策略'
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True)),
                showlegend=False,
                title="收益与风险指标雷达图"
            )
            st.plotly_chart(fig_radar, use_container_width=True)

dca_backtest() 