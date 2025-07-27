import streamlit as st
import json
import os
from ai_utils import get_api_key, set_api_key, get_api_key_path
from data import get_etf_list

st.set_page_config(page_title="AI助手与API密钥配置", page_icon="🤖", layout="wide")
st.title("🤖 AI助手与API密钥配置")

# 配置文件路径
config_dir = "config"
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

favorite_etfs_file = os.path.join(config_dir, "favorite_etfs.json")
api_key_file = get_api_key_path()

# 创建两列布局
col1, col2 = st.columns(2)

with col1:
    st.header("🔑 AI API密钥管理")
    
    st.markdown("""
    > 本页用于配置和管理AI助手相关的API Key。API Key仅保存在本地，不会上传服务器，确保安全。
    """)

    api_key = st.text_input("请输入你的AI API Key（仅本地保存）", value=get_api_key(), type="password")
    if st.button("保存API Key"):
        set_api_key(api_key)
        st.success("API Key已保存，下次自动读取。")

    if get_api_key():
        st.info("✅ 当前已保存的API Key（已隐藏）")
    else:
        st.warning("⚠️ 尚未保存API Key，部分AI分析功能将不可用。")

    st.markdown(f"**本地保存路径：** `{api_key_file}`")

    st.markdown("""
    - 推荐使用 [Qwen-plus](https://help.aliyun.com/zh/dashscope/developer-reference/qwen-openai-api) 或兼容OpenAI API的Key。
    - 如需更换Key，直接输入新Key并保存即可。
    - 如需彻底删除Key，请手动删除上述路径下的 user_openai_key.txt 文件。
    """)

with col2:
    st.header("📈 自选ETF配置")
    
    st.markdown("""
    > 配置你常用的ETF，这些ETF将在各个页面中优先显示，方便快速选择。
    """)
    
    # 获取ETF列表
    etf_list = get_etf_list()
    if etf_list.empty:
        st.error("无法获取ETF列表，请检查网络连接")
    else:
        # 加载已保存的自选ETF
        favorite_etfs = []
        if os.path.exists(favorite_etfs_file):
            try:
                with open(favorite_etfs_file, 'r', encoding='utf-8') as f:
                    favorite_etfs = [str(code) for code in json.load(f)]
            except:
                favorite_etfs = []
        
        # 调试信息
        with st.expander("🔧 调试信息"):
            st.write(f"**配置文件路径：** `{favorite_etfs_file}`")
            st.write(f"**配置文件存在：** {os.path.exists(favorite_etfs_file)}")
            st.write(f"**自选ETF数量：** {len(favorite_etfs)}")
            st.write(f"**自选ETF列表：** {favorite_etfs}")
            st.write(f"**ETF列表总数：** {len(etf_list)}")
            st.write(f"**ETF列表前5个：** {etf_list['symbol'].head().tolist()}")
        
        # 显示当前自选ETF
        if favorite_etfs:
            st.subheader("当前自选ETF")
            for i, etf_code in enumerate(favorite_etfs):
                # 确保类型一致进行比较
                etf_info = etf_list[etf_list['symbol'].astype(str) == etf_code]
                if not etf_info.empty:
                    etf_name = etf_info['name'].values[0]
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"**{etf_code}** - {etf_name}")
                    with col_b:
                        if st.button("删除", key=f"del_{i}"):
                            favorite_etfs.remove(etf_code)
                            with open(favorite_etfs_file, 'w', encoding='utf-8') as f:
                                json.dump([str(code) for code in favorite_etfs], f, ensure_ascii=False, indent=2)
                            st.success(f"已删除 {etf_code}")
                            st.rerun()
                else:
                    # 如果找不到对应的ETF信息，显示代码但标记为未知
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"**{etf_code}** - 未知ETF")
                    with col_b:
                        if st.button("删除", key=f"del_{i}"):
                            favorite_etfs.remove(etf_code)
                            with open(favorite_etfs_file, 'w', encoding='utf-8') as f:
                                json.dump([str(code) for code in favorite_etfs], f, ensure_ascii=False, indent=2)
                            st.success(f"已删除 {etf_code}")
                            st.rerun()
        else:
            st.info("暂无自选ETF，请添加你常用的ETF")
        
        st.markdown("---")
        
        # 添加新的自选ETF
        st.subheader("添加自选ETF")
        
        # 搜索框
        search_term = st.text_input("搜索ETF代码或名称", placeholder="例如：510300 或 沪深300")
        
        # 过滤ETF列表
        if search_term:
            filtered_etfs = etf_list[
                (etf_list['symbol'].astype(str).str.contains(search_term, case=False)) |
                (etf_list['name'].str.contains(search_term, case=False))
            ]
        else:
            # 显示前20个ETF作为默认选项
            filtered_etfs = etf_list.head(20)
        
        # 显示可选择的ETF
        if not filtered_etfs.empty:
            st.write("**可选择的ETF：**")
            for _, row in filtered_etfs.iterrows():
                etf_code = str(row['symbol'])
                etf_name = row['name']
                
                # 检查是否已经在自选列表中
                is_favorite = etf_code in favorite_etfs
                
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.write(f"{etf_code} - {etf_name}")
                with col_b:
                    if is_favorite:
                        st.write("✅ 已添加")
                    else:
                        if st.button("添加", key=f"add_{etf_code}"):
                            favorite_etfs.append(etf_code)
                            with open(favorite_etfs_file, 'w', encoding='utf-8') as f:
                                json.dump([str(code) for code in favorite_etfs], f, ensure_ascii=False, indent=2)
                            st.success(f"已添加 {etf_code}")
                            st.rerun()
        else:
            st.warning("未找到匹配的ETF")
        
        st.markdown(f"**配置文件路径：** `{favorite_etfs_file}`")

# 底部说明
st.markdown("---")
st.markdown("""
### 🤖 配置说明
- **AI助手API密钥**：用于AI分析、智能助手等功能，支持OpenAI、Qwen等兼容API
- **自选ETF**：配置后在各页面的ETF选择器中会优先显示
- **数据安全**：所有配置仅保存在本地，不会上传到服务器
- **配置同步**：配置修改后立即生效，无需重启应用
""") 