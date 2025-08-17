import streamlit as st
from data import get_etf_list

# 设置页面配置
st.set_page_config(
    page_title="ETF回测与分析工具",
    page_icon="📊",
    layout="wide"
)

# 创建漂亮的宣传区域
st.markdown("""
<div style="
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
    border-radius: 20px;
    text-align: center;
    color: white;
    margin: 1rem 0;
">
    <h1 style="font-size: 3rem; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
        📊 ETF回测与分析工具
    </h1>
    <p style="font-size: 1.5rem; margin: 1rem 0; opacity: 0.9;">
        专业级投资分析平台 · 动态交互式图表 · AI智能策略建议
    </p>
</div>
""", unsafe_allow_html=True)

# 功能特色展示
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background: #f0f2f6; border-radius: 15px; margin: 0.5rem 0;">
        <div style="font-size: 2.5rem;">🚀</div>
        <div style="font-weight: bold; color: #333;">组合回测</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background: #f0f2f6; border-radius: 15px; margin: 0.5rem 0;">
        <div style="font-size: 2.5rem;">📈</div>
        <div style="font-weight: bold; color: #333;">动量策略</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background: #f0f2f6; border-radius: 15px; margin: 0.5rem 0;">
        <div style="font-size: 2.5rem;">🎯</div>
        <div style="font-weight: bold; color: #333;">有效前沿</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div style="text-align: center; padding: 1rem; background: #f0f2f6; border-radius: 15px; margin: 0.5rem 0;">
        <div style="font-size: 2.5rem;">🤖</div>
        <div style="font-weight: bold; color: #333;">AI策略</div>
    </div>
    """, unsafe_allow_html=True)

# 统计数据
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("功能模块", "27+", "持续更新")

with col2:
    st.metric("图表类型", "动态交互", "Plotly驱动")

with col3:
    st.metric("数据源", "实时更新", "akshare")

with col4:
    st.metric("用户体验", "专业级", "响应式设计")

# 图表展示说明
st.markdown("---")
st.markdown("## 🎨 丰富的图表展示")
st.markdown("所有图表均采用Plotly动态交互式设计，支持缩放、悬停、图例交互等专业功能")

# 创建两行图表展示
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 15px; margin: 0.5rem 0;">
        <h3 style="color: #333; margin-bottom: 1rem;">📈 趋势分析图</h3>
        <p style="color: #666; margin: 0;">支持多ETF对比，动态缩放，悬停显示详细数据，专业级投资分析体验</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 15px; margin: 0.5rem 0;">
        <h3 style="color: #333; margin-bottom: 1rem;">📊 相关性热力图</h3>
        <p style="color: #666; margin: 0;">ETF间相关性分析，颜色深浅直观显示，支持交互式探索</p>
    </div>
    """, unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 15px; margin: 0.5rem 0;">
        <h3 style="color: #333; margin-bottom: 1rem;">🎯 有效前沿图</h3>
        <p style="color: #666; margin: 0;">风险收益优化分析，蒙特卡洛模拟，寻找最优投资组合</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 15px; margin: 0.5rem 0;">
        <h3 style="color: #333; margin-bottom: 1rem;">📉 回撤分析图</h3>
        <p style="color: #666; margin: 0;">最大回撤分析，风险指标可视化，支持多维度对比</p>
    </div>
    """, unsafe_allow_html=True)

# 可选：添加logo（如有logo.png放在项目根目录）
# st.image("logo.png", width=120)

st.title("📊 ETF回测与分析工具")

# 添加刷新ETF缓存列表按钮
if st.button("🔄 刷新ETF缓存列表"):
    with st.spinner("正在刷新ETF列表缓存..."):
        get_etf_list(force_refresh=True)
    st.success("ETF列表缓存已刷新！")

st.markdown("""
---

## 🚀 功能导航

### 📊 基础回测与分析

1. **组合回测**  
   多ETF自定义权重历史回测，支持保存/加载组合和年度再平衡。

2. **定投回测**  
   ETF定投策略模拟，支持权重分配与定投日设置。

3. **有效前沿分析**  
   蒙特卡洛模拟，寻找最优风险收益组合，支持保存/加载分析参数。

4. **动量策略**  
   多ETF动量轮动策略，支持参数自定义和历史回测，包含趋势图、因子分析、BIAS超买超卖分析。

