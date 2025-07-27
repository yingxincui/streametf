import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from data import get_etf_list, fetch_etf_data_with_retry

# 标准普尔配置页面
def sp500_portfolio_page():
    st.title("🎯 标准普尔配置")
    
    # 添加概念讲解
    with st.expander("🔍 什么是标准普尔家庭资产配置图？", expanded=True):
        st.markdown("""
        **标准普尔家庭资产配置图**是标准普尔公司通过调研全球10万个资产稳健增长的家庭，分析总结出的一套成熟、科学的家庭资产配置方式。
        
        标准普尔家庭资产配置图把家庭资产分成四个账户，这四个账户作用不同，投资工具也各不相同，只有拥有这四个账户，并且按照固定比例进行分配，才能保证家庭资产长期、持续、稳健的增长。
        
        ### 📊 四个账户详解
        
        **💰 要花的钱（10%）**
        - 作用：短期消费，3-6个月的生活费
        - 保障：用于日常开销、旅游、娱乐等
        - 投资工具：活期理财、货币基金等
        - 特点：随时可以支取，不会贬值
        
        **🛡️ 保命的钱（20%）**
        - 作用：保障突发的大额开销
        - 保障：解决重大疾病、意外伤害等风险
        - 投资工具：重疾险、医疗险、意外险等
        - 特点：专款专用，解决家庭突发的大开支
        
        **📈 保本升值的钱（30%）**
        - 作用：保障家庭资产稳健增长
        - 保障：养老金、子女教育金等
        - 投资工具：债券、信托、理财险等
        - 特点：本金安全、收益稳定
        
        **🚀 生钱的钱（40%）**
        - 作用：创造高收益
        - 保障：用于投资增值
        - 投资工具：股票、房产、基金等
        - 特点：高收益、高风险
        
        ### 🎯 配置原则
        - 按照10%、20%、30%、40%的比例分配
        - 根据家庭实际情况灵活调整
        - 定期评估和再平衡
        """)
    
    # 四账户配置建议
    st.header("💡 四账户配置建议")
    
    # 要花的钱
    st.subheader("💰 要花的钱 (10%)")
    st.markdown("""
    - **投资工具**：货币基金、银行活期理财
    - **推荐ETF**：
      - 511090.SH (浦银安盛日日盈ETF) - 货币型ETF
      - 511380.SH (华宝添益) - 货币型ETF
    - **特点**：流动性好，风险极低，收益稳定
    """)
    
    # 保命的钱
    st.subheader("🛡️ 保命的钱 (20%)")
    st.markdown("""
    - **投资工具**：保险产品（不在ETF范围内）
    - **建议**：购买重疾险、医疗险、意外险等
    - **特点**：专款专用，保障突发大额支出
    """)
    
    # 保本升值的钱
    st.subheader("📈 保本升值的钱 (30%)")
    st.markdown("""
    - **投资工具**：债券ETF、国债ETF
    - **推荐ETF**：
      - 511010.SH (国债ETF) - 国债ETF
      - 511220.SH (城投债ETF) - 债券ETF
    - **特点**：本金安全，收益稳定
    """)
    
    # 生钱的钱
    st.subheader("🚀 生钱的钱 (40%)")
    st.markdown("""
    - **投资工具**：股票ETF、宽基指数ETF
    - **推荐ETF**：
      - 510300.SH (沪深300ETF) - 大盘股ETF
      - 510500.SH (中证500ETF) - 中盘股ETF
      - 510310.SH (上证50ETF) - 大盘股ETF
      - 512890.SH (银行ETF) - 行业ETF
      - 512010.SH (医药ETF) - 行业ETF
    - **特点**：高风险高收益，长期增值潜力大
    """)
    
    # 资金分配计算器
    st.header("🧮 资金分配计算器")
    st.markdown("""
    根据标准普尔家庭资产配置图，您可以输入总资金，系统将自动为您计算各账户的分配金额。
    """)
    
    # 用户输入总资金
    total_fund = st.number_input("请输入您的总资金 (元)", min_value=0.0, value=100000.0, step=1000.0, format="%.2f")
    
    if total_fund > 0:
        # 计算各账户分配金额
        spend_fund = total_fund * 0.10
        insurance_fund = total_fund * 0.20
        stable_fund = total_fund * 0.30
        investment_fund = total_fund * 0.40
        
        # 显示分配结果
        st.subheader("📊 资金分配结果")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(label="💰 要花的钱 (10%)", value=f"¥{spend_fund:,.2f}")
        with col2:
            st.metric(label="🛡️ 保命的钱 (20%)", value=f"¥{insurance_fund:,.2f}")
        with col3:
            st.metric(label="📈 保本升值的钱 (30%)", value=f"¥{stable_fund:,.2f}")
        with col4:
            st.metric(label="🚀 生钱的钱 (40%)", value=f"¥{investment_fund:,.2f}")
        
        # 显示推荐ETF投资分配
        st.subheader("📈 推荐ETF投资分配")
        st.markdown("""
        根据各账户特点，为您推荐以下ETF投资方案：
        """)
        
        # 要花的钱ETF分配
        st.markdown("**💰 要花的钱 (10%)**")
        st.write(f"- 511090.SH (浦银安盛日日盈ETF): ¥{spend_fund * 0.5:,.2f}")
        st.write(f"- 511380.SH (华宝添益): ¥{spend_fund * 0.5:,.2f}")
        
        # 保本升值的钱ETF分配
        st.markdown("**📈 保本升值的钱 (30%)**")
        st.write(f"- 511010.SH (国债ETF): ¥{stable_fund * 0.6:,.2f}")
        st.write(f"- 511220.SH (城投债ETF): ¥{stable_fund * 0.4:,.2f}")
        
        # 生钱的钱ETF分配
        st.markdown("**🚀 生钱的钱 (40%)**")
        st.write(f"- 510300.SH (沪深300ETF): ¥{investment_fund * 0.3:,.2f}")
        st.write(f"- 510500.SH (中证500ETF): ¥{investment_fund * 0.25:,.2f}")
        st.write(f"- 510310.SH (上证50ETF): ¥{investment_fund * 0.2:,.2f}")
        st.write(f"- 512890.SH (银行ETF): ¥{investment_fund * 0.15:,.2f}")
        st.write(f"- 512010.SH (医药ETF): ¥{investment_fund * 0.1:,.2f}")
        
        # 总结
        st.info(f"💡 您的总资金 ¥{total_fund:,.2f} 已按标准普尔配置图完成分配建议。投资有风险，入市需谨慎！")
    else:
        st.info("请输入您的总资金以查看分配建议")
    
    # 配置优化建议
    st.header("🎯 配置优化建议")
    st.markdown("""
    ### 📋 实施步骤
    1. **评估现状**：盘点现有资产，确定各账户资金缺口
    2. **分步配置**：按比例逐步配置各账户
    3. **定期调整**：每年或每半年评估一次，进行再平衡
    4. **动态优化**：根据市场变化和个人情况调整配置
    
    ### ⚠️ 注意事项
    - 配置比例可根据个人风险承受能力适当调整
    - 投资有风险，入市需谨慎
    - 建议咨询专业理财顾问
    """)
    
    # 历史表现
    st.header("📈 历史表现")
    st.info("正在开发中，敬请期待历史表现分析功能...")

# 页面入口
if __name__ == "__main__":
    sp500_portfolio_page()