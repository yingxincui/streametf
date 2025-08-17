import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import akshare as ak
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="申万指数分析月报表", page_icon="📊", layout="wide")
st.title("📊 申万指数分析月报表")

# 使用expander折叠说明部分
with st.expander("📖 功能说明与使用指南", expanded=False):
    st.markdown("""
    > 基于申万宏源研究的指数分析月报表，深入分析市场表征、一级行业、二级行业和风格指数的表现。
    > 提供多维度数据可视化和统计分析，帮助投资者了解市场结构和行业轮动规律。

    **🎯 核心功能：**
    - **多维度分析**：市场表征、一级行业、二级行业、风格指数
    - **月度数据**：获取申万指数月度分析报表
    - **可视化图表**：涨跌幅分布、估值分析、成交分析等
    - **对比分析**：不同指数类别间的表现对比
    - **数据导出**：支持CSV和Excel格式下载

    **📊 分析维度：**
    - **涨跌幅分析**：指数涨跌分布和排名
    - **估值分析**：市盈率、市净率、股息率分析
    - **成交分析**：成交量、换手率、成交额占比
    - **市值分析**：流通市值和平均流通市值
    - **行业轮动**：不同行业指数的相对表现

    **🎨 颜色规则：**
    - **涨（正值）**：红色 🔴
    - **跌（负值）**：绿色 🟢
    （符合中国股市习惯）

    **📈 指数类别说明：**
    - **市场表征**：代表整体市场走势的指数
    - **一级行业**：申万一级行业分类指数
    - **二级行业**：申万二级行业分类指数
    - **风格指数**：不同投资风格的指数
    """)

# 获取可用的月度日期
@st.cache_data(ttl=3600)  # 缓存1小时
def get_monthly_dates():
    """获取可用的月度日期列表"""
    try:
        # 获取月度数据
        monthly_data = ak.index_analysis_week_month_sw(symbol="month")
        if not monthly_data.empty:
            # 提取日期列并去重排序（列名是'date'）
            dates = monthly_data['date'].unique()
            # 创建日期选项：显示友好格式，存储API格式
            date_options = []
            for date in dates:
                friendly_format = date.strftime('%Y年%m月%d日')
                api_format = date.strftime('%Y%m%d')
                date_options.append((friendly_format, api_format))
            
            # 按日期倒序排列
            date_options = sorted(date_options, key=lambda x: x[1], reverse=True)
            return date_options
        else:
            return []
    except Exception as e:
        st.error(f"获取月度日期失败: {str(e)}")
        return []

# 获取申万指数月度分析数据
@st.cache_data(ttl=3600)  # 缓存1小时
def get_sw_monthly_data(symbol, date):
    """获取申万指数月度分析数据"""
    try:
        data = ak.index_analysis_monthly_sw(symbol=symbol, date=date)
        if not data.empty:
            # 清理数据
            data = data.copy()
            # 转换数值列
            numeric_columns = ['收盘指数', '成交量', '涨跌幅', '换手率', '市盈率', '市净率', 
                             '均价', '成交额占比', '流通市值', '平均流通市值', '股息率']
            for col in numeric_columns:
                if col in data.columns:
                    data[col] = pd.to_numeric(data[col], errors='coerce')
            return data
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"获取{symbol}数据失败: {str(e)}")
        return pd.DataFrame()

# 获取可用日期
available_dates = get_monthly_dates()

if not available_dates:
    st.error("无法获取可用的月度日期，请检查网络连接")
    st.stop()

# 页面控制
st.subheader("🔍 分析参数设置")

col1, col2 = st.columns(2)

with col1:
    # 指数类别选择
    symbol_options = {
        "市场表征": "市场表征",
        "一级行业": "一级行业", 
        "二级行业": "二级行业",
        "风格指数": "风格指数"
    }
    
    selected_symbol = st.selectbox(
        "选择指数类别",
        options=list(symbol_options.keys()),
        index=0,
        help="选择要分析的指数类别"
    )

