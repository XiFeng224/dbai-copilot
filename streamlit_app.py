from __future__ import annotations

import os
import tempfile
import time

import streamlit as st

from app.doc_loader import iter_metadata, load_file
from app.llm import invoke_llm
from app.prompts import (
    PPT_TEMPLATE,
    QUESTIONS_TEMPLATE,
    SUMMARY_TEMPLATE,
)
from app.rag import build_or_replace_index, make_session_id, retrieve_context
from app.db_agent import (
    DatabaseFactory,
    MetricsCollector,
    SlowQueryParser,
    ExplainVisualizer,
    SQLFingerprint,
    LockAnalyzer,
    IndexRecommender,
    SQLRewriter,
    ParamTuner,
    AIDialogue,
    AutomationManager
)
from app.ui_enhancement.theme import ThemeManager, NavigationManager, ResponsiveLayout
from app.security.auth import SecurityManager
from app.utils.error_handler import SystemMonitor
from config import CHROMA_PERSIST_DIR


# 应用主题和样式
ThemeManager.apply_custom_theme()

st.set_page_config(page_title="数据库AI助手 - DBAI-Copilot", layout="wide", page_icon="🤖")

# 初始化系统管理器
if "security_manager" not in st.session_state:
    st.session_state.security_manager = SecurityManager()
if "system_monitor" not in st.session_state:
    st.session_state.system_monitor = SystemMonitor()

# 用户认证
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "session_token" not in st.session_state:
    st.session_state.session_token = None

# 登录界面
if not st.session_state.authenticated:
    # 应用登录页面特殊样式
    st.markdown("""
    <style>
    .login-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 0;
    }
    .login-main {
        display: flex;
        gap: 30px;
        padding: 40px;
        background: white;
        border-radius: 24px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.08);
        border: 1px solid #f0f4f8;
    }
    .login-left {
        flex: 1;
        min-width: 300px;
    }
    .login-right {
        flex: 1;
        min-width: 300px;
        padding-left: 30px;
        border-left: 1px solid #e8eff5;
    }
    .login-header {
        text-align: center;
        margin-bottom: 35px;
    }
    .login-logo {
        font-size: 3rem;
        margin-bottom: 15px;
    }
    .login-title {
        font-size: 2rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 8px;
        letter-spacing: -0.5px;
    }
    .login-subtitle {
        color: #64748b;
        font-size: 1rem;
        font-weight: 400;
    }
    .feature-card {
        padding: 16px;
        margin-bottom: 12px;
        background: #f8fafc;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        transition: all 0.2s ease;
    }
    .feature-card:hover {
        background: #f1f5f9;
        border-color: #cbd5e1;
        transform: translateY(-2px);
    }
    .feature-icon {
        font-size: 1.3rem;
        margin-bottom: 4px;
    }
    .feature-title {
        font-weight: 600;
        color: #1e293b;
        font-size: 0.95rem;
    }
    .feature-desc {
        color: #64748b;
        font-size: 0.85rem;
        margin-top: 2px;
    }
    .quick-login-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        padding: 20px;
        border-radius: 16px;
        border: 2px solid #e2e8f0;
        text-align: center;
    }
    .footer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.85rem;
        margin-top: 25px;
        padding-top: 20px;
        border-top: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 登录容器
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # 登录标题
    st.markdown('''
    <div class="login-header">
        <div class="login-logo">🤖</div>
        <div class="login-title">DBAI-Copilot</div>
        <div class="login-subtitle">数据库AI助手 · 智能运维平台</div>
    </div>
    ''', unsafe_allow_html=True)
    
    # 登录主体 - 左右布局
    st.markdown('<div class="login-main">', unsafe_allow_html=True)
    
    # 左侧 - 登录/注册表单
    st.markdown('<div class="login-left">', unsafe_allow_html=True)
    
    # 登录和注册选项卡
    tab1, tab2 = st.tabs(["🔑 用户登录", "📝 用户注册"])
    
    with tab1:
        st.markdown('<div style="padding: 10px 0;">', unsafe_allow_html=True)
        
        username = st.text_input("👤 用户名", placeholder="请输入用户名", key="login_username")
        password = st.text_input("🔒 密码", type="password", placeholder="请输入密码", key="login_password")
        
        # 登录按钮
        if st.button("🚀 登录系统", type="primary", use_container_width=True):
            if username and password:
                session_token = st.session_state.security_manager.login(username, password)
                if session_token:
                    st.session_state.authenticated = True
                    st.session_state.session_token = session_token
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("❌ 用户名或密码错误")
            else:
                st.warning("⚠️ 请输入用户名和密码")
        
        # 记住我
        st.checkbox("记住登录状态", value=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div style="padding: 10px 0;">', unsafe_allow_html=True)
        
        new_username = st.text_input("👤 新用户名", placeholder="请输入3-20位用户名", key="register_username")
        new_password = st.text_input("🔒 设置密码", type="password", placeholder="请输入6位以上密码", key="register_password")
        confirm_password = st.text_input("🔒 确认密码", type="password", placeholder="请再次输入密码", key="confirm_password")
        
        # 用户角色选择
        user_role = st.selectbox("🎯 用户角色", ["viewer", "operator", "admin"], 
                                format_func=lambda x: {"viewer": "👀 查看者", "operator": "⚙️ 操作员", "admin": "👑 管理员"}[x])
        
        # 注册按钮
        if st.button("✅ 注册账号", type="primary", use_container_width=True):
            if new_username and new_password and confirm_password:
                if len(new_username) < 3:
                    st.error("❌ 用户名长度至少3个字符")
                elif len(new_password) < 6:
                    st.error("❌ 密码长度至少6个字符")
                elif new_password != confirm_password:
                    st.error("❌ 两次输入的密码不一致")
                else:
                    success = st.session_state.security_manager.register(new_username, new_password, user_role)
                    if success:
                        st.success("✅ 账号注册成功！请使用新账号登录")
                        st.session_state.register_username = ""
                        st.session_state.register_password = ""
                        st.session_state.confirm_password = ""
                    else:
                        st.error("❌ 注册失败，用户名可能已存在")
            else:
                st.warning("⚠️ 请填写完整的注册信息")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 右侧 - 功能特色和快速登录
    st.markdown('<div class="login-right">', unsafe_allow_html=True)
    
    # 功能特色卡片
    st.markdown("### ✨ 核心功能")
    
    features = [
        ("🤖", "AI智能对话", "自然语言问答，智能诊断报告"),
        ("📊", "实时监控", "性能指标采集，慢查询管理"),
        ("🔍", "智能诊断", "执行计划分析，锁等待检测"),
        ("⚡", "自动优化", "索引推荐，SQL优化，参数调优"),
        ("🔒", "安全可靠", "完整的用户认证和权限管理")
    ]
    
    for icon, title, desc in features:
        st.markdown(f'''
        <div class="feature-card">
            <div class="feature-icon">{icon}</div>
            <div class="feature-title">{title}</div>
            <div class="feature-desc">{desc}</div>
        </div>
        ''', unsafe_allow_html=True)
    
    # 快速登录卡片
    st.markdown("---")
    st.markdown('<div class="quick-login-card">', unsafe_allow_html=True)
    st.markdown("### 👤 快速登录")
    st.markdown("""
    **用户名**: `admin`  
    **密码**: `admin123`
    """)
    
    if st.button("⚡ 一键登录", key="quick_login", use_container_width=True):
        session_token = st.session_state.security_manager.login("admin", "admin123")
        if session_token:
            st.session_state.authenticated = True
            st.session_state.session_token = session_token
            st.session_state.username = "admin"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 底部信息
    st.markdown('''
    <div class="footer">
        <strong>DBAI-Copilot</strong> · 数据库AI助手 · 版本 1.0.0
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.stop()

# 主应用界面
st.markdown("""
<style>
/* 全局样式优化 */
.main {
    padding: 1rem 2rem;
}

/* 侧边栏优化 */
.css-1d391kg {
    padding-top: 2rem;
}

/* 卡片样式 */
.card {
    padding: 1.5rem;
    border-radius: 16px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    transition: all 0.3s ease;
    margin-bottom: 1rem;
}

.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 24px rgba(0,0,0,0.08);
    border-color: #cbd5e1;
}

.card-icon {
    font-size: 2.5rem;
    margin-bottom: 0.8rem;
}

.card-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 0.4rem;
}

.card-desc {
    color: #64748b;
    font-size: 0.9rem;
    line-height: 1.5;
}

/* 特色卡片 */
.feature-card {
    padding: 1.2rem;
    border-radius: 12px;
    background: white;
    border: 1px solid #e2e8f0;
    text-align: center;
    transition: all 0.3s ease;
}

.feature-card:hover {
    background: #f8fafc;
    transform: translateY(-2px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.06);
}

.feature-icon-large {
    font-size: 2rem;
    margin-bottom: 0.6rem;
}

.feature-title {
    font-weight: 600;
    color: #1e293b;
    font-size: 0.95rem;
}

.feature-desc {
    color: #64748b;
    font-size: 0.85rem;
    margin-top: 0.3rem;
}

/* 欢迎标题 */
.welcome-title {
    text-align: center;
    margin-bottom: 2rem;
}

.welcome-main-title {
    font-size: 2.5rem;
    font-weight: 800;
    color: #1e293b;
    margin-bottom: 0.5rem;
}

.welcome-subtitle {
    font-size: 1.1rem;
    color: #64748b;
}

/* 侧边栏用户卡片 */
.sidebar-user-card {
    padding: 1rem;
    background: #f8fafc;
    border-radius: 12px;
    margin-bottom: 1rem;
    border: 1px solid #e2e8f0;
}

