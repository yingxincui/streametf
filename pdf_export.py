import io
import base64
import os
from datetime import datetime
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# 添加中文字体支持
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 注册中文字体
try:
    # Windows系统字体路径
    font_path = "C:/Windows/Fonts/simhei.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('SimHei', font_path))
    else:
        # 尝试其他可能的字体路径
        alt_font_paths = [
            "C:/Windows/Fonts/simkai.ttf",  # 楷体
            "C:/Windows/Fonts/simsun.ttc",  # 宋体
            "C:/Windows/Fonts/msyh.ttc"     # 微软雅黑
        ]
        for alt_path in alt_font_paths:
            if os.path.exists(alt_path):
                font_name = os.path.basename(alt_path).split('.')[0]
                pdfmetrics.registerFont(TTFont(font_name, alt_path))
                break
except Exception as e:
    print(f"注册中文字体失败: {str(e)}")
    # 如果注册失败，程序仍会继续，但PDF中的中文可能显示为乱码

# 创建PDF样式
def get_styles():
    styles = getSampleStyleSheet()
    
    # 设置默认字体为中文字体
    chinese_font = 'SimHei'  # 默认使用黑体
    
    # 如果SimHei注册失败，尝试使用其他已注册的字体
    if 'SimHei' not in pdfmetrics.getRegisteredFontNames():
        registered_fonts = pdfmetrics.getRegisteredFontNames()
        for font in ['simkai', 'simsun', 'msyh']:
            if font in registered_fonts:
                chinese_font = font
                break
    
    # 检查样式是否已存在，避免重复添加
    if 'CustomTitle' not in styles:
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName=chinese_font  # 使用中文字体
        ))
    
    if 'CustomSubtitle' not in styles:
        styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            alignment=TA_LEFT,
            spaceAfter=10,
            spaceBefore=10,
            fontName=chinese_font  # 使用中文字体
        ))
    
    if 'Normal_CENTER' not in styles:
        styles.add(ParagraphStyle(
            name='Normal_CENTER',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontName=chinese_font  # 使用中文字体
        ))
    
    # 修改默认的Normal样式，使用中文字体
    styles['Normal'].fontName = chinese_font
    
    return styles

# 将matplotlib图形转换为reportlab图像
def fig_to_image(fig, width=5*inch):
    img_data = io.BytesIO()
    fig.savefig(img_data, format='png', bbox_inches='tight', dpi=120)
    img_data.seek(0)
    img = Image(img_data, width=width)
    # 设置图像的最大宽度和高度，确保不会超出页面边界
    img.drawHeight = img.drawWidth * 0.6  # 控制高宽比
    return img

