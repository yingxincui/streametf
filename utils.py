import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
from scipy.optimize import newton
import os
import json

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 禁用警告
warnings.filterwarnings("ignore")

# 清理ETF代码，去掉市场前缀
def clean_etf_symbol(symbol):
    return re.sub(r'^(sh|sz|bj)?(\d+)$', r'\2', str(symbol).lower())

# 计算XIRR（内部收益率）
def calculate_xirr(cashflows):
    try:
        # 将现金流转换为日期和金额的列表
        dates = [cf[0] for cf in cashflows]
        amounts = [cf[1] for cf in cashflows]
        
        # 转换为相对于第一天的天数
        days = [(date - dates[0]).days for date in dates]
        
        # 定义计算净现值的函数
        def net_present_value(rate):
            return sum([amt / (1 + rate)**(day/365) for amt, day in zip(amounts, days)])
        
        # 使用牛顿法求解
        xirr = newton(net_present_value, x0=0.1)
        return xirr
    except Exception as e:
        print(f"⚠️ 计算XIRR失败: {str(e)}")
        return np.nan

# 计算年度收益率
def calculate_annual_returns(portfolio_value):
    annual_returns = portfolio_value.resample('Y').last().pct_change().dropna()
    annual_returns.index = annual_returns.index.year
    return annual_returns * 100  # 转换为百分比

def get_favorite_etfs():
    """
    获取用户配置的自选ETF列表
    返回:
    list: 自选ETF代码字符串列表，如果文件不存在或读取失败则返回空列表
    """
    config_dir = "config"
    favorite_etfs_file = os.path.join(config_dir, "favorite_etfs.json")
    if os.path.exists(favorite_etfs_file):
        try:
            with open(favorite_etfs_file, 'r', encoding='utf-8') as f:
                return [str(code) for code in json.load(f)]
        except:
            return []
    return []

def get_etf_options_with_favorites(etf_list):
    """
    获取ETF选项列表，自选ETF优先显示
    
    参数:
    etf_list: DataFrame, 包含所有ETF的列表
    
    返回:
    list: 按优先级排序的ETF代码列表
    """
    favorite_etfs = get_favorite_etfs()
    
    if not favorite_etfs:
        return etf_list['symbol'].unique().tolist()
    
    # 分离自选ETF和其他ETF
    favorite_codes = []
    other_codes = []
    
    for symbol in etf_list['symbol'].unique():
        # 确保类型一致进行比较
        symbol_str = str(symbol)
        if symbol_str in favorite_etfs:
            favorite_codes.append(symbol)
        else:
            other_codes.append(symbol)
    
    # 自选ETF在前，其他ETF在后
    return favorite_codes + other_codes