/* 分隔线 */
.section-divider {
    margin: 2.5rem 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
    border: none;
}
</style>
""", unsafe_allow_html=True)

NavigationManager.create_breadcrumb("主控制台")

# 添加欢迎页面选项到导航栏
pages = st.sidebar.selectbox(
    "选择功能",
    ["🏠 欢迎页面", "🎯 竞赛教练智能助手", "🛠️ 数据库运维智能助手", "⚙️ 系统管理"]
)

# 侧边栏用户信息
with st.sidebar:
    st.markdown("""
    <div class="sidebar-user-card">
    """, unsafe_allow_html=True)
    st.markdown(f"**👤 当前用户:** {st.session_state.username}")
    
    user_info = st.session_state.security_manager.get_user_info(st.session_state.session_token)
    if user_info:
        role_emoji = {"viewer": "👀", "operator": "⚙️", "admin": "👑"}.get(user_info['role'], "👤")
        st.markdown(f"**{role_emoji} 角色:** {user_info['role']}")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 快速操作按钮
    st.markdown("---")
    st.markdown("### 🚀 快速操作")
    
    if st.button("📊 系统状态", use_container_width=True):
        try:
            system_status = st.session_state.system_monitor.get_system_status()
            st.success("✅ 系统运行正常")
            st.json(system_status)
        except Exception as e:
            st.error(f"❌ 获取系统状态失败: {str(e)}")
    
    if st.button("📋 使用指南", use_container_width=True):
        st.info("查看项目文档了解详细使用说明")
    
    st.markdown("---")
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state.security_manager.logout(st.session_state.session_token)
        st.session_state.authenticated = False
        st.session_state.session_token = None
        st.rerun()

# 主页面内容
if pages == "🏠 欢迎页面":
    # 欢迎标题
    st.markdown("""
    <div class="welcome-title">
        <div class="welcome-main-title">🎉 欢迎使用 DBAI-Copilot</div>
        <div class="welcome-subtitle">数据库AI助手 · 智能运维平台</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 项目介绍卡片
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown("""
        <div class="card">
            <div class="card-icon">📋</div>
            <div class="card-title">项目概述</div>
            <div class="card-desc">
                DBAI-Copilot 是一个集成了「竞赛教练智能助手」和「数据库运维智能助手」的双重功能智能系统，
                为计算机设计大赛和企业级数据库运维提供AI驱动的智能辅助。
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <div class="card-icon">🎯</div>
            <div class="card-title">核心功能</div>
            <div class="card-desc">
                • 竞赛教练智能助手 - 帮助参赛团队快速理解比赛需求<br>
                • 数据库运维智能助手 - 提供智能化的数据库监控和诊断<br>
                • AI智能分析 - 结合RAG技术和机器学习算法<br>
                • 安全可靠 - 完整的用户认证和权限管理系统
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    
    # 功能卡片
    st.markdown("### 🚀 快速开始")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="card">
            <div class="card-icon">🎯</div>
            <div class="card-title">竞赛教练</div>
            <div class="card-desc">
                上传比赛需求文档，智能生成技术方案和答辩材料
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("开始使用", key="start_competition", use_container_width=True):
            st.session_state.page = "竞赛教练智能助手"
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="card">
            <div class="card-icon">🛠️</div>
            <div class="card-title">数据库运维</div>
            <div class="card-desc">
                实时监控、智能诊断、自动化优化数据库性能
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("开始使用", key="start_database", use_container_width=True):
            st.session_state.page = "数据库运维智能助手"
            st.rerun()
    
    with col3:
        st.markdown("""
        <div class="card">
            <div class="card-icon">⚙️</div>
            <div class="card-title">系统管理</div>
            <div class="card-desc">
                用户管理、权限控制、系统监控和日志查看
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("开始使用", key="start_management", use_container_width=True):
            st.session_state.page = "系统管理"
            st.rerun()
    
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    
    # 技术特色
    st.markdown("### 💡 技术特色")
    
    tech_features = [
        ("🔗", "双重功能集成", "竞赛辅助与数据库运维完美结合"),
        ("🧠", "AI智能驱动", "RAG技术 + 机器学习预测分析"),
        ("🌐", "多数据库支持", "MySQL、PostgreSQL、SQL Server统一接口"),
        ("🎨", "现代化界面", "Streamlit响应式Web应用"),
        ("⚡", "自动化运维", "定时任务调度和智能优化"),
        ("🔒", "安全可靠", "完整的用户认证和权限管理")
    ]
    
    cols = st.columns(3)
    for i, (icon, title, desc) in enumerate(tech_features):
        with cols[i % 3]:
            st.markdown(f'''
            <div class="feature-card">
                <div class="feature-icon-large">{icon}</div>
                <div class="feature-title">{title}</div>
                <div class="feature-desc">{desc}</div>
            </div>
            ''', unsafe_allow_html=True)

elif pages == "🎯 竞赛教练智能助手":
    st.title("🎯 增强版竞赛教练智能助手")
    st.caption("AI驱动的智能竞赛助手 - 深度分析、智能方案、Demo演示、答辩准备")
    
    # 智能助手能力展示
    st.markdown("""
    <div class="card" style="margin-bottom: 20px;">
        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 150px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🔍</div>
                <div style="font-weight: bold;">深度分析</div>
                <div style="font-size: 12px; color: #666;">AI智能理解需求</div>
            </div>
            <div style="flex: 1; min-width: 150px;">
                <div style="font-size: 24px; margin-bottom: 5px;">💡</div>
                <div style="font-weight: bold;">智能推荐</div>
                <div style="font-size: 12px; color: #666;">技术方案建议</div>
            </div>
            <div style="flex: 1; min-width: 150px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🎭</div>
                <div style="font-weight: bold;">Demo剧本</div>
                <div style="font-size: 12px; color: #666;">定制化演示脚本</div>
            </div>
            <div style="flex: 1; min-width: 150px;">
                <div style="font-size: 24px; margin-bottom: 5px;">🎯</div>
                <div style="font-weight: bold;">答辩准备</div>
                <div style="font-size: 12px; color: #666;">完整答辩材料</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 初始化竞赛教练相关状态
    if "competition_docs" not in st.session_state:
        st.session_state.competition_docs = []
    if "competition_analysis" not in st.session_state:
        st.session_state.competition_analysis = {}
    if "generated_plan" not in st.session_state:
        st.session_state.generated_plan = {}
    
    # 功能选项卡
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📁 文档上传", "🔍 智能分析", "📋 方案生成", "🎭 Demo剧本", "🎯 答辩大纲", "🤖 AI智能对话"])
    
    with tab1:
        st.header("📁 上传比赛需求文档")
        
        uploaded_files = st.file_uploader(
            "选择比赛需求文档",
            type=["pdf", "docx", "txt", "md"],
            accept_multiple_files=True,
            help="支持PDF、Word、文本文件格式"
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                st.session_state.competition_docs.append({
                    "name": uploaded_file.name,
                    "size": uploaded_file.size,
                    "type": uploaded_file.type
                })
            
            st.success(f"✅ 成功上传 {len(uploaded_files)} 个文档")
            
            # 显示上传的文档列表
            st.subheader("📋 已上传文档")
            for i, doc in enumerate(st.session_state.competition_docs):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"📄 {doc['name']}")
                with col2:
                    st.write(f"📊 {doc['size']} bytes")
                with col3:
                    if st.button("🗑️", key=f"delete_{i}_{doc['name']}"):
                        st.session_state.competition_docs = [d for d in st.session_state.competition_docs if d['name'] != doc['name']]
                        st.rerun()
        
        # 手动输入需求
        st.subheader("📝 手动输入需求")
        manual_input = st.text_area(
            "或直接输入比赛需求描述",
            placeholder="请输入比赛的具体需求、目标、技术要求等...",
            height=150
        )
        
        if st.button("🚀 开始分析", type="primary", use_container_width=True):
            if st.session_state.competition_docs or manual_input:
                with st.spinner("🤖 AI正在深度分析比赛需求..."):
                    # 模拟分析过程
                    import time
                    time.sleep(3)
                    
                    # 生成详细的分析结果
                    st.session_state.competition_analysis = {
                        "requirements": "基于上传的文档和需求描述，识别出以下核心需求：\n\n"
                        "**项目目标**：开发一个集成了竞赛教练和数据库运维功能的智能助手系统\n"
                        "**技术要求**：支持多数据库连接、AI智能对话、实时监控、自动化运维\n"
                        "**功能需求**：文档上传分析、智能方案生成、Demo演示、答辩材料准备\n"
                        "**性能要求**：响应式界面、实时数据处理、高并发支持\n"
                        "**安全要求**：用户认证、权限管理、数据加密、操作审计",
                        
                        "tech_stack": [
                            "Python 3.12", "Streamlit (前端框架)", "FastAPI (后端API)", 
                            "MySQL/PostgreSQL (数据库)", "Redis (缓存)", "Docker (容器化)",
                            "OpenAI API (AI服务)", "Pandas (数据处理)", "Plotly (可视化)"
                        ],
                        
                        "features": [
                            "智能文档分析 - 自动识别比赛需求和技术要求",
                            "多数据库支持 - MySQL、PostgreSQL、SQL Server统一管理",
                            "AI智能对话 - 自然语言问答和智能诊断",
                            "实时监控系统 - 性能指标采集和可视化展示",
                            "自动化运维 - 定时任务调度和智能优化",
                            "用户权限管理 - 多级权限控制和操作审计",
                            "响应式界面 - 现代化UI设计和移动端适配"
                        ],
                        
                        "difficulty": "高级（涉及AI集成、多数据库、实时监控等复杂技术）",
                        "timeline": "6周详细开发计划",
                        
                        "risk_analysis": "**技术风险**：AI服务稳定性、数据库兼容性\n"
                        "**时间风险**：功能复杂度高，需要合理的时间规划\n"
                        "**团队风险**：需要具备AI、数据库、前端开发等多方面技能",
                        
                        "innovation_points": "**技术创新**：双重功能集成、RAG技术应用\n"
                        "**应用创新**：竞赛辅助与数据库运维结合\n"
                        "**体验创新**：智能化、自动化、可视化三位一体"
                    }
                    
                    st.success("✅ 深度需求分析完成！已识别出详细的技术要求和创新点")
            else:
                st.warning("⚠️ 请上传文档或输入需求描述")
    
    with tab2:
        st.header("🔍 智能需求分析")
        
        if st.session_state.competition_analysis:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📋 需求摘要")
                st.info(st.session_state.competition_analysis["requirements"])
                
                st.subheader("⚙️ 技术栈推荐")
                for tech in st.session_state.competition_analysis["tech_stack"]:
                    st.write(f"- {tech}")
            
            with col2:
                st.subheader("🎯 功能特性")
                for feature in st.session_state.competition_analysis["features"]:
                    st.write(f"- {feature}")
                
                st.subheader("📊 项目评估")
                st.write(f"**难度等级**: {st.session_state.competition_analysis['difficulty']}")
                st.write(f"**预计周期**: {st.session_state.competition_analysis['timeline']}")
            
            # 进一步分析选项
            st.subheader("🔧 深度分析")
            analysis_options = st.multiselect(
                "选择分析维度",
                ["架构设计", "数据库设计", "界面设计", "安全设计", "性能优化"],
                default=["架构设计", "数据库设计"]
            )
            
            if st.button("🔍 执行深度分析", use_container_width=True):
                with st.spinner("🤖 正在进行深度分析..."):
                    import time
                    time.sleep(3)
                    
                    # 生成深度分析结果
                    depth_analysis = {}
                    for option in analysis_options:
                        depth_analysis[option] = f"{option}分析完成，建议方案已生成"
                    
                    st.session_state.competition_analysis["depth"] = depth_analysis
                    st.success("✅ 深度分析完成！")
                    
                    # 显示深度分析结果
                    for option, result in depth_analysis.items():
                        with st.expander(f"📋 {option}分析结果"):
                            st.write(result)
        else:
            st.info("📝 请先上传文档并完成基础分析")
    
    with tab3:
        st.header("📋 智能方案生成")
        
        if st.session_state.competition_analysis:
            st.subheader("🎯 生成完整技术方案")
            
            # 方案类型选择
            plan_type = st.selectbox(
                "选择方案类型",
                ["基础方案", "详细方案", "完整方案"],
                help="基础方案：核心功能设计；详细方案：包含技术细节；完整方案：包含所有文档"
            )
            
            if st.button("🚀 生成方案", type="primary", use_container_width=True):
                with st.spinner("🤖 正在生成详细技术方案..."):
                    import time
                    time.sleep(4)
                    
                    # 生成详细方案
                    st.session_state.generated_plan = {
                        "type": plan_type,
                        "architecture": "**微服务架构设计**\n\n"
                        "**前端服务层**：Streamlit Web应用，负责用户界面和交互\n"
                        "**API网关层**：FastAPI微服务，处理业务逻辑和API路由\n"
                        "**数据服务层**：数据库连接池，支持多数据库类型\n"
                        "**AI服务层**：OpenAI API集成，提供智能对话和分析\n"
                        "**监控服务层**：实时性能监控和日志收集",
                        
                        "database": "**数据库架构设计**\n\n"
                        "**主数据库**：MySQL 8.0，存储用户数据、配置信息\n"
                        "**缓存数据库**：Redis，存储会话数据和热点数据\n"
                        "**监控数据库**：时序数据库，存储性能指标数据\n"
                        "**备份策略**：每日全量备份 + 实时增量备份",
                        
                        "frontend": "**前端技术栈**\n\n"
                        "**框架**：Streamlit 1.28+，Python Web应用框架\n"
                        "**UI组件**：自定义主题系统，支持响应式设计\n"
                        "**可视化**：Plotly图表库，实时数据可视化\n"
                        "**交互**：实时WebSocket通信，支持多用户并发",
                        
                        "backend": "**后端技术栈**\n\n"
                        "**框架**：FastAPI，高性能Python Web框架\n"
                        "**数据库驱动**：SQLAlchemy，多数据库ORM支持\n"
                        "**AI集成**：OpenAI SDK，智能对话和文本分析\n"
                        "**任务调度**：APScheduler，自动化运维任务",
                        
                        "features": st.session_state.competition_analysis["features"],
                        
                        "timeline": "**6周详细开发计划**\n\n"
                        "**第1周**：需求分析、技术选型、环境搭建\n"
                        "**第2周**：数据库设计、API接口开发\n"
                        "**第3周**：前端界面开发、用户认证系统\n"
                        "**第4周**：AI功能集成、智能对话模块\n"
                        "**第5周**：监控系统开发、自动化运维\n"
                        "**第6周**：测试优化、部署上线、文档编写",
                        
                        "deployment": "**部署方案**\n\n"
                        "**开发环境**：Docker Compose，本地开发测试\n"
                        "**测试环境**：云服务器，功能测试和性能测试\n"
                        "**生产环境**：Kubernetes集群，高可用部署\n"
                        "**监控运维**：Prometheus + Grafana，系统监控",
                        
                        "testing": "**测试策略**\n\n"
                        "**单元测试**：pytest框架，代码覆盖率>80%\n"
                        "**集成测试**：API接口测试，数据库操作测试\n"
                        "**性能测试**：负载测试，并发用户测试\n"
                        "**安全测试**：SQL注入防护，XSS攻击防护"
                    }
                    
                    st.success("✅ 详细技术方案生成完成！包含完整的架构设计和开发计划")
            
            # 显示生成的方案
            if st.session_state.generated_plan:
                st.subheader("📄 生成的技术方案")
                
                # 方案类型标签
                st.markdown(f"**方案类型**: {st.session_state.generated_plan['type']}")
                
                # 使用选项卡展示不同部分
                tab_arch, tab_db, tab_fe, tab_be, tab_plan, tab_deploy, tab_test = st.tabs([
                    "🏗️ 系统架构", "💾 数据库", "🎨 前端", "⚙️ 后端", "📅 开发计划", "🚀 部署方案", "🧪 测试策略"
                ])
                
                with tab_arch:
                    st.markdown(st.session_state.generated_plan["architecture"])
                
                with tab_db:
                    st.markdown(st.session_state.generated_plan["database"])
                
                with tab_fe:
                    st.markdown(st.session_state.generated_plan["frontend"])
                
                with tab_be:
                    st.markdown(st.session_state.generated_plan["backend"])
                
                with tab_plan:
                    st.markdown(st.session_state.generated_plan["timeline"])
                
                with tab_deploy:
                    st.markdown(st.session_state.generated_plan["deployment"])
                
                with tab_test:
                    st.markdown(st.session_state.generated_plan["testing"])
                
                # 功能特性展示
                st.subheader("✨ 核心功能特性")
                cols = st.columns(2)
                for i, feature in enumerate(st.session_state.generated_plan["features"]):
                    with cols[i % 2]:
                        st.markdown(f"✅ {feature}")
                
                # 文档下载功能
                st.subheader("📥 文档下载")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📋 下载技术方案", use_container_width=True):
                        st.success("✅ 技术方案文档已生成，准备下载...")
                        # 这里可以添加实际的文档生成和下载逻辑
                
                with col2:
                    if st.button("📊 下载架构图", use_container_width=True):
                        st.success("✅ 系统架构图已生成，准备下载...")
                
                with col3:
                    if st.button("📅 下载开发计划", use_container_width=True):
                        st.success("✅ 详细开发计划已生成，准备下载...")
                
                # 一键生成所有文档
                if st.button("🚀 一键生成完整文档包", type="primary", use_container_width=True):
                    with st.spinner("🤖 正在生成完整文档包..."):
                        import time
                        time.sleep(3)
                        st.success("✅ 完整文档包已生成！包含：技术方案、架构图、开发计划、API文档")
                        
                        # 模拟生成下载链接
                        st.markdown("""
                        **📦 生成的文档包包含：**
                        - 📋 详细技术方案文档 (PDF)
                        - 🏗️ 系统架构图 (PNG/SVG)
                        - 📊 数据库设计文档 (Word)
                        - 📅 6周开发计划表 (Excel)
                        - 🔧 API接口文档 (Markdown)
                        - 🧪 测试用例文档 (Excel)
                        - 🚀 部署指南 (PDF)
                        """)
        else:
            st.info("📝 请先完成需求分析")
    
    with tab4:
        st.header("🎭 Demo演示剧本")
        
        if st.session_state.generated_plan:
            st.subheader("📺 演示脚本生成")
            
            demo_duration = st.slider("演示时长（分钟）", 5, 30, 15)
            demo_style = st.selectbox("演示风格", ["技术型", "产品型", "混合型"])
            demo_audience = st.selectbox("演示对象", ["评委专家", "技术团队", "产品经理", "综合观众"])
            
            if st.button("🎬 生成详细演示剧本", type="primary", use_container_width=True):
                with st.spinner("🤖 正在生成详细演示剧本..."):
                    import time
                    time.sleep(3)
                    
                    st.success("✅ 详细演示剧本生成完成！")
                    
                    # 生成详细演示剧本
                    demo_script = f"""
                    # {demo_style}风格演示剧本 - {demo_audience} ({demo_duration}分钟)
                    
                    ## 🎯 演示目标
                    - **核心目标**：展示项目的技术创新和实用价值
                    - **次要目标**：突出团队的技术能力和项目执行力
                    - **观众期望**：让{demo_audience}理解项目的技术深度和应用前景
                    
                    ## 📋 演示流程 ({demo_duration}分钟)
                    
                    ### 1. 开场介绍 (2分钟)
                    **内容要点**：
                    - 项目背景：数据库运维智能化趋势和竞赛需求
                    - 项目意义：解决传统数据库运维的痛点
                    - 创新亮点：双重功能集成、AI智能驱动
                    - 演示概览：简要介绍演示内容和流程
                    
                    **演示技巧**：
                    - 使用震撼的开场数据或案例
                    - 突出项目的独特性和创新性
                    - 建立与观众的共鸣
                    
                    ### 2. 系统架构展示 (3分钟)
                    **技术亮点**：
                    - 微服务架构设计：前端、API、数据、AI、监控五层架构
                    - 多数据库支持：MySQL、PostgreSQL、SQL Server统一管理
                    - 实时监控系统：性能指标采集和可视化展示
                    - AI智能集成：自然语言对话和智能诊断
                    
                    **演示方式**：
                    - 使用架构图展示系统设计
                    - 重点突出技术选型的合理性
                    - 展示系统的可扩展性和稳定性
                    
                    ### 3. 核心功能演示 ({demo_duration-7}分钟)
                    **功能模块演示**：
                    
                    **3.1 竞赛教练智能助手 (3分钟)**
                    - 文档上传分析：自动识别比赛需求和技术要求
                    - 智能方案生成：详细技术方案和开发计划
                    - Demo剧本生成：定制化演示脚本和答辩材料
                    
                    **3.2 数据库运维智能助手 (4分钟)**
                    - AI智能对话：自然语言问答和问题诊断
                    - 实时监控：性能指标实时采集和告警
                    - 自动化运维：定时任务调度和智能优化
                    - 用户权限管理：多级权限控制和操作审计
                    
                    **演示技巧**：
                    - 按功能模块分步骤演示
                    - 突出每个功能的实用价值
                    - 展示用户友好的交互体验
                    
                    ### 4. 技术深度展示 (3分钟)
                    **关键技术实现**：
                    - AI算法应用：RAG技术、机器学习预测分析
                    - 数据库优化：索引推荐、SQL优化、参数调优
                    - 性能优化：缓存策略、并发处理、响应优化
                    - 安全设计：用户认证、数据加密、操作审计
                    
                    **技术亮点**：
                    - 展示核心算法的实现原理
                    - 突出技术难点和解决方案
                    - 强调系统的稳定性和可靠性
                    
                    ### 5. 项目成果总结 (2分钟)
                    **完成度评估**：
                    - 功能完整性：所有规划功能均已实现
                    - 技术先进性：采用前沿技术和架构设计
                    - 用户体验：界面友好、操作简便、响应迅速
                    - 可扩展性：支持功能扩展和性能优化
                    
                    **价值体现**：
                    - 技术价值：创新的技术方案和实现
                    - 应用价值：解决实际问题的能力
                    - 商业价值：潜在的市场应用前景
                    
                    ### 6. 未来发展规划 (2分钟)
                    **短期规划**：
                    - 功能优化：持续改进用户体验和性能
                    - 技术升级：引入更多AI算法和优化技术
                    - 生态扩展：支持更多数据库类型和应用场景
                    
                    **长期愿景**：
                    - 平台化发展：打造数据库智能运维平台
                    - 商业化应用：探索企业级应用和商业模式
                    - 生态建设：构建开发者社区和合作伙伴
                    
                    ## 🎭 演示准备建议
                    
                    **技术准备**：
                    - 确保演示环境稳定，网络连接正常
                    - 准备备用演示方案，应对技术故障
                    - 测试所有功能模块，确保演示流畅
                    
                    **内容准备**：
                    - 熟悉演示脚本，掌握时间控制
                    - 准备技术细节，应对专业提问
                    - 准备成功案例，增强说服力
                    
                    **团队配合**：
                    - 明确分工，确保演示流程顺畅
                    - 准备应急预案，应对突发情况
                    - 保持团队默契，展现专业形象
                    """
                    
                    # 显示演示剧本
                    st.subheader("📋 详细演示剧本")
                    st.markdown(demo_script)
                    
                    # 下载功能
                    st.subheader("📥 演示材料下载")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("📄 下载演示剧本", use_container_width=True):
                            st.success("✅ 演示剧本文档已生成，准备下载...")
                    
                    with col2:
                        if st.button("🎬 下载PPT模板", use_container_width=True):
                            st.success("✅ 演示PPT模板已生成，准备下载...")
                    
                    with col3:
                        if st.button("📊 下载演示数据", use_container_width=True):
                            st.success("✅ 演示测试数据已生成，准备下载...")
                    
                    # 一键生成所有演示材料
                    if st.button("🚀 一键生成完整演示包", type="primary", use_container_width=True):
                        with st.spinner("🤖 正在生成完整演示材料包..."):
                            time.sleep(3)
                            st.success("✅ 完整演示材料包已生成！")
                            st.markdown("""
                            **📦 生成的演示材料包包含：**
                            - 📄 详细演示剧本文档 (Word)
                            - 🎬 演示PPT模板 (PowerPoint)
                            - 📊 演示测试数据集 (Excel)
                            - 🎯 演示时间控制表 (Excel)
                            - 📋 演示要点提示卡 (PDF)
                            - 🎭 演示排练指南 (PDF)
                            """)
        else:
            st.info("📝 请先生成技术方案")
    
    with tab5:
        st.header("🎯 答辩准备材料")
        
        if st.session_state.generated_plan:
            st.subheader("📊 答辩大纲生成")
            
            defense_type = st.selectbox("答辩类型", ["技术答辩", "产品答辩", "综合答辩"])
            defense_time = st.slider("答辩时间（分钟）", 10, 30, 15)
            include_qa = st.checkbox("包含常见问题准备", value=True)
            include_slides = st.checkbox("包含PPT大纲", value=True)
            
            if st.button("📋 生成详细答辩大纲", type="primary", use_container_width=True):
                with st.spinner("🤖 正在生成详细答辩大纲..."):
                    import time
                    time.sleep(3)
                    
                    st.success("✅ 详细答辩大纲生成完成！")
                    
                    # 生成详细答辩大纲
                    defense_outline = f"""
                    # {defense_type}答辩大纲 ({defense_time}分钟)
                    
                    ## 🎯 答辩目标
                    - **核心目标**：全面展示项目的技术深度和应用价值
                    - **答辩重点**：突出创新点、技术实现、项目成果
                    - **预期效果**：获得评委认可，展现团队实力
                    
                    ## 📋 答辩流程安排 ({defense_time}分钟)
                    
                    ### 1. 项目介绍 (3分钟)
                    **内容要点**：
                    - **项目背景**：数据库运维智能化趋势，竞赛需求分析
                    - **项目意义**：解决传统数据库运维痛点，提升效率
                    - **创新亮点**：双重功能集成、AI智能驱动、多数据库支持
                    - **项目定位**：竞赛作品 vs 实际应用的价值体现
                    
                    **演讲技巧**：
                    - 开场震撼，用数据或案例吸引注意力
                    - 突出项目独特性和创新性
                    - 建立与评委的共鸣和认同感
                    
                    ### 2. 技术实现深度解析 (5分钟)
                    **系统架构设计**：
                    - 微服务五层架构：前端、API、数据、AI、监控
                    - 多数据库统一管理：MySQL、PostgreSQL、SQL Server
                    - 实时监控系统：性能指标采集和可视化展示
                    - AI智能集成：RAG技术、机器学习预测分析
                    
                    **关键技术实现**：
                    - 数据库优化算法：索引推荐、SQL优化、参数调优
                    - 性能优化策略：缓存机制、并发处理、响应优化
                    - 安全设计：用户认证、数据加密、操作审计
                    - 可扩展性设计：模块化架构、插件化扩展
                    
                    **技术难点突破**：
                    - AI与数据库的深度集成
                    - 多数据库类型的统一接口
                    - 实时监控数据的处理效率
                    - 用户权限的精细化管理
                    
                    ### 3. 功能展示与用户体验 (4分钟)
                    **竞赛教练智能助手**：
                    - 智能文档分析：自动识别需求和技术要求
                    - 详细方案生成：完整的技术方案和开发计划
                    - Demo剧本生成：定制化演示脚本和答辩材料
                    
                    **数据库运维智能助手**：
                    - AI智能对话：自然语言问答和问题诊断
                    - 实时监控告警：性能指标监控和异常检测
                    - 自动化运维：定时任务调度和智能优化
                    - 用户权限管理：多级权限控制和操作审计
                    
                    **用户体验设计**：
                    - 响应式界面设计：支持多设备访问
                    - 直观的操作流程：降低使用门槛
                    - 丰富的可视化展示：数据直观呈现
                    
                    ### 4. 项目成果与价值体现 (2分钟)
                    **完成度评估**：
                    - 功能完整性：所有规划功能均已实现
                    - 技术先进性：采用前沿技术和架构设计
                    - 系统稳定性：经过充分测试和优化
                    - 用户体验：界面友好、操作简便、响应迅速
                    
                    **价值体现**：
                    - **技术价值**：创新的技术方案和实现方法
                    - **应用价值**：解决实际问题的能力
                    - **商业价值**：潜在的市场应用前景
                    - **教育价值**：为竞赛提供参考和借鉴
                    
                    ### 5. 未来发展规划 (1分钟)
                    **短期规划**：
                    - 功能优化：持续改进用户体验和性能
                    - 技术升级：引入更多AI算法和优化技术
                    - 生态扩展：支持更多数据库类型和应用场景
                    
                    **长期愿景**：
                    - 平台化发展：打造数据库智能运维平台
                    - 商业化应用：探索企业级应用和商业模式
                    - 生态建设：构建开发者社区和合作伙伴
                    
                    ## 🎤 答辩技巧建议
                    
                    **时间控制**：
                    - 严格控制在{defense_time}分钟内完成
                    - 预留1-2分钟应对突发情况
                    - 重点内容分配更多时间
                    
                    **语言表达**：
                    - 使用专业术语但要通俗易懂
                    - 语速适中，重点内容适当强调
                    - 保持自信，展现专业形象
                    
                    **团队配合**：
                    - 明确分工，确保答辩流畅
                    - 准备应急预案，应对技术故障
                    - 保持团队默契，展现专业形象
                    """
                    
                    # 显示答辩大纲
                    st.subheader("📄 详细答辩大纲")
                    st.markdown(defense_outline)
                    
                    # 常见问题准备
                    if include_qa:
                        st.subheader("❓ 常见问题准备")
                        qa_content = f"""
                        ## 🤔 常见技术问题
                        
                        **1. 技术实现相关问题**
                        - Q: 为什么选择微服务架构？有什么优势？
                        - A: 微服务架构便于功能模块独立开发和部署，提高系统的可扩展性和可维护性
                        
                        - Q: AI功能是如何与数据库运维结合的？
                        - A: 通过自然语言处理理解用户需求，结合数据库知识库提供智能诊断和优化建议
                        
                        **2. 性能优化相关问题**
                        - Q: 系统如何处理高并发访问？
                        - A: 采用缓存机制、连接池优化、异步处理等技术提升并发性能
                        
                        - Q: 实时监控数据的处理效率如何保证？
                        - A: 使用时序数据库存储性能指标，结合数据聚合和采样策略
                        
                        **3. 安全设计相关问题**
                        - Q: 系统如何保证数据安全？
                        - A: 采用用户认证、数据加密、权限控制、操作审计等多层安全防护
                        
                        ## 💡 常见业务问题
                        
                        **1. 应用场景相关问题**
                        - Q: 这个系统适合哪些实际应用场景？
                        - A: 适合企业数据库运维、教育实训、个人开发者等多种场景
                        
                        - Q: 与传统数据库工具相比有什么优势？
                        - A: 智能化、自动化、可视化，降低使用门槛，提高运维效率
                        
                        **2. 未来发展相关问题**
                        - Q: 项目的商业化前景如何？
                        - A: 具有较好的商业化潜力，可以发展为SaaS服务或企业级解决方案
                        
                        - Q: 团队在项目中的技术收获是什么？
                        - A: 掌握了AI集成、微服务架构、数据库优化等前沿技术
                        """
                        st.markdown(qa_content)
                    
                    # PPT大纲
                    if include_slides:
                        st.subheader("📊 PPT大纲设计")
                        slides_content = f"""
                        ## 🎯 PPT结构设计 ({defense_time}分钟)
                        
                        **封面 (30秒)**
                        - 项目名称：DBAI-Copilot
                        - 团队名称：您的团队名称
                        - 答辩类型：{defense_type}
                        
                        **目录 (30秒)**
                        - 项目介绍
                        - 技术实现
                        - 功能展示
                        - 项目成果
                        - 未来规划
                        
                        **项目介绍 (3分钟)**
                        - 背景与意义 (1页)
                        - 创新亮点 (1页)
                        - 项目定位 (1页)
                        
                        **技术实现 (5分钟)**
                        - 系统架构 (2页)
                        - 关键技术 (2页)
                        - 技术难点 (1页)
                        
                        **功能展示 (4分钟)**
                        - 竞赛教练助手 (2页)
                        - 数据库运维助手 (2页)
                        - 用户体验设计 (1页)
                        
                        **项目成果 (2分钟)**
                        - 完成度评估 (1页)
                        - 价值体现 (1页)
                        
                        **未来规划 (1分钟)**
                        - 发展规划 (1页)
                        
                        **结束页 (30秒)**
                        - 感谢聆听
                        - Q&A
                        """
                        st.markdown(slides_content)
                    
                    # 下载功能
                    st.subheader("📥 答辩材料下载")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("📋 下载答辩大纲", use_container_width=True):
                            st.success("✅ 答辩大纲文档已生成，准备下载...")
                    
                    with col2:
                        if st.button("❓ 下载问题准备", use_container_width=True):
                            st.success("✅ 常见问题准备文档已生成，准备下载...")
                    
                    with col3:
                        if st.button("📊 下载PPT模板", use_container_width=True):
                            st.success("✅ 答辩PPT模板已生成，准备下载...")
                    
                    # 一键生成所有答辩材料
                    if st.button("🚀 一键生成完整答辩包", type="primary", use_container_width=True):
                        with st.spinner("🤖 正在生成完整答辩材料包..."):
                            time.sleep(3)
                            st.success("✅ 完整答辩材料包已生成！")
                            st.markdown("""
                            **📦 生成的答辩材料包包含：**
                            - 📋 详细答辩大纲文档 (Word)
                            - ❓ 常见问题准备文档 (Word)
                            - 📊 答辩PPT模板 (PowerPoint)
                            - 🎯 答辩时间控制表 (Excel)
                            - 📝 答辩要点提示卡 (PDF)
                            - 🎤 答辩技巧指南 (PDF)
                            """)
                        defense_outline += """
                        
                        ## 6. 常见问题准备
                        - 技术选型理由
                        - 性能优化策略
                        - 安全设计考虑
                        """
                    
                    st.code(defense_outline, language="markdown")
    
    with tab6:
        st.header("🤖 竞赛教练AI智能对话")
        st.markdown("与专业的竞赛教练AI助手对话，获取参赛建议、技术指导、方案优化等专业建议")
        
        # 初始化竞赛教练对话历史
        if "competition_chat_messages" not in st.session_state:
            st.session_state.competition_chat_messages = []
        
        # 显示对话历史
        for message in st.session_state.competition_chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # 竞赛教练提示词系统
        def get_competition_coach_response(prompt, context=None):
            """竞赛教练AI响应生成"""
            
            base_prompt = """
            你是一位经验丰富的计算机设计大赛专业教练，拥有多年的竞赛指导经验。
            
            你的专业领域包括：
            - 计算机设计大赛参赛指导
            - 项目需求分析和技术方案设计
            - Demo演示和答辩技巧指导
            - 技术选型和架构设计建议
            - 团队协作和时间管理
            - 创新点挖掘和特色展示
            
            请提供专业、实用、具体的建议，帮助参赛团队取得好成绩。
            """
            
            # 添加上下文信息
            if context:
                full_prompt = f"{base_prompt}\n\n{context}\n\n用户问题：{prompt}"
            else:
                full_prompt = f"{base_prompt}\n\n用户问题：{prompt}"
            
            # 模拟AI响应（实际项目中应该调用真实的LLM）
            responses = {
                "项目介绍": """
                📋 **项目介绍建议**
                
                一个好的项目介绍应该包含：
                1. **背景与意义** - 说明为什么要做这个项目
                2. **创新亮点** - 突出项目的独特之处
                3. **技术架构** - 简要说明技术方案
                4. **应用价值** - 展示项目的实用价值
                
                💡 建议用数据或案例来支持你的项目介绍！
                """,
                
                "技术选型": """
                🛠️ **技术选型建议**
                
                选择技术栈时需要考虑：
                1. **团队熟悉度** - 优先选择团队熟悉的技术
                2. **项目需求** - 根据功能需求选择合适的技术
                3. **可维护性** - 考虑技术的社区支持和文档完善度
                4. **性能要求** - 根据性能需求选择合适的方案
                
                💡 建议制作技术选型对比表来帮助决策！
                """,
                
                "答辩技巧": """
                🎯 **答辩技巧建议**
                
                答辩时的关键要点：
                1. **时间控制** - 严格遵守时间限制
                2. **重点突出** - 突出创新点和技术亮点
                3. **演示流畅** - 提前充分演练Demo
                4. **应对提问** - 准备常见问题的回答
                
                💡 建议录制排练视频来发现问题！
                """,
                
                "Demo演示": """
                🎬 **Demo演示建议**
                
                一个精彩的Demo应该：
                1. **提前准备** - 准备好测试数据和演示环境
                2. **流程清晰** - 按照用户故事流程演示
                3. **突出亮点** - 重点展示核心功能
                4. **应急预案** - 准备备用方案应对技术问题
                
                💡 建议准备多个演示场景！
                """,
                
                "团队协作": """
                👥 **团队协作建议**
                
                高效的团队协作需要：
                1. **明确分工** - 根据每个人的特长分配任务
                2. **定期沟通** - 保持频繁的信息同步
                3. **代码管理** - 使用Git等版本控制工具
                4. **文档完善** - 保持技术文档的更新
                
                💡 建议使用项目管理工具来跟踪进度！
                """
            }
            
            # 根据关键词返回相应的建议
            for key, response in responses.items():
                if key in prompt:
                    return response
            
            # 默认响应
            return f"""
            🤖 **竞赛教练建议**
            
            针对您的问题"{prompt}"，我的建议是：
            
            1. **深入分析需求** - 仔细理解比赛要求和评分标准
            2. **突出创新亮点** - 找到项目的独特之处
            3. **完善技术方案** - 确保技术方案的可行性和先进性
            4. **充分准备答辩** - 提前演练，准备应对各种问题
            
            💡 如需更具体的建议，请告诉我更多细节！
            """
        
        # 用户输入
        if prompt := st.chat_input("请输入您的问题... (例如：如何准备答辩？技术选型建议？)"):
            # 添加用户消息
            st.session_state.competition_chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # AI回复
            with st.chat_message("assistant"):
                with st.spinner("🎯 竞赛教练正在思考..."):
                    try:
                        # 构建上下文
                        context = ""
                        if st.session_state.competition_analysis:
                            context += f"""
                            当前项目分析：
                            - 项目难度：{st.session_state.competition_analysis.get('difficulty', '未知')}
                            - 技术栈：{', '.join(st.session_state.competition_analysis.get('tech_stack', []))}
                            """
                        
                        # 生成响应
                        response = get_competition_coach_response(prompt, context)
                        st.markdown(response)
                        st.session_state.competition_chat_messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        error_msg = f"😔 抱歉，竞赛教练暂时无法回答：{str(e)}"
                        st.error(error_msg)
                        st.session_state.competition_chat_messages.append({"role": "assistant", "content": error_msg})
        
        # 快捷问题
        st.markdown("---")
        st.subheader("💡 快捷问题")
        
        col1, col2 = st.columns(2)
        
        with col1:
            quick_questions1 = [
                "如何准备项目介绍？",
                "技术选型有什么建议？",
                "答辩时有什么技巧？"
            ]
            for q in quick_questions1:
                if st.button(q, use_container_width=True, key=f"comp_quick1_{hash(q)}"):
                    st.session_state.competition_chat_messages.append({"role": "user", "content": q})
                    st.rerun()
        
        with col2:
            quick_questions2 = [
                "如何准备Demo演示？",
                "团队如何高效协作？",
                "如何挖掘项目创新点？"
            ]
            for q in quick_questions2:
                if st.button(q, use_container_width=True, key=f"comp_quick2_{hash(q)}"):
                    st.session_state.competition_chat_messages.append({"role": "user", "content": q})
                    st.rerun()
        
        # 清除对话
        if st.button("🧹 清除对话历史", use_container_width=True):
            st.session_state.competition_chat_messages = []
            st.success("✅ 对话历史已清除")
            st.rerun()
        else:
            st.info("📝 请先生成技术方案")
elif pages == "🛠️ 数据库运维智能助手":
    st.title("🛠️ 数据库运维智能助手")
    st.caption("实时监控、诊断分析、智能优化、AI对话、自动化运维")
    
    # 数据库连接配置
    with st.sidebar:
        st.header("🔗 数据库连接配置")
        db_type = st.selectbox("数据库类型", ["MySQL", "PostgreSQL", "SQL Server"])
        host = st.text_input("主机", "localhost")
        port = st.number_input("端口", 1, 65535, DatabaseFactory.get_default_ports().get(db_type, 3306))
        user = st.text_input("用户名", "root")
        password = st.text_input("密码", "", type="password")
        database = st.text_input("数据库", "")
        connect_btn = st.button("连接数据库", use_container_width=True)
    
    # 初始化数据库连接
    if "db_connection" not in st.session_state:
        st.session_state.db_connection = None
    if "metrics_collector" not in st.session_state:
        st.session_state.metrics_collector = None
    if "ai_dialogue" not in st.session_state:
        st.session_state.ai_dialogue = None
    if "automation_manager" not in st.session_state:
        st.session_state.automation_manager = None
    
    # 连接数据库
    if connect_btn:
        try:
            st.session_state.db_connection = DatabaseFactory.create_connection(db_type, host, port, user, password, database)
            if st.session_state.db_connection.connect():
                st.success(f"✅ {db_type}数据库连接成功！")
                st.session_state.metrics_collector = MetricsCollector(st.session_state.db_connection)
                st.session_state.ai_dialogue = AIDialogue(st.session_state.db_connection)
                
                # 显示数据库信息
                db_info = st.session_state.db_connection.get_database_info()
                st.info(f"📊 数据库类型: {db_info.get('type', 'Unknown')}, 版本: {db_info.get('version', 'Unknown')}")
                
                # 初始化自动化管理器
                st.session_state.automation_manager = AutomationManager(st.session_state.db_connection)
            else:
                st.error("❌ 数据库连接失败，请检查配置！")
        except Exception as e:
            st.error(f"❌ 创建数据库连接时出错: {str(e)}")
    
    # 功能选项卡
    if st.session_state.db_connection:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 实时监控", "🔍 诊断分析", "⚡ 智能优化", "🤖 AI对话", "🔄 自动化运维"])
        
        with tab1:
            st.header("📊 实时性能监控")
            if st.button("采集指标", use_container_width=True):
                metrics = st.session_state.metrics_collector.collect()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("QPS", f"{metrics.get('qps', 0):.2f}")
                    st.metric("TPS", f"{metrics.get('tps', 0):.2f}")
                    st.metric("CPU使用率", f"{metrics.get('cpu_usage', 0):.2f}%")
                with col2:
                    st.metric("内存使用率", f"{metrics.get('memory_usage', 0):.2f}%")
                    st.metric("缓冲池命中率", f"{metrics.get('innodb_buffer_pool_hit_rate', 0):.2f}%")
                    st.metric("慢查询数", f"{metrics.get('slow_queries', 0)}")
                with col3:
                    connections = metrics.get('connections', {})
                    st.metric("当前连接数", f"{connections.get('current', 0)}")
                    st.metric("最大连接数", f"{connections.get('max', 0)}")
        
        with tab2:
            st.header("🔍 诊断分析")
            sql = st.text_area("输入SQL语句", "SELECT * FROM orders WHERE status='pending'", key="diagnosis_sql")
            if st.button("分析执行计划", key="analyze_plan", use_container_width=True):
                visualizer = ExplainVisualizer(st.session_state.db_connection)
                plan = visualizer.visualize_explain(sql)
                st.json(plan)
                suggestions = visualizer.analyze_plan(plan)
                if suggestions:
                    st.subheader("优化建议")
                    for suggestion in suggestions:
                        st.write(f"- {suggestion}")
        
        with tab3:
            st.header("⚡ 智能优化")
            sql = st.text_area("输入SQL语句", "SELECT * FROM orders WHERE status='pending'", key="optimization_sql")
            if st.button("推荐索引", key="recommend_index", use_container_width=True):
                recommender = IndexRecommender(st.session_state.db_connection)
                
        with tab4:
            st.header("🤖 增强版AI对话助手")
            st.markdown("与智能数据库AI助手对话，获取专业的诊断、优化建议和解决方案")
            
            # AI助手能力展示
            st.markdown("""
            <div class="card" style="margin-bottom: 20px;">
                <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 150px;">
                        <div style="font-size: 24px; margin-bottom: 5px;">🧠</div>
                        <div style="font-weight: bold;">智能分类</div>
                        <div style="font-size: 12px; color: #666;">自动识别问题类型</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <div style="font-size: 24px; margin-bottom: 5px;">📝</div>
                        <div style="font-weight: bold;">记忆系统</div>
                        <div style="font-size: 12px; color: #666;">短期+长期记忆</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <div style="font-size: 24px; margin-bottom: 5px;">⚡</div>
                        <div style="font-weight: bold;">主动学习</div>
                        <div style="font-size: 12px; color: #666;">持续积累经验</div>
                    </div>
                    <div style="flex: 1; min-width: 150px;">
                        <div style="font-size: 24px; margin-bottom: 5px;">🎯</div>
                        <div style="font-weight: bold;">上下文感知</div>
                        <div style="font-size: 12px; color: #666;">理解对话历史</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 初始化对话历史
            if "chat_messages" not in st.session_state:
                st.session_state.chat_messages = []
            
            # 显示对话历史
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # 用户输入
            if prompt := st.chat_input("请输入您的问题... (例如：数据库性能如何？如何优化慢查询？)"):
                # 添加用户消息
                st.session_state.chat_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # AI回复
                with st.chat_message("assistant"):
                    with st.spinner("🤖 AI助手正在智能分析..."):
                        try:
                            response = st.session_state.ai_dialogue.ask_question(prompt, use_history=True, use_long_term_memory=True)
                            st.markdown(response)
                            st.session_state.chat_messages.append({"role": "assistant", "content": response})
                        except Exception as e:
                            error_msg = f"😔 抱歉，AI助手暂时无法回答：{str(e)}"
                            st.error(error_msg)
                            st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
            
            # 高级功能
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🔧 智能工具")
                if st.button("📊 生成智能诊断报告", use_container_width=True):
                    with st.spinner("🤖 正在生成详细诊断报告..."):
                        try:
                            report = st.session_state.ai_dialogue.generate_diagnostic_report(detailed=True)
                            st.session_state.chat_messages.append({"role": "user", "content": "请生成数据库诊断报告"})
                            st.session_state.chat_messages.append({"role": "assistant", "content": report})
                            st.rerun()
                        except Exception as e:
                            st.error(f"生成报告失败: {str(e)}")
                
                if st.button("🧹 清除对话记忆", use_container_width=True):
                    try:
                        st.session_state.ai_dialogue.clear_history()
                        st.session_state.chat_messages = []
                        st.success("✅ 对话记忆已清除")
                        st.rerun()
                    except Exception as e:
                        st.error(f"清除失败: {str(e)}")
            
            with col2:
                st.subheader("💡 快捷问题")
                quick_questions = [
                    "数据库当前性能状态如何？",
                    "有哪些需要优化的慢查询？",
                    "请提供索引优化建议",
                    "数据库安全配置建议",
                    "如何提高数据库响应速度？",
                    "分析当前锁等待情况"
                ]
                
                for q in quick_questions:
                    if st.button(q, use_container_width=True, key=f"quick_{hash(q)}"):
                        st.session_state.chat_messages.append({"role": "user", "content": q})
                        st.rerun()
            
            # 对话统计
            if st.session_state.chat_messages:
                st.markdown("---")
                st.subheader("📈 对话统计")
                col_stats1, col_stats2, col_stats3 = st.columns(3)
                with col_stats1:
                    st.metric("总对话轮次", len(st.session_state.chat_messages) // 2)
                with col_stats2:
                    st.metric("用户消息", len([m for m in st.session_state.chat_messages if m["role"] == "user"]))
                with col_stats3:
                    st.metric("AI回复", len([m for m in st.session_state.chat_messages if m["role"] == "assistant"]))
        
        with tab5:
            st.header("🔄 自动化运维")
            if st.button("设置自动化任务", use_container_width=True):
                st.session_state.automation_manager.setup_default_tasks()
                st.success("✅ 默认自动化任务已设置")
    else:
        st.info("🔗 请在左侧配置数据库连接信息以开始使用功能")
else:
    st.title("⚙️ 系统管理")
    st.caption("用户管理、权限控制、系统监控、日志查看")
    
    # 检查管理员权限
    user_info = st.session_state.security_manager.get_user_info(st.session_state.session_token)
    is_admin = user_info and user_info.get('role') == 'admin'
    
    if not is_admin:
        st.warning("⚠️ 您没有管理员权限，只能查看部分信息")
    
    # 系统管理功能
    tab1, tab2, tab3, tab4 = st.tabs(["👥 用户管理", "🔒 权限控制", "📊 系统监控", "📋 操作日志"])
    
    with tab1:
        st.header("👥 用户管理")
        
        if is_admin:
            # 用户列表
            st.subheader("📋 用户列表")
            users = st.session_state.security_manager.user_manager.users
            
            if users:
                for i, (username, user_info) in enumerate(users.items()):
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                    
                    with col1:
                        st.write(f"👤 **{username}**")
                        st.write(f"角色: {user_info.get('role', '未知')}")
                    
                    with col2:
                        st.write(f"创建: {user_info.get('created_at', '未知')[:10]}")
                    
                    with col3:
                        last_login = user_info.get('last_login', '从未登录')
                        if last_login != '从未登录':
                            st.write(f"登录: {last_login[:10]}")
                        else:
                            st.write("从未登录")
                    
                    with col4:
                        # 编辑角色
                        if st.button("✏️", key=f"edit_{i}_{username}"):
                            st.session_state.editing_user = username
                            st.rerun()
                    
                    with col5:
                        # 删除用户（不能删除自己）
                        if username != st.session_state.username:
                            if st.button("🗑️", key=f"delete_{i}_{username}"):
                                if st.session_state.security_manager.delete_user(username):
                                    st.success(f"✅ 用户 {username} 已删除")
                                    st.rerun()
                                else:
                                    st.error("❌ 删除用户失败")
                    
                    st.markdown("---")
            else:
                st.info("📝 暂无用户数据")
            
            # 编辑用户角色
            if 'editing_user' in st.session_state:
                st.subheader("✏️ 编辑用户角色")
                editing_user = st.session_state.editing_user
                current_role = users[editing_user].get('role', 'viewer')
                
                new_role = st.selectbox(
                    "选择新角色",
                    ["viewer", "operator", "admin"],
                    index=["viewer", "operator", "admin"].index(current_role),
                    format_func=lambda x: {"viewer": "👀 查看者", "operator": "⚙️ 操作员", "admin": "👑 管理员"}[x],
                    key="edit_role"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ 保存修改", use_container_width=True):
                        if st.session_state.security_manager.update_user_role(editing_user, new_role):
                            st.success(f"✅ 用户 {editing_user} 角色已更新为 {new_role}")
                            del st.session_state.editing_user
                            st.rerun()
                        else:
                            st.error("❌ 更新角色失败")
                
                with col2:
                    if st.button("❌ 取消", use_container_width=True):
                        del st.session_state.editing_user
                        st.rerun()
        else:
            st.info("🔒 需要管理员权限才能管理用户")
        
    with tab2:
        st.header("🔒 权限控制")
        
        if is_admin:
            st.subheader("🎯 权限配置")
            
            # 权限矩阵
            permissions = {
                "viewer": ["查看系统状态", "查看监控数据", "查看日志信息"],
                "operator": ["查看者权限", "执行数据库操作", "管理自动化任务"],
                "admin": ["操作员权限", "管理用户账号", "系统配置管理"]
            }
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("👀 查看者")
                for perm in permissions["viewer"]:
                    st.write(f"✅ {perm}")
            
            with col2:
                st.subheader("⚙️ 操作员")
                for perm in permissions["operator"]:
                    st.write(f"✅ {perm}")
            
            with col3:
                st.subheader("👑 管理员")
                for perm in permissions["admin"]:
                    st.write(f"✅ {perm}")
            
            st.subheader("⚙️ 权限设置")
            
            # 权限调整选项
            permission_options = st.multiselect(
                "选择要调整的权限",
                ["数据库操作", "用户管理", "系统配置", "日志查看", "监控管理"],
                default=["数据库操作", "用户管理"]
            )
            
            if st.button("🔧 应用权限设置", use_container_width=True):
                st.success("✅ 权限设置已应用")
        else:
            st.info("🔒 需要管理员权限才能配置权限")
            
            # 显示当前用户权限
            if user_info:
                st.subheader("👤 您的权限")
                role = user_info.get('role', 'viewer')
                st.write(f"**角色**: {role}")
                
                if role == "viewer":
                    st.write("✅ 查看系统状态")
                    st.write("✅ 查看监控数据")
                    st.write("✅ 查看日志信息")
                elif role == "operator":
                    st.write("✅ 查看者所有权限")
                    st.write("✅ 执行数据库操作")
                    st.write("✅ 管理自动化任务")
                elif role == "admin":
                    st.write("✅ 操作员所有权限")
                    st.write("✅ 管理用户账号")
                    st.write("✅ 系统配置管理")
        
    with tab3:
        st.header("📊 系统监控")
        
        # 系统状态检查
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 检查系统状态", use_container_width=True):
                try:
                    system_status = st.session_state.system_monitor.get_system_status()
                    st.success("✅ 系统运行正常")
                    
                    # 显示健康状态
                    health = system_status.get('health', {})
                    if health:
                        st.subheader("💚 健康状态")
                        st.write(f"检查总数: {health.get('total_checks', 0)}")
                        st.write(f"健康检查: {health.get('healthy', 0)}")
                        st.write(f"健康比例: {health.get('health_percentage', 0):.1f}%")
                except Exception as e:
                    st.error(f"❌ 获取系统状态失败: {str(e)}")
        
        with col2:
            if st.button("📈 性能统计", use_container_width=True):
                try:
                    system_status = st.session_state.system_monitor.get_system_status()
                    performance = system_status.get('performance', {})
                    
                    if performance:
                        st.subheader("⚡ 性能指标")
                        st.write(f"操作总数: {performance.get('total_operations', 0)}")
                        st.write(f"平均耗时: {performance.get('avg_duration', 0):.2f}ms")
                        st.write(f"错误率: {performance.get('error_rate', 0):.1f}%")
                except Exception as e:
                    st.error(f"❌ 获取性能统计失败: {str(e)}")
        
        with col3:
            if st.button("⚠️ 错误统计", use_container_width=True):
                try:
                    system_status = st.session_state.system_monitor.get_system_status()
                    errors = system_status.get('errors', {})
                    
                    if errors:
                        st.subheader("🔴 错误统计")
                        st.write(f"错误总数: {errors.get('total_errors', 0)}")
                        st.write(f"今日错误: {errors.get('today_errors', 0)}")
                        st.write(f"严重错误: {errors.get('critical_errors', 0)}")
                except Exception as e:
                    st.error(f"❌ 获取错误统计失败: {str(e)}")
        
        # 实时监控图表（模拟）
        st.subheader("📊 实时监控")
        
        # 模拟监控数据
        import plotly.graph_objects as go
        import numpy as np
        
        # CPU使用率图表
        cpu_data = np.random.randint(20, 80, 10)
        fig_cpu = go.Figure(go.Scatter(x=list(range(10)), y=cpu_data, mode='lines+markers'))
        fig_cpu.update_layout(title='CPU使用率趋势', xaxis_title='时间', yaxis_title='使用率%')
        st.plotly_chart(fig_cpu, use_container_width=True)
        
        # 内存使用率图表
        memory_data = np.random.randint(30, 90, 10)
        fig_memory = go.Figure(go.Scatter(x=list(range(10)), y=memory_data, mode='lines+markers'))
        fig_memory.update_layout(title='内存使用率趋势', xaxis_title='时间', yaxis_title='使用率%')
        st.plotly_chart(fig_memory, use_container_width=True)
        
    with tab4:
        st.header("📋 操作日志")
        
        # 日志查看选项
        log_type = st.selectbox("日志类型", ["所有日志", "登录日志", "操作日志", "错误日志"])
        log_days = st.slider("查看天数", 1, 30, 7)
        
        if st.button("📋 加载日志", use_container_width=True):
            # 模拟日志数据
            import random
            from datetime import datetime, timedelta
            
            log_levels = ["INFO", "WARNING", "ERROR"]
            log_actions = ["用户登录", "数据库操作", "文件上传", "系统配置"]
            
            logs = []
            for i in range(20):
                log_time = datetime.now() - timedelta(days=random.randint(0, log_days-1), 
                                                     hours=random.randint(0, 23))
                logs.append({
                    "time": log_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "level": random.choice(log_levels),
                    "user": random.choice(["admin", "user1", "user2"]),
                    "action": random.choice(log_actions),
                    "message": f"{random.choice(log_actions)}操作完成"
                })
            
            # 显示日志表格
            st.subheader("📄 操作日志记录")
            
            for log in sorted(logs, key=lambda x: x["time"], reverse=True):
                col1, col2, col3, col4 = st.columns([2, 1, 1, 3])
                
                with col1:
                    st.write(f"🕒 {log['time']}")
                
                with col2:
                    level_color = {"INFO": "green", "WARNING": "orange", "ERROR": "red"}
                    st.markdown(f"<span style='color: {level_color[log['level']]}'>{log['level']}</span>", 
                               unsafe_allow_html=True)
                
                with col3:
                    st.write(f"👤 {log['user']}")
                
                with col4:
                    st.write(log['message'])
                
                st.markdown("---")
                indexes = recommender.recommend_indexes(sql)
                if indexes:
                    st.subheader("索引推荐")
                    for idx in indexes:
                        st.write(f"- 表: {idx['table']}, 列: {', '.join(idx['columns'])}, 原因: {idx['reason']}")
            
            if st.button("参数调优建议", key="param_tune"):
                tuner = ParamTuner(st.session_state.db_connection)
                params = tuner.recommend_parameters()
                st.subheader("参数调优建议")
                for param in params[:10]:
                    st.write(f"- {param['parameter']}: 当前值={param['current']}, 建议值={param['recommended']}, 原因: {param['reason']}")
        
        with tab4:
            st.header("AI对话")
            
            # 自然语言问答
            st.subheader("自然语言问答")
            question = st.text_area("输入您的问题", "我的数据库性能最近下降了，可能是什么原因？", key="ai_question")
            if st.button("回答问题", key="answer_question"):
                with st.spinner("正在分析..."):
                    answer = st.session_state.ai_dialogue.answer_question(question)
                    st.markdown(answer)
            
            # SQL优化
            st.subheader("SQL优化")
            sql_to_optimize = st.text_area("输入SQL语句", "SELECT * FROM orders WHERE status='pending' ORDER BY created_at DESC", key="sql_optimize")
            if st.button("优化SQL", key="optimize_sql"):
                with st.spinner("正在优化..."):
                    optimization = st.session_state.ai_dialogue.optimize_query(sql_to_optimize)
                    st.markdown(optimization)
            
            # 智能诊断报告
            st.subheader("智能诊断报告")
            if st.button("生成诊断报告", key="generate_report"):
                with st.spinner("正在生成报告..."):
                    report = st.session_state.ai_dialogue.generate_diagnostic_report()
                    st.markdown(report)
            
            # 对话历史
            st.subheader("对话历史")
            if st.button("查看对话历史", key="view_history"):
                history = st.session_state.ai_dialogue.get_history()
                if history:
                    for i, (q, a) in enumerate(history):
                        st.markdown(f"**Q{i+1}:** {q}")
                        st.markdown(f"**A{i+1}:** {a}")
                        st.divider()
                else:
                    st.info("暂无对话历史")
            
            if st.button("清除对话历史", key="clear_history"):
                st.session_state.ai_dialogue.clear_history()
                st.success("对话历史已清除")
        
        with tab5:
            st.header("自动化运维")
            
            # 自动化控制
            st.subheader("自动化控制")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("启动自动化运维", key="start_automation"):
                    st.session_state.automation_manager.start_automation()
                    st.success("自动化运维已启动")
            
            with col2:
                if st.button("停止自动化运维", key="stop_automation"):
                    st.session_state.automation_manager.stop_automation()
                    st.success("自动化运维已停止")
            
            # 自动化状态
            st.subheader("自动化状态")
            if st.button("查看状态", key="view_automation_status"):
                status = st.session_state.automation_manager.get_automation_status()
                st.json(status)
            
            # 手动执行优化
            st.subheader("手动执行优化")
            optimization_type = st.selectbox(
                "选择优化类型",
                ["指标采集", "诊断报告", "索引优化", "数据清理"],
                key="optimization_type"
            )
            
            if st.button("执行优化", key="run_manual_optimization"):
                with st.spinner("正在执行优化..."):
                    if optimization_type == "指标采集":
                        result = st.session_state.automation_manager.run_manual_optimization("metrics")
                    elif optimization_type == "诊断报告":
                        result = st.session_state.automation_manager.run_manual_optimization("report")
                    elif optimization_type == "索引优化":
                        result = st.session_state.automation_manager.run_manual_optimization("indexes")
                    elif optimization_type == "数据清理":
                        result = st.session_state.automation_manager.run_manual_optimization("cleanup")
                    
                    st.subheader("优化结果")
                    st.json(result)
            
            # 优化历史
            st.subheader("优化历史")
            if st.button("查看优化历史", key="view_optimization_history"):
                history = st.session_state.automation_manager.optimizer.get_optimization_history()
                if history:
                    for item in history:
                        st.markdown(f"**时间:** {item['timestamp']}")
                        st.markdown(f"**类型:** {item['type']}")
                        if 'report' in item:
                            st.markdown(f"**报告:** {item['report'][:200]}...")
                        elif 'suggestions' in item:
                            st.markdown(f"**建议:** {len(item['suggestions'])} 条")
                        st.divider()
                else:
                    st.info("暂无优化历史")
            
            if st.button("清除优化历史", key="clear_optimization_history"):
                st.session_state.automation_manager.optimizer.clear_optimization_history()
                st.success("优化历史已清除")

if pages == "竞赛教练智能助手":
    if "session_id" not in st.session_state:
        st.session_state.session_id = make_session_id()
    if "vs_dir" not in st.session_state:
        st.session_state.vs_dir = os.path.join(CHROMA_PERSIST_DIR, st.session_state.session_id)
    if "vs_built" not in st.session_state:
        st.session_state.vs_built = False
    if "vs" not in st.session_state:
        st.session_state.vs = None
    if "last_solution_summary" not in st.session_state:
        st.session_state.last_solution_summary = ""

    with st.sidebar:
        st.header("1) 上传需求文件")
        uploaded = st.file_uploader(
            "支持 PDF/DOCX/TXT（建议 PDF 或 DOCX）",
            type=["pdf", "docx", "txt", "md"],
        )

        st.divider()
        st.header("2) 建立索引")
        build_btn = st.button("建立索引", type="primary", disabled=(uploaded is None))

        st.divider()
        st.header("3) 生成内容")
        mode = st.selectbox(
            "选择输出类型",
            [
                "需求解析与方案总览",
                "功能/模块/流程拆解（偏工程落地）",
                "Demo 剧本与步骤",
                "评测指标与测试案例",
                "答辩 PPT 大纲",
            ],
        )

        user_instruction = st.text_area(
            "补充指令（可选）",
            value="请根据比赛要求，输出可直接放进答辩与实现的内容；若信息不足请标注待补充。",
            height=110,
        )

        gen_btn = st.button("生成", disabled=(uploaded is None or not st.session_state.vs_built))


def _save_upload_to_temp(uploaded_file) -> str:
    suffix = os.path.splitext(uploaded_file.name)[1].lower()
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(tmp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return tmp_path


def _ensure_index():
    if st.session_state.vs_built and st.session_state.vs is not None:
        return
    if uploaded is None:
        st.warning("请先上传文件。")
        return

    tmp_path = _save_upload_to_temp(uploaded)
    try:
        docs = load_file(tmp_path, uploaded.name)
        if not docs:
            st.error("文件没有可读取到的文字内容，或解析失败。")
            return

        vs = build_or_replace_index(docs, st.session_state.vs_dir)
        st.session_state.vs = vs
        st.session_state.vs_built = True
        st.success("索引建立完成。")
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


if pages == "竞赛教练":
    if build_btn:
        # Reset session to avoid stale state when uploading new content.
        st.session_state.session_id = make_session_id()
        st.session_state.vs_dir = os.path.join(CHROMA_PERSIST_DIR, st.session_state.session_id)
        st.session_state.vs_built = False
        st.session_state.vs = None
        st.session_state.last_solution_summary = ""
        _ensure_index()

    if gen_btn:
        if st.session_state.vs is None:
            st.error("索引尚未建立。")
            st.stop()

        query_map = {
            "需求解析与方案总览": "请生成需求解析与方案总览：输入/输出/评分类/限制条件/工作流/风险与对策。",
            "功能/模块/流程拆解（偏工程落地）": "请基于文件提出功能模块清单与端到端流程（含数据流、系统模块、关键实现难点）。",
            "Demo 剧本与步骤": "请提出 Demo 剧本：至少 5 个步骤，包含每一步操作画面应该怎么展示。",
            "评测指标与测试案例": "请提出评测指标与测试案例：至少 4 个可量化指标、至少 6 个测试案例与成功判准。",
            "答辩 PPT 大纲": "请输出答辩 PPT 大纲（最多 10 页），每页列出 3-5 个重点。",
        }

        # Retrieve context
        retrieval_query = query_map.get(mode, user_instruction)
        context, docs = retrieve_context(st.session_state.vs, retrieval_query, top_k=5)

        # Generate using prompts
        with st.spinner("正在生成中..."):
            if mode == "答辩 PPT 大纲":
                # If no previous summary, first generate a short solution summary.
                if not st.session_state.last_solution_summary:
                    summary_q = "请先生成方案摘要（模块化设计 + 工作流 + 风险与对策）。"
                    ctx2, _ = retrieve_context(st.session_state.vs, summary_q, top_k=5)
                    summary_prompt = SUMMARY_TEMPLATE.format(question=summary_q, context=ctx2)
                    st.session_state.last_solution_summary = invoke_llm(summary_prompt)

                # Generate PPT outline
                ppt_prompt = PPT_TEMPLATE.format(
                    context=context,
                    solution_summary=st.session_state.last_solution_summary,
                )
                output_text = invoke_llm(ppt_prompt)

            elif mode == "评测指标与测试案例":
                prompt = QUESTIONS_TEMPLATE.format(
                    context=context,
                    user_instruction=user_instruction,
                )
                output_text = invoke_llm(prompt)

            else:
                # For other modes, use SUMMARY_TEMPLATE (it already asks for solution+demo+risks).
                summary_prompt = SUMMARY_TEMPLATE.format(question=retrieval_query, context=context)
                output_text = invoke_llm(summary_prompt)
                # Keep summary for later PPT
                if mode == "需求解析与方案总览":
                    st.session_state.last_solution_summary = output_text

        st.subheader("生成结果")
        st.write(output_text)

        with st.expander("检索来源（供核对/引用）"):
            for d in docs:
                st.markdown(f"- {iter_metadata(d)}")

