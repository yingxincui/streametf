import numpy as np

# 性能指标计算
def calculate_metrics(returns, portfolio_value):
    if returns is None or portfolio_value is None:
        return {}
    
    total_days = len(returns)
    total_return = (portfolio_value[-1] / portfolio_value[0] - 1) * 100
    annualized_return = ((1 + total_return/100) ** (365/total_days) - 1) * 100
    volatility = returns.std() * np.sqrt(252) * 100
    sharpe_ratio = (annualized_return / 100) / (volatility / 100) if volatility != 0 else 0
    
    max_value = portfolio_value.cummax()
    drawdown = (portfolio_value - max_value) / max_value
    max_drawdown = drawdown.min() * 100
    
    return {
        '总收益率 (%)': total_return,
        '年化收益率 (%)': annualized_return,
        '年化波动率 (%)': volatility,
        '夏普比率': sharpe_ratio,
        '最大回撤 (%)': max_drawdown
    }