# 创建组合回测PDF报告
def create_portfolio_backtest_pdf(portfolio_value, benchmark_value, returns, etf_data, etf_names, 
                                 metrics, annual_returns, initial_investment, selected_etfs):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = get_styles()
    elements = []
    
    # 标题
    title = Paragraph(f"ETF组合回测报告 - {datetime.now().strftime('%Y-%m-%d')}", styles['CustomTitle'])
    elements.append(title)
    elements.append(Spacer(1, 0.5*cm))
    
    # 回测参数
    elements.append(Paragraph("回测参数", styles['CustomSubtitle']))
    etf_names_list = [f"{etf} - {etf_names.get(etf.split('_')[0], '')}" for etf in etf_data.columns]
    param_data = [
        ["回测时间范围", f"{portfolio_value.index[0].strftime('%Y-%m-%d')} 至 {portfolio_value.index[-1].strftime('%Y-%m-%d')}"],
        ["初始投资金额", f"{initial_investment:,.2f} 元"],
        ["ETF组合", ", ".join(etf_names_list)]
    ]
    param_table = Table(param_data, colWidths=[3*cm, 8*cm])
    param_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
    ]))
    elements.append(param_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # 性能指标
    elements.append(Paragraph("性能指标", styles['CustomSubtitle']))
    metric_data = [["指标", "值"]]
    for key, value in metrics.items():
        metric_data.append([key, f"{value:.2f}{'%' if '%' in key else ''}"])
    metric_table = Table(metric_data, colWidths=[5*cm, 6*cm])
    metric_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    elements.append(metric_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # 净值曲线图
    elements.append(Paragraph("净值曲线", styles['CustomSubtitle']))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(portfolio_value.index, portfolio_value / initial_investment, label='投资组合', linewidth=2, color='black')
    # 限制显示的ETF数量，避免图例过多
    etf_count = 0
    for col in etf_data.columns:
        if etf_count < 5:  # 最多显示5个ETF曲线
            symbol = col.split('_')[0]
            ax.plot(etf_data[col].index, etf_data[col] / etf_data[col].iloc[0], 
                    label=f"{etf_names.get(symbol, '')}", alpha=0.6, linewidth=1)
            etf_count += 1
    if benchmark_value is not None:
        ax.plot(benchmark_value.index, benchmark_value / initial_investment, 
                label='等权重基准', linestyle='--', linewidth=1.5, color='gray')
    ax.set_title("投资组合与各ETF净值走势（归一化）", fontsize=12)
    ax.set_xlabel("日期", fontsize=10)
    ax.set_ylabel("净值倍数", fontsize=10)
    # 调整图例位置和大小
    ax.legend(loc='best', fontsize=8)
    ax.grid(True)
    plt.tight_layout()
    elements.append(fig_to_image(fig, width=5*inch))
    plt.close(fig)
    elements.append(Spacer(1, 0.5*cm))
    
    # 年度收益率表格
    if annual_returns is not None and not annual_returns.empty:
        elements.append(Paragraph("年度收益率", styles['CustomSubtitle']))
        annual_data = [["年份", "收益率 (%)"]]
        for year, ret in zip(annual_returns.index, annual_returns.values):
            annual_data.append([str(year), f"{ret:.2f}%"])
        annual_table = Table(annual_data, colWidths=[5*cm, 6*cm])
        annual_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        elements.append(annual_table)
        elements.append(Spacer(1, 0.5*cm))
    
    # 相关性矩阵图
    elements.append(Paragraph("ETF相关性矩阵", styles['CustomSubtitle']))
    corr_fig, corr_ax = plt.subplots(figsize=(6, 4))
    import seaborn as sns
    sns.heatmap(returns.corr(), annot=True, cmap='coolwarm', center=0, ax=corr_ax, annot_kws={"size": 8})
    plt.title("ETF相关性矩阵", fontsize=12)
    elements.append(fig_to_image(corr_fig, width=4.5*inch))
    plt.close(corr_fig)
    
    # 生成PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# 创建定投回测PDF报告
def create_dca_backtest_pdf(portfolio_value, total_invested, returns, etf_data, annualized_return, selected_etfs):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = get_styles()
    elements = []
    
    # 标题
    title = Paragraph(f"ETF定投回测报告 - {datetime.now().strftime('%Y-%m-%d')}", styles['CustomTitle'])
    elements.append(title)
    elements.append(Spacer(1, 0.5*cm))
    
    # 回测参数
    elements.append(Paragraph("定投参数", styles['CustomSubtitle']))
    param_data = [
        ["定投时间范围", f"{portfolio_value.index[0].strftime('%Y-%m-%d')} 至 {portfolio_value.index[-1].strftime('%Y-%m-%d')}"],
        ["ETF组合", ", ".join(selected_etfs)]
    ]
    param_table = Table(param_data, colWidths=[3*cm, 8*cm])
    param_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
    ]))
    elements.append(param_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # 性能指标
    elements.append(Paragraph("性能指标", styles['CustomSubtitle']))
    final_value = portfolio_value.iloc[-1]
    total_invested_final = total_invested.iloc[-1]
    total_return = (final_value / total_invested_final - 1) * 100
    
    metric_data = [
        ["指标", "值"],
        ["累计投入金额", f"{total_invested_final:,.2f} 元"],
        ["当前价值", f"{final_value:,.2f} 元"],
        ["总收益率", f"{total_return:.2f}%"],
        ["年化收益率 (XIRR)", f"{annualized_return:.2f}%"]
    ]
    metric_table = Table(metric_data, colWidths=[5*cm, 6*cm])
    metric_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    elements.append(metric_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # 定投累计价值图
    elements.append(Paragraph("定投累计价值", styles['CustomSubtitle']))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(portfolio_value.index, portfolio_value, label='定投累计价值', linewidth=2, color='blue')
    ax.plot(total_invested.index, total_invested, label='累计投入金额', linestyle='--', linewidth=1.5, color='green')
    ax.set_title("定投累计价值 vs 累计投入金额", fontsize=12)
    ax.set_xlabel("日期", fontsize=10)
    ax.set_ylabel("金额 (元)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True)
    plt.tight_layout()
    elements.append(fig_to_image(fig, width=5*inch))
    plt.close(fig)
    elements.append(Spacer(1, 0.5*cm))
    
    # 收益率曲线
    elements.append(Paragraph("定投收益率", styles['CustomSubtitle']))
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.plot(returns.index, returns, label='定投收益率', linewidth=2, color='red')
    ax2.set_title("定投收益率变化", fontsize=12)
    ax2.set_xlabel("日期", fontsize=10)
    ax2.set_ylabel("收益率 (%)", fontsize=10)
    ax2.legend(fontsize=8)
    ax2.grid(True)
    plt.tight_layout()
    elements.append(fig_to_image(fig2, width=5*inch))
    plt.close(fig2)
    
    # 生成PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# 生成下载链接
def get_pdf_download_link(pdf_buffer, filename="report.pdf"):
    b64 = base64.b64encode(pdf_buffer.read()).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}" style="display: inline-block; padding: 0.5em 1em; color: white; background-color: #4CAF50; text-decoration: none; border-radius: 4px; font-weight: bold;">📥 下载PDF报告</a>'
    return href