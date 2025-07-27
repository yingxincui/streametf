import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
from data import fetch_etf_data_with_retry
from utils import calculate_xirr

# 计算定投收益
def calculate_dca(etfs, weights, start_date, end_date, monthly_amount, invest_day, etf_list):
    data = pd.DataFrame()
    unavailable_etfs = []
    etf_names = {}
    
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    st.write(f"\n⏳ 定投日期范围：{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    for etf in etfs:
        # 使用支持缓存的fetch_etf_data_with_retry函数
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
    
    if data.empty:
        st.error("❌ 无法获取任何ETF数据")
        return None, None, None, None, None
    
    data.fillna(method='ffill', inplace=True)
    
    # 生成定投日期序列
    invest_dates = []
    current_date = start_date
    
    while current_date <= end_date:
        # 处理每月定投日
        try:
            # 尝试使用指定的定投日
            invest_date = current_date.replace(day=invest_day)
        except ValueError:
            # 如果指定的定投日超出当月天数，使用当月最后一天
            if current_date.month == 12:
                next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                next_month = current_date.replace(month=current_date.month + 1, day=1)
            invest_date = next_month - timedelta(days=1)
        
        if start_date <= invest_date <= end_date:
            invest_dates.append(invest_date)
        
        # 移动到下个月
        try:
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        except ValueError:
            # 如果当前日期是月末（如1月31日），移动到下个月时可能产生无效日期
            # 使用下个月第一天，然后减去一天来获取当前月的最后一天
            if current_date.month == 12:
                next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                next_month = current_date.replace(month=current_date.month + 1, day=1)
            current_date = next_month - timedelta(days=1)
    
    # 初始化定投记录
    dca_records = []
    total_invested = 0
    total_units = {etf: 0 for etf in data.columns}
    cashflows = []
    
    for date in invest_dates:
        if date > end_date or date < start_date:
            continue
            
        # 找到最近的交易日
        valid_dates = data.index[data.index <= date]
        if len(valid_dates) == 0:
            continue
        valid_date = valid_dates[-1]
        
        # 获取当天的ETF价格
        prices = data.loc[valid_date]
        
        # 计算每个ETF的定投金额
        # 解决类型不匹配问题：etf.split('_')[0]返回字符串，而etfs列表中是numpy.int64
        etf_amounts = []
        for etf in data.columns:
            etf_code = etf.split('_')[0]
            # 查找匹配的ETF权重
            weight = 0
            for i, selected_etf in enumerate(etfs):
                if str(selected_etf) == str(etf_code):
                    weight = weights[i]
                    break
            etf_amounts.append(weight)
        etf_amounts = np.array(etf_amounts)
        # 避免除零错误
        if etf_amounts.sum() > 0:
            etf_amounts = etf_amounts / etf_amounts.sum() * monthly_amount
        else:
            etf_amounts = np.array([monthly_amount / len(data.columns)] * len(data.columns))
        
        # 计算购买的份额
        for i, etf in enumerate(data.columns):
            price = prices[i]
            if pd.notna(price) and price > 0:
                units = etf_amounts[i] / price
                total_units[etf] += units
        
        total_invested += monthly_amount
        cashflows.append((valid_date, -monthly_amount))  # 投入为负
        
        # 计算当前投资组合价值
        current_value = sum(total_units[etf] * data[etf].iloc[-1] for etf in data.columns)
        
        # 记录定投信息
        dca_records.append({
            '日期': valid_date,
            '累计投入': total_invested,
            '当前价值': current_value,
            '简单收益率 (%)': (current_value / total_invested - 1) * 100 if total_invested > 0 else 0
        })
    
    if not dca_records:
        st.error("❌ 没有有效的定投记录")
        return None, None, None, None, None
    
    # 添加最终价值作为正现金流
    final_date = data.index[-1]
    final_value = sum(total_units[etf] * data[etf].iloc[-1] for etf in data.columns)
    cashflows.append((final_date, final_value))
    
    # 计算XIRR（年化收益率）
    xirr = calculate_xirr(cashflows)
    annualized_return = xirr * 100 if not np.isnan(xirr) else 0
    
    dca_df = pd.DataFrame(dca_records).set_index('日期')
    portfolio_value = dca_df['当前价值']
    total_invested = dca_df['累计投入']
    simple_returns = dca_df['简单收益率 (%)']
    
    return portfolio_value, total_invested, simple_returns, data, annualized_return