with col2:
    # 日期选择
    if available_dates:
        # 默认选择最新日期
        default_date_index = 0
        selected_date_friendly, selected_date_api = available_dates[default_date_index]
        selected_date = st.selectbox(
            "选择分析日期",
            options=[item[0] for item in available_dates],
            index=default_date_index,
            help="选择要分析的月度日期"
        )
    else:
        st.error("没有可用的日期数据")
        st.stop()

# 运行分析按钮
run_btn = st.button("🚀 运行申万指数分析")

if run_btn:
    st.subheader("📊 申万指数分析结果")
    
    # 获取数据
    with st.spinner(f"正在获取{selected_symbol}数据..."):
        data = get_sw_monthly_data(symbol_options[selected_symbol], selected_date_api)
    
    if data.empty:
        st.error(f"未获取到{selected_symbol}的数据，请检查参数设置")
        st.stop()
    
    # 数据预处理
    data = data.copy()
    
    # 显示数据概览
    st.subheader("📋 数据概览")
    st.info(f"**分析类别：** {selected_symbol} | **分析日期：** {selected_date_friendly} | **数据条数：** {len(data)}")
    
    # 可视化分析 - 涨跌幅图放在最前面
    st.subheader("📈 涨跌幅分析")
    
    if not data.empty:
        # 涨跌幅全排名（全宽显示）
        if '涨跌幅' in data.columns:
            # 按涨跌幅排序（从高到低）
            sorted_data = data.sort_values('涨跌幅', ascending=False)[['指数名称', '涨跌幅']]
            
            # 创建全排名图
            fig_ranking = go.Figure()
            
            # 根据涨跌设置渐变颜色
            colors = []
            for x in sorted_data['涨跌幅']:
                if pd.isna(x) or x == 0:
                    # 处理NaN或0值，使用灰色
                    colors.append('#808080')
                elif x > 0:
                    # 红色渐变：从浅红到深红
                    intensity = min(abs(x) / 20, 1.0)  # 根据涨跌幅强度调整颜色
                    intensity = max(0.3, intensity)  # 确保最小值
                    colors.append(f'rgba(220, 53, 69, {intensity})')
                else:
                    # 绿色渐变：从浅绿到深绿
                    intensity = min(abs(x) / 20, 1.0)  # 根据涨跌幅强度调整颜色
                    intensity = max(0.3, intensity)  # 确保最小值
                    colors.append(f'rgba(40, 167, 69, {intensity})')
            
            fig_ranking.add_trace(go.Bar(
                y=sorted_data['指数名称'],
                x=sorted_data['涨跌幅'],
                marker_color=colors,
                orientation='h',
                hovertemplate='<b>%{y}</b><br>涨跌幅: %{x:.2f}%<extra></extra>',
                text=[f'{x:.2f}%' for x in sorted_data['涨跌幅']],
                textposition='auto'
            ))
            
            fig_ranking.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
            
            fig_ranking.update_layout(
                title=f'{selected_symbol}涨跌幅全排名',
                yaxis_title='指数名称',
                xaxis_title='涨跌幅 (%)',
                height=max(600, len(sorted_data) * 20),  # 根据数据量动态调整高度
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig_ranking, use_container_width=True)
    
    # 快速统计
    st.subheader("📊 快速统计")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # 涨跌幅统计
        if '涨跌幅' in data.columns:
            positive_count = sum(1 for x in data['涨跌幅'] if x > 0)
            negative_count = sum(1 for x in data['涨跌幅'] if x < 0)
            avg_change = data['涨跌幅'].mean()
            
            st.metric(
                "平均涨跌幅", 
                f"{avg_change:.2f}%",
                delta_color="normal" if avg_change > 0 else "inverse"
            )
            st.metric(
                "上涨数量", 
                f"{positive_count}",
                f"占比 {positive_count/len(data)*100:.1f}%"
            )
    
    with col2:
        if '涨跌幅' in data.columns:
            best_performer = data.loc[data['涨跌幅'].idxmax()]
            worst_performer = data.loc[data['涨跌幅'].idxmin()]
            
            st.metric(
                "最佳表现", 
                f"{best_performer['涨跌幅']:.2f}%",
                best_performer['指数名称']
            )
    
    with col3:
        if '涨跌幅' in data.columns:
            st.metric(
                "最差表现", 
                f"{worst_performer['涨跌幅']:.2f}%",
                worst_performer['指数名称']
            )
    
    with col4:
        if '涨跌幅' in data.columns:
            volatility = data['涨跌幅'].std()
            st.metric(
                "涨跌波动", 
                f"{volatility:.2f}%",
                "标准差"
            )
    
    # 其他可视化分析
    st.subheader("📈 其他分析图表")
    
    if not data.empty:
        # 第二行：估值分析
        st.subheader("💰 估值分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 市盈率排名前15
            if '市盈率' in data.columns:
                # 过滤异常值并排序
                pe_data = data[data['市盈率'] > 0][data['市盈率'] < 100].nlargest(15, '市盈率')
                
                if not pe_data.empty:
                    fig_pe = go.Figure()
                    
                    # 根据市盈率值设置颜色（高市盈率用红色，低市盈率用绿色）
                    colors = ['#d62728' if x > pe_data['市盈率'].median() else '#2ca02c' for x in pe_data['市盈率']]
                    
                    fig_pe.add_trace(go.Bar(
                        y=pe_data['指数名称'],
                        x=pe_data['市盈率'],
                        marker_color=colors,
                        orientation='h',
                        hovertemplate='<b>%{y}</b><br>市盈率: %{x:.2f}倍<extra></extra>',
                        text=[f'{x:.1f}' for x in pe_data['市盈率']],
                        textposition='auto'
                    ))
                    
                    fig_pe.update_layout(
                        title=f'{selected_symbol}市盈率排名前15',
                        yaxis_title='指数名称',
                        xaxis_title='市盈率 (倍)',
                        height=500,
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_pe, use_container_width=True)
                else:
                    st.info("市盈率数据不足，无法生成排名图")
        
        with col2:
            # 市净率排名前15
            if '市净率' in data.columns:
                # 过滤异常值并排序
                pb_data = data[data['市净率'] > 0][data['市净率'] < 10].nlargest(15, '市净率')
                
                if not pb_data.empty:
                    fig_pb = go.Figure()
                    
                    # 根据市净率值设置颜色（高市净率用红色，低市净率用绿色）
                    colors = ['#d62728' if x > pb_data['市净率'].median() else '#2ca02c' for x in pb_data['市净率']]
                    
                    fig_pb.add_trace(go.Bar(
                        y=pb_data['指数名称'],
                        x=pb_data['市净率'],
                        marker_color=colors,
                        orientation='h',
                        hovertemplate='<b>%{y}</b><br>市净率: %{x:.2f}倍<extra></extra>',
                        text=[f'{x:.2f}' for x in pb_data['市净率']],
                        textposition='auto'
                    ))
                    
                    fig_pb.update_layout(
                        title=f'{selected_symbol}市净率排名前15',
                        yaxis_title='指数名称',
                        xaxis_title='市净率 (倍)',
                        height=500,
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_pb, use_container_width=True)
                else:
                    st.info("市净率数据不足，无法生成排名图")
        
        # 第三行：成交分析
        st.subheader("📈 成交分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 成交量排名前15
            if '成交量' in data.columns:
                volume_data = data.nlargest(15, '成交量')[['指数名称', '成交量']]
                
                fig_volume = go.Figure()
                
                fig_volume.add_trace(go.Bar(
                    y=volume_data['指数名称'],
                    x=volume_data['成交量'],
                    marker_color='#1f77b4',
                    orientation='h',
                    hovertemplate='<b>%{y}</b><br>成交量: %{x:.2f}亿股<extra></extra>',
                    text=[f'{x:.1f}' for x in volume_data['成交量']],
                    textposition='auto'
                ))
                
                fig_volume.update_layout(
                    title=f'{selected_symbol}成交量排名前15',
                    yaxis_title='指数名称',
                    xaxis_title='成交量 (亿股)',
                    height=500,
                    showlegend=False
                )
                
                st.plotly_chart(fig_volume, use_container_width=True)
        
        with col2:
            # 换手率排名前15
            if '换手率' in data.columns:
                turnover_data = data.nlargest(15, '换手率')[['指数名称', '换手率']]
                
                fig_turnover = go.Figure()
                
                fig_turnover.add_trace(go.Bar(
                    y=turnover_data['指数名称'],
                    x=turnover_data['换手率'],
                    marker_color='#ff7f0e',
                    orientation='h',
                    hovertemplate='<b>%{y}</b><br>换手率: %{x:.2f}%<extra></extra>',
                    text=[f'{x:.2f}' for x in turnover_data['换手率']],
                    textposition='auto'
                ))
                
                fig_turnover.update_layout(
                    title=f'{selected_symbol}换手率排名前15',
                    yaxis_title='指数名称',
                    xaxis_title='换手率 (%)',
                    height=500,
                    showlegend=False
                )
                
                st.plotly_chart(fig_turnover, use_container_width=True)
        
        # 第四行：市值分析
        st.subheader("💎 市值分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 流通市值排名前15
            if '流通市值' in data.columns:
                market_cap_data = data[data['流通市值'] > 0].nlargest(15, '流通市值')[['指数名称', '流通市值']]
                
                if not market_cap_data.empty:
                    fig_market_cap = go.Figure()
                    
                    fig_market_cap.add_trace(go.Bar(
                        y=market_cap_data['指数名称'],
                        x=market_cap_data['流通市值'],
                        marker_color='#9467bd',
                        orientation='h',
                        hovertemplate='<b>%{y}</b><br>流通市值: %{x:.2f}亿元<extra></extra>',
                        text=[f'{x:.0f}' for x in market_cap_data['流通市值']],
                        textposition='auto'
                    ))
                    
                    fig_market_cap.update_layout(
                        title=f'{selected_symbol}流通市值排名前15',
                        yaxis_title='指数名称',
                        xaxis_title='流通市值 (亿元)',
                        height=500,
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_market_cap, use_container_width=True)
                else:
                    st.info("流通市值数据不足，无法生成排名图")
        
        with col2:
            # 股息率排名前15
            if '股息率' in data.columns:
                dividend_data = data[data['股息率'] > 0].nlargest(15, '股息率')[['指数名称', '股息率']]
                
                if not dividend_data.empty:
                    fig_dividend = go.Figure()
                    
                    fig_dividend.add_trace(go.Bar(
                        y=dividend_data['指数名称'],
                        x=dividend_data['股息率'],
                        marker_color='#2ca02c',
                        orientation='h',
                        hovertemplate='<b>%{y}</b><br>股息率: %{x:.2f}%<extra></extra>',
                        text=[f'{x:.2f}' for x in dividend_data['股息率']],
                        textposition='auto'
                    ))
                    
                    fig_dividend.update_layout(
                        title=f'{selected_symbol}股息率排名前15',
                        yaxis_title='指数名称',
                        xaxis_title='股息率 (%)',
                        height=500,
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_dividend, use_container_width=True)
                else:
                    st.info("股息率数据不足，无法生成排名图")
        
        # 投资建议
        st.subheader("💡 投资建议")
        
        if '涨跌幅' in data.columns:
            # 找出表现最好和最差的指数
            best_performer = data.loc[data['涨跌幅'].idxmax()]
            worst_performer = data.loc[data['涨跌幅'].idxmin()]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                **🏆 最佳表现：**
                - **指数：** {best_performer['指数名称']}
                - **涨跌幅：** {best_performer['涨跌幅']:.2f}%
                - **收盘指数：** {best_performer['收盘指数']:.2f}
                - **成交量：** {best_performer['成交量']:.2f}亿股
                """)
            
            with col2:
                st.markdown(f"""
                **📉 最差表现：**
                - **指数：** {worst_performer['指数名称']}
                - **涨跌幅：** {worst_performer['涨跌幅']:.2f}%
                - **收盘指数：** {worst_performer['收盘指数']:.2f}
                - **成交量：** {worst_performer['成交量']:.2f}亿股
                """)
            
            # 整体分析
            positive_count = sum(1 for x in data['涨跌幅'] if x > 0)
            negative_count = sum(1 for x in data['涨跌幅'] if x < 0)
            avg_change = data['涨跌幅'].mean()
            
            st.markdown(f"""
            **📊 整体分析：**
            - **分析类别：** {selected_symbol}
            - **分析日期：** {selected_date_friendly}
            - **总数量：** {len(data)}个指数
            - **上涨数量：** {positive_count}个 ({positive_count/len(data)*100:.1f}%)
            - **下跌数量：** {negative_count}个 ({negative_count/len(data)*100:.1f}%)
            - **平均涨跌幅：** {avg_change:.2f}%
            
            **💡 投资建议：**
            - **强势指数**：关注涨跌幅较高的指数，可能处于上升周期
            - **弱势指数**：涨跌幅较低的指数可能处于调整期，关注反转机会
            - **估值分析**：结合市盈率、市净率等指标，寻找估值合理的投资机会
            - **成交活跃度**：关注换手率和成交量较高的指数，可能具有更好的流动性
            - **市值特征**：不同流通市值的指数可能具有不同的投资特征
            - **行业轮动**：通过月度数据观察行业轮动规律，把握投资时机
            """)
        
        # 显示原始数据表格（放在最后）
        st.subheader("📋 原始数据表格")
        
        # 格式化表格显示
        def color_returns(val):
            """根据涨跌幅设置颜色"""
            if pd.isna(val):
                return ''
            if val > 0:
                return 'background-color: #f8d7da; color: #721c24'  # 红色背景（涨）
            elif val < 0:
                return 'background-color: #d4edda; color: #155724'  # 绿色背景（跌）
            else:
                return ''
        
        # 应用样式
        styled_df = data.style.apply(
            lambda x: [color_returns(val) if col == '涨跌幅' else '' for col, val in x.items()], 
            subset=['涨跌幅']
        ).format({
            '收盘指数': '{:.2f}',
            '成交量': '{:.2f}',
            '涨跌幅': '{:.2f}%',
            '换手率': '{:.2f}%',
            '市盈率': '{:.2f}',
            '市净率': '{:.2f}',
            '均价': '{:.2f}',
            '成交额占比': '{:.2f}%',
            '流通市值': '{:.2f}',
            '平均流通市值': '{:.2f}',
            '股息率': '{:.2f}%'
        })
        
        st.dataframe(styled_df, use_container_width=True)
        
        # 下载功能
        st.subheader("💾 下载分析结果")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 下载CSV
            csv = data.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 下载CSV报告",
                data=csv,
                file_name=f"申万指数分析_{selected_symbol}_{selected_date_api}.csv",
                mime="text/csv"
            )
        
        with col2:
            # 下载Excel
            try:
                import io
                
                # 创建Excel文件
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    data.to_excel(writer, sheet_name='申万指数分析结果', index=False)
                    
                    # 获取工作表
                    worksheet = writer.sheets['申万指数分析结果']
                    
                    # 设置列宽
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 20)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                excel_data = output.getvalue()
                st.download_button(
                    label="📥 下载Excel报告",
                    data=excel_data,
                    file_name=f"申万指数分析_{selected_symbol}_{selected_date_api}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except ImportError:
                st.info("💡 安装 openpyxl 可下载Excel格式报告")
else:
    st.info("👆 请设置分析参数并点击运行按钮开始分析")
