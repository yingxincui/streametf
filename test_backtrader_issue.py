import backtrader as bt
import pandas as pd
import numpy as np

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
        self.counter = 0
    
    def next(self):
        self.counter += 1
        if self.counter == 1:
            print(f"Date: {self.datas[0].datetime.date(0)}")
            print(f"Close: {self.datas[0].close[0]}")

def test_backtrader():
    # 创建测试数据
    dates = pd.date_range('2020-01-01', periods=10, freq='D')
    data = pd.DataFrame({
        'open': [100] * 10,
        'high': [100] * 10,
        'low': [100] * 10,
        'close': [100] * 10,
        'volume': [1000] * 10
    }, index=dates)
    
    # 创建cerebro引擎
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000.0)
    
    # 添加数据
    datafeed = PandasData_BT(dataname=data)
    cerebro.adddata(datafeed)
    
    # 添加策略
    cerebro.addstrategy(TestStrategy)
    
    # 运行回测
    print("Running backtrader test...")
    result = cerebro.run()
    print("Backtrader test completed successfully!")

if __name__ == "__main__":
    test_backtrader()