import streamlit as st
import pandas as pd
import numpy as np
from data import fetch_etf_data_with_retry
from utils import clean_etf_symbol

# 计算组合收益（支持年度再平衡）
def calculate_portfolio(etfs, weights, start_date, end_date, etf_list, initial_investment=10000, rebalance_annually=False):
    data = pd.DataFrame()
    unavailable_etfs = []
    etf_names = {}
    
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    st.write(f"\n⏳ 回测日期范围：{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    for etf in etfs:
        etf_data = fetch_etf_data_with_retry(etf, start_date, end_date, etf_list)
        if etf_data.empty:
            unavailable_etfs.append(etf)
            continue
            
        if data.empty:
            data = etf_data
        else:
            data = data.join(etf_data, how='outer')
        
        # 保存ETF名称映射
        for col in etf_data.columns:
            parts = col.split('_')
            etf_names[parts[0]] = '_'.join(parts[1:])
    
    if unavailable_etfs:
        st.warning(f"⚠️ 以下ETF无法获取数据: {', '.join(unavailable_etfs)}")
    
    if data.empty or len(data.columns) < 2:  # 至少需要2只ETF的数据
        st.error("❌ 无法获取足够的数据进行回测")
        return None, None, None, None, None, None
    
    data.fillna(method='ffill', inplace=True)
    returns = data.pct_change().dropna()
    
    # 重新调整权重（只针对可获取数据的ETF）
    valid_weights = np.array([weights[etfs.index(etf)] for etf in etfs if clean_etf_symbol(etf) in etf_names])
    valid_weights = valid_weights / valid_weights.sum()
    
    # 计算不进行再平衡的组合收益
    portfolio_returns_no_rebalance = (returns * valid_weights).sum(axis=1)
    cumulative_returns_no_rebalance = (1 + portfolio_returns_no_rebalance).cumprod()
    portfolio_value_no_rebalance = initial_investment * cumulative_returns_no_rebalance
    
    # 计算基准收益
    benchmark_weights = np.ones(len(data.columns)) / len(data.columns)
    benchmark_value = initial_investment * (1 + (returns * benchmark_weights).sum(axis=1)).cumprod()
    
    # 如果不需要再平衡，直接返回结果
    if not rebalance_annually:
        return portfolio_value_no_rebalance, benchmark_value, returns, data, etf_names, None
    
    # 计算年度再平衡的组合收益
    portfolio_value_rebalance = calculate_rebalanced_portfolio(data, valid_weights, initial_investment, start_date, end_date)
    
    # 检查再平衡结果是否有效
    if portfolio_value_rebalance is None:
        st.error("❌ 再平衡计算失败，返回不再平衡的结果")
        return portfolio_value_no_rebalance, benchmark_value, returns, data, etf_names, None
    
    return portfolio_value_no_rebalance, benchmark_value, returns, data, etf_names, portfolio_value_rebalance

def calculate_rebalanced_portfolio(data, target_weights, initial_investment, start_date, end_date):
    """修正：严格年度再平衡，每年首日用总市值按目标权重重新分配份额"""
    # 数据预处理和验证
    trading_days = data.index
    n_assets = data.shape[1]
    
    # 处理无效价格数据：使用前向填充
    data_clean = data.copy()
    data_clean = data_clean.fillna(method='ffill').fillna(method='bfill')
    
    # 检查是否还有无效数据
    if np.any(data_clean <= 0):
        st.warning("⚠️ 发现价格为0的数据，使用前向填充处理")
        # 将0值替换为前一个有效值
        for col in data_clean.columns:
            data_clean[col] = data_clean[col].replace(0, method='ffill')
    
    prices = data_clean.values
    
    # 最终检查：如果仍有无效数据，使用相邻有效值
    for i in range(prices.shape[0]):
        for j in range(prices.shape[1]):
            if prices[i, j] <= 0 or np.isnan(prices[i, j]):
                # 使用前一个有效值
                if i > 0:
                    prices[i, j] = prices[i-1, j]
                elif i < prices.shape[0] - 1:
                    prices[i, j] = prices[i+1, j]
                else:
                    st.error(f"❌ 无法找到有效价格数据，位置: 第{i}行，第{j}列")
                    return None
    
    weights = np.array(target_weights)
    weights = weights / weights.sum()
    
    # 验证权重
    if np.any(np.isnan(weights)) or np.any(weights <= 0):
        st.error("❌ 权重数据无效，无法计算再平衡")
        return None

    # 初始化：用初始资金按权重买入各资产
    initial_prices = prices[0]
    holdings = initial_investment * weights / initial_prices
    portfolio_values = [initial_investment]
    rebalance_dates = [trading_days[0]]
    last_rebalance_year = trading_days[0].year

    for i in range(1, len(trading_days)):
        date = trading_days[i]
        current_prices = prices[i]
        
        # 每年首日再平衡
        if date.year != last_rebalance_year:
            # 计算当前总市值
            total_value = np.sum(holdings * current_prices)
            
            # 按目标权重重新分配份额
            holdings = total_value * weights / current_prices
            rebalance_dates.append(date)
            last_rebalance_year = date.year
        
        # 每日市值变动
        portfolio_value = np.sum(holdings * current_prices)
        portfolio_values.append(portfolio_value)

    portfolio_series = pd.Series(portfolio_values, index=trading_days)
    
    if rebalance_dates:
        st.info(f"年度再平衡：共进行了 {len(rebalance_dates)} 次再平衡")
        st.write(f"再平衡日期：{', '.join([d.strftime('%Y-%m-%d') for d in rebalance_dates])}")
    
    return portfolio_series

# 计算再平衡与不再平衡的对比指标
def calculate_rebalance_comparison(portfolio_no_rebalance, portfolio_rebalance, returns):
    """计算再平衡与不再平衡的对比指标"""
    if portfolio_rebalance is None:
        return None
    
    # 检查输入数据是否有效
    if (portfolio_no_rebalance is None or 
        np.any(np.isnan(portfolio_no_rebalance)) or 
        np.any(portfolio_no_rebalance <= 0)):
        st.error("❌ 不再平衡组合数据无效")
        return None
    
    if (portfolio_rebalance is None or 
        np.any(np.isnan(portfolio_rebalance)) or 
        np.any(portfolio_rebalance <= 0)):
        st.error("❌ 再平衡组合数据无效")
        return None
    
    # 计算收益率
    returns_no_rebalance = portfolio_no_rebalance.pct_change().dropna()
    returns_rebalance = portfolio_rebalance.pct_change().dropna()
    
    # 检查收益率数据
    if len(returns_no_rebalance) == 0 or len(returns_rebalance) == 0:
        st.error("❌ 收益率数据不足，无法计算对比指标")
        return None
    
    # 计算总收益率
    try:
        total_return_no_rebalance = (portfolio_no_rebalance.iloc[-1] / portfolio_no_rebalance.iloc[0] - 1) * 100
        total_return_rebalance = (portfolio_rebalance.iloc[-1] / portfolio_rebalance.iloc[0] - 1) * 100
    except Exception as e:
        st.error(f"❌ 计算总收益率失败: {e}")
        return None
    
    # 检查总收益率是否有效
    if np.isnan(total_return_no_rebalance) or np.isnan(total_return_rebalance):
        st.error("❌ 总收益率计算结果无效")
        return None
    
    # 计算年化收益率
    try:
        days = len(portfolio_no_rebalance)
        annual_return_no_rebalance = ((portfolio_no_rebalance.iloc[-1] / portfolio_no_rebalance.iloc[0]) ** (252/days) - 1) * 100
        annual_return_rebalance = ((portfolio_rebalance.iloc[-1] / portfolio_rebalance.iloc[0]) ** (252/days) - 1) * 100
    except Exception as e:
        st.error(f"❌ 计算年化收益率失败: {e}")
        return None
    
    # 计算波动率
    try:
        volatility_no_rebalance = returns_no_rebalance.std() * np.sqrt(252) * 100
        volatility_rebalance = returns_rebalance.std() * np.sqrt(252) * 100
    except Exception as e:
        st.error(f"❌ 计算波动率失败: {e}")
        return None
    
    # 计算夏普比率（假设无风险利率为3%）
    risk_free_rate = 3
    try:
        sharpe_no_rebalance = (annual_return_no_rebalance - risk_free_rate) / volatility_no_rebalance if volatility_no_rebalance > 0 else 0
        sharpe_rebalance = (annual_return_rebalance - risk_free_rate) / volatility_rebalance if volatility_rebalance > 0 else 0
    except Exception as e:
        st.error(f"❌ 计算夏普比率失败: {e}")
        return None
    
    # 计算最大回撤
    def calculate_max_drawdown(values):
        try:
            peak = values.expanding().max()
            drawdown = (values - peak) / peak * 100
            return drawdown.min()
        except Exception as e:
            st.error(f"❌ 计算最大回撤失败: {e}")
            return 0
    
    max_dd_no_rebalance = calculate_max_drawdown(portfolio_no_rebalance)
    max_dd_rebalance = calculate_max_drawdown(portfolio_rebalance)
    
    # 计算差异
    try:
        return_diff = total_return_rebalance - total_return_no_rebalance
        annual_diff = annual_return_rebalance - annual_return_no_rebalance
        volatility_diff = volatility_rebalance - volatility_no_rebalance
        sharpe_diff = sharpe_rebalance - sharpe_no_rebalance
        max_dd_diff = max_dd_rebalance - max_dd_no_rebalance
    except Exception as e:
        st.error(f"❌ 计算差异指标失败: {e}")
        return None
    
    return {
        'no_rebalance': {
            'total_return': total_return_no_rebalance,
            'annual_return': annual_return_no_rebalance,
            'volatility': volatility_no_rebalance,
            'sharpe_ratio': sharpe_no_rebalance,
            'max_drawdown': max_dd_no_rebalance
        },
        'rebalance': {
            'total_return': total_return_rebalance,
            'annual_return': annual_return_rebalance,
            'volatility': volatility_rebalance,
            'sharpe_ratio': sharpe_rebalance,
            'max_drawdown': max_dd_rebalance
        },
        'difference': {
            'total_return': return_diff,
            'annual_return': annual_diff,
            'volatility': volatility_diff,
            'sharpe_ratio': sharpe_diff,
            'max_drawdown': max_dd_diff
        }
    }