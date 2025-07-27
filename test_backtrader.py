import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 创建测试数据
dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
prices = np.random.randn(len(dates)).cumsum() + 100

df = pd.DataFrame({
    'open': prices,
    'high': prices + np.random.rand(len(dates)),
    'low': prices - np.random.rand(len(dates)),
    'close': prices,
    'volume': np.ones(len(dates)) * 1000000
}, index=dates)

class PandasData_BT(bt.feeds.PandasData):
    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),
    )

class TestStrategy(bt.Strategy):
    def __init__(self):
        pass
    
    def next(self):
        if not self.position:
            self.buy()

cerebro = bt.Cerebro()
cerebro.broker.setcash(10000.0)

datafeed = PandasData_BT(dataname=df)
cerebro.adddata(datafeed, name="TEST")

cerebro.addstrategy(TestStrategy)
result = cerebro.run()
print("Backtrader test completed successfully!")