5. **轮动回测**  
   多ETF动量轮动策略，支持参数自定义和历史回测。

6. **价值平均定投回测**  
   支持目标市值递推/自定义，自动对比普通定投。

### 🏆 经典策略与对比

7. **永久组合回测**  
   经典永久组合策略回测，包含黄金、股票、债券、现金四大类资产。

8. **永久组合对比**  
   多种永久组合版本收益、回撤、波动等指标对比。

### 📈 行业与指数分析

9. **指定ETF月均涨跌幅分析**  
   分析指定ETF近3/5/10年各月平均涨跌幅，挖掘季节性规律。

10. **ETF近20日涨幅排行**  
    场内基金近一月涨幅前50/后50排行，快速筛选强弱势基金。

11. **二月策略分析**  
    分析二月效应，验证"二月不买"等市场谚语的有效性。

### 🔍 基金筛选与监控

12. **场内基金筛选**  
    按年化收益率、成立年限等条件筛选场内基金。

13. **红利基金筛选**  
    场内红利基金筛选，支持年化收益率、成立年限等条件。

14. **开放式基金分析（含排行筛选）**  
    开放式基金实时数据分析，包含净值走势、业绩对比、风险分析、排行榜筛选等多维度可视化。

16. **基金溢价监控**  
    QDII/LOF/ETF等基金T-1日溢价率监控，支持阈值筛选。

### 📅 时间周期分析

17. **周度涨跌分析**  
    分析每月各周的涨跌规律，识别最容易上涨和下跌的周次，支持动态图表。

18. **月度胜率分析**  
    分析ETF各月份的胜率和平均收益，挖掘月度投资规律，支持动态图表。

19. **月末测量回测**  
    月末效应分析，验证月末投资策略的有效性。

### 🎯 技术指标与策略

20. **常见技术指标回测**  
    移动平均线、RSI、MACD等技术指标回测分析。

21. **网格策略回测**  
    网格交易策略回测，支持参数自定义和收益分析。

22. **指数相对涨幅分析**  
    分析主要指数相对涨幅，识别市场强弱变化。

### 🌍 海外与主题投资

23. **标准普尔配置**  
    标普500指数相关ETF配置策略分析。

24. **市场风格分析**  
    分析市场风格轮动，识别成长/价值风格切换。

25. **AI智能策略建议**  
    基于AI分析的ETF投资策略建议，优先推荐自选ETF。

### 💡 理念与工具

26. **投资大师理念**  
    纳瓦尔、芒格、巴菲特等投资理念与经典语录。

27. **财富自由计算器**  
    4%法则财富自由目标测算，支持储蓄率、收益率等参数。

28. **AI助手与API密钥配置**  
    配置AI助手功能和相关API密钥。

---

## 🆕 最新更新

### ✨ 新增功能
- **动态图表**：所有图表已升级为Plotly交互式图表，支持缩放、悬停、图例交互
- **BIAS分析**：动量策略页面新增超买超卖分析，支持动态阈值计算
- **因子分析**：动量策略页面新增相关性分析和风险指标对比
- **趋势图表**：动量策略页面新增近一年走势趋势图和等权配置收益曲线
- **周度分析**：新增周度涨跌分析页面，分析每月各周投资规律
- **月度分析**：月度胜率分析页面升级为动态图表

### 🎨 界面优化
- **颜色规范**：统一使用红色表示上涨，绿色表示下跌（符合中国股市习惯）
- **图表布局**：优化图表高度、图例位置、悬停提示等细节
- **响应式设计**：支持不同屏幕尺寸，图表自适应容器宽度

### 🔧 技术改进
- **缓存优化**：智能缓存机制，提高数据获取效率
- **错误处理**：完善的错误处理和用户提示
- **数据验证**：增强的数据验证和边界检查

---

> 💡 **建议**：请通过左侧导航栏选择功能页面，每个页面均可自定义参数，点击按钮运行分析。
> 
> 支持保存/加载自定义组合，便于多次复用。支持导出PDF报告，便于分享和归档。
> 
> 🎯 **推荐页面**：动量策略、周度涨跌分析、月度胜率分析、ETF对比分析等页面功能丰富，值得优先体验！
""")