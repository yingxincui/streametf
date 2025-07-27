import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objs as go

class EfficientFrontier:
    def __init__(self, price_df, risk_free_rate=0.0):
        """
        price_df: DataFrame, index为日期，columns为资产名，值为价格
        risk_free_rate: 无风险利率
        """
        self.price_df = price_df
        self.risk_free_rate = risk_free_rate
        self.returns = self.price_df.pct_change().dropna()
        self.mean_returns = self.returns.mean()
        self.cov_matrix = self.returns.cov()
        self.asset_names = self.price_df.columns.tolist()

    def simulate_portfolios(self, num_portfolios=5000):
        results = []
        for _ in range(num_portfolios):
            weights = np.random.random(len(self.asset_names))
            weights /= np.sum(weights)
            port_return = np.dot(weights, self.mean_returns) * 252  # 年化
            port_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix * 252, weights)))
            sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
            results.append({
                'return': port_return,
                'volatility': port_vol,
                'sharpe': sharpe,
                'weights': weights
            })
        self.portfolios = pd.DataFrame(results)
        return self.portfolios

    def get_efficient_frontier(self):
        if not hasattr(self, 'portfolios'):
            raise ValueError('请先运行simulate_portfolios')
        df = self.portfolios.copy()
        df['vol_bin'] = pd.cut(df['volatility'], bins=100)
        frontier = df.loc[df.groupby('vol_bin', observed=True)['return'].idxmax()]
        return frontier.sort_values('volatility')

    def get_max_sharpe_portfolio(self):
        if not hasattr(self, 'portfolios'):
            raise ValueError('请先运行simulate_portfolios')
        idx = self.portfolios['sharpe'].idxmax()
        return self.portfolios.loc[idx]

    def get_min_vol_portfolio(self):
        if not hasattr(self, 'portfolios'):
            raise ValueError('请先运行simulate_portfolios')
        idx = self.portfolios['volatility'].idxmin()
        return self.portfolios.loc[idx]

    def get_equal_weight_portfolio(self):
        weights = np.ones(len(self.asset_names)) / len(self.asset_names)
        port_return = np.dot(weights, self.mean_returns) * 252
        port_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix * 252, weights)))
        sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
        return {
            'return': port_return,
            'volatility': port_vol,
            'sharpe': sharpe,
            'weights': weights
        }

    def get_max_return_portfolio(self):
        if not hasattr(self, 'portfolios'):
            raise ValueError('请先运行simulate_portfolios')
        idx = self.portfolios['return'].idxmax()
        return self.portfolios.loc[idx]

    def get_target_return_portfolio(self, target_return):
        # 给定目标收益下最小风险组合
        from scipy.optimize import minimize
        n = len(self.asset_names)
        args = (self.mean_returns * 252, self.cov_matrix * 252)
        def portfolio_volatility(weights, mean_returns, cov_matrix):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                       {'type': 'eq', 'fun': lambda x: np.dot(x, args[0]) - target_return})
        bounds = tuple((0, 1) for _ in range(n))
        result = minimize(portfolio_volatility, n*[1./n,], args=args, method='SLSQP', bounds=bounds, constraints=constraints)
        if not result.success:
            raise ValueError('优化失败，无法找到目标收益下的最小风险组合')
        weights = result.x
        port_return = np.dot(weights, self.mean_returns) * 252
        port_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix * 252, weights)))
        sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
        return {
            'return': port_return,
            'volatility': port_vol,
            'sharpe': sharpe,
            'weights': weights
        }

    def get_target_risk_portfolio(self, target_risk):
        # 给定目标风险下最大收益组合
        from scipy.optimize import minimize
        n = len(self.asset_names)
        args = (self.mean_returns * 252, self.cov_matrix * 252)
        def neg_return(weights, mean_returns, cov_matrix):
            return -np.dot(weights, mean_returns)
        def portfolio_volatility(weights, mean_returns, cov_matrix):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                       {'type': 'eq', 'fun': lambda x: portfolio_volatility(x, *args) - target_risk})
        bounds = tuple((0, 1) for _ in range(n))
        result = minimize(neg_return, n*[1./n,], args=args, method='SLSQP', bounds=bounds, constraints=constraints)
        if not result.success:
            raise ValueError('优化失败，无法找到目标风险下的最大收益组合')
        weights = result.x
        port_return = np.dot(weights, self.mean_returns) * 252
        port_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix * 252, weights)))
        sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
        return {
            'return': port_return,
            'volatility': port_vol,
            'sharpe': sharpe,
            'weights': weights
        }

    def visualize_frontier(self, save_path=None, show=True):
        if not hasattr(self, 'portfolios'):
            raise ValueError('请先运行simulate_portfolios')
        frontier = self.get_efficient_frontier()
        max_sharpe = self.get_max_sharpe_portfolio()
        min_vol = self.get_min_vol_portfolio()
        plt.figure(figsize=(10, 7))
        plt.scatter(self.portfolios['volatility'], self.portfolios['return'], c=self.portfolios['sharpe'], cmap='viridis', alpha=0.4, label='Portfolios')
        plt.plot(frontier['volatility'], frontier['return'], color='red', linewidth=2, label='Efficient Frontier')
        plt.scatter(max_sharpe['volatility'], max_sharpe['return'], marker='*', color='orange', s=200, label='Max Sharpe')
        plt.scatter(min_vol['volatility'], min_vol['return'], marker='X', color='blue', s=150, label='Min Volatility')
        plt.xlabel('Volatility (Risk)')
        plt.ylabel('Expected Return')
        plt.title('Efficient Frontier')
        plt.colorbar(label='Sharpe Ratio')
        plt.legend()
        plt.grid(True)
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()

    def plot_frontier(self, ax):
        if not hasattr(self, 'portfolios'):
            raise ValueError('请先运行simulate_portfolios')
        frontier = self.get_efficient_frontier()
        max_sharpe = self.get_max_sharpe_portfolio()
        min_vol = self.get_min_vol_portfolio()
        sc = ax.scatter(self.portfolios['volatility'], self.portfolios['return'], c=self.portfolios['sharpe'], cmap='viridis', alpha=0.4, label='Portfolios')
        ax.plot(frontier['volatility'], frontier['return'], color='red', linewidth=2, label='Efficient Frontier')
        ax.scatter(max_sharpe['volatility'], max_sharpe['return'], marker='*', color='orange', s=200, label='Max Sharpe')
        ax.scatter(min_vol['volatility'], min_vol['return'], marker='X', color='blue', s=150, label='Min Volatility')
        ax.set_xlabel('Volatility (Risk)')
        ax.set_ylabel('Expected Return')
        ax.set_title('Efficient Frontier')
        plt.colorbar(sc, ax=ax, label='Sharpe Ratio')
        ax.legend()
        ax.grid(True)

    def plotly_frontier_figure(self):
        if not hasattr(self, 'portfolios'):
            raise ValueError('请先运行simulate_portfolios')
        frontier = self.get_efficient_frontier()
        max_sharpe = self.get_max_sharpe_portfolio()
        min_vol = self.get_min_vol_portfolio()
        max_return = self.get_max_return_portfolio()
        scatter = go.Scatter(
            x=self.portfolios['volatility'],
            y=self.portfolios['return'],
            mode='markers',
            marker=dict(
                color=self.portfolios['sharpe'],
                colorscale='Viridis',
                colorbar=dict(title='夏普比率'),
                size=6,
                opacity=0.5
            ),
            text=[
                '<br>'.join([
                    f'权重: {w:.2%}' for w in weights
                ]) for weights in self.portfolios['weights']
            ],
            hovertemplate=(
                '风险: %{x:.2%}<br>收益: %{y:.2%}<br>夏普: %{marker.color:.2f}<br>%{text}'
            ),
            name='投资组合'
        )
        frontier_line = go.Scatter(
            x=frontier['volatility'],
            y=frontier['return'],
            mode='lines',
            line=dict(color='red', width=2),
            name='有效前沿'
        )
        max_sharpe_point = go.Scatter(
            x=[max_sharpe['volatility']],
            y=[max_sharpe['return']],
            mode='markers',
            marker=dict(color='orange', size=16, symbol='star'),
            name='最大夏普比率'
        )
        min_vol_point = go.Scatter(
            x=[min_vol['volatility']],
            y=[min_vol['return']],
            mode='markers',
            marker=dict(color='blue', size=14, symbol='x'),
            name='最小方差'
        )
        max_return_point = go.Scatter(
            x=[max_return['volatility']],
            y=[max_return['return']],
            mode='markers',
            marker=dict(color='purple', size=16, symbol='diamond'),
            name='最大收益'
        )
        layout = go.Layout(
            title='有效前沿图',
            xaxis=dict(title='波动率 (风险)'),
            yaxis=dict(title='预期收益率'),
            hovermode='closest'
        )
        fig = go.Figure(data=[scatter, frontier_line, max_sharpe_point, min_vol_point, max_return_point], layout=layout)
        return fig 