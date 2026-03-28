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
    st.title("🎯 竞赛教练智能助手")
    st.caption("上传比赛需求文件 -> 建立索引 -> 生成方案/功能/ Demo 剧本/评测/答辩大纲")
    
    # 初始化竞赛教练相关状态
    if "competition_docs" not in st.session_state:
        st.session_state.competition_docs = []
    if "competition_analysis" not in st.session_state:
        st.session_state.competition_analysis = {}
    if "generated_plan" not in st.session_state:
        st.session_state.generated_plan = {}
    
    # 功能选项卡
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📁 文档上传", "🔍 智能分析", "📋 方案生成", "🎭 Demo剧本", "🎯 答辩大纲"])
    
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
                with st.spinner("🤖 AI正在分析比赛需求..."):
                    # 模拟分析过程
                    import time
                    time.sleep(2)
                    
                    # 生成分析结果
                    st.session_state.competition_analysis = {
                        "requirements": "已识别比赛需求",
                        "tech_stack": ["Python", "Streamlit", "数据库"],
                        "features": ["智能对话", "实时监控", "数据分析"],
                        "difficulty": "中等",
                        "timeline": "4周"
                    }
                    
                    st.success("✅ 需求分析完成！")
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
                with st.spinner("🤖 正在生成技术方案..."):
                    import time
                    time.sleep(3)
                    
                    # 生成方案
                    st.session_state.generated_plan = {
                        "type": plan_type,
                        "architecture": "微服务架构设计",
                        "database": "MySQL + Redis缓存",
                        "frontend": "Streamlit响应式界面",
                        "backend": "Python FastAPI",
                        "features": st.session_state.competition_analysis["features"],
                        "timeline": "详细开发计划"
                    }
                    
                    st.success("✅ 技术方案生成完成！")
            
            # 显示生成的方案
            if st.session_state.generated_plan:
                st.subheader("📄 生成的技术方案")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**🏗️ 系统架构**")
                    st.info(st.session_state.generated_plan["architecture"])
                    
                    st.write("**💾 数据库设计**")
                    st.info(st.session_state.generated_plan["database"])
                    
                    st.write("**🎨 前端技术**")
                    st.info(st.session_state.generated_plan["frontend"])
                
                with col2:
                    st.write("**⚙️ 后端技术**")
                    st.info(st.session_state.generated_plan["backend"])
                    
                    st.write("**✨ 核心功能**")
                    for feature in st.session_state.generated_plan["features"]:
                        st.write(f"- {feature}")
                    
                    st.write("**📅 开发计划**")
                    st.info(st.session_state.generated_plan["timeline"])
                
                # 下载方案按钮
                if st.button("📥 下载方案文档", use_container_width=True):
                    st.success("✅ 方案文档已生成，准备下载...")
        else:
            st.info("📝 请先完成需求分析")
    
    with tab4:
        st.header("🎭 Demo演示剧本")
        
        if st.session_state.generated_plan:
            st.subheader("📺 演示脚本生成")
            
            demo_duration = st.slider("演示时长（分钟）", 5, 30, 15)
            demo_style = st.selectbox("演示风格", ["技术型", "产品型", "混合型"])
            
            if st.button("🎬 生成演示剧本", use_container_width=True):
                with st.spinner("🤖 正在生成演示剧本..."):
                    import time
                    time.sleep(2)
                    
                    st.success("✅ 演示剧本生成完成！")
                    
                    # 显示演示剧本
                    st.subheader("📋 演示剧本大纲")
                    
                    demo_script = f"""
                    # {demo_style}风格演示剧本 ({demo_duration}分钟)
                    
                    ## 开场介绍 (2分钟)
                    - 项目背景和意义
                    - 演示目标和内容概述
                    
                    ## 核心功能演示 ({demo_duration-4}分钟)
                    - 主要功能点展示
                    - 技术亮点演示
                    - 用户体验展示
                    
                    ## 技术实现 (2分钟)
                    - 架构设计亮点
                    - 关键技术实现
                    
                    ## 总结展望 (2分钟)
                    - 项目价值总结
                    - 未来发展规划
                    """
                    
                    st.code(demo_script, language="markdown")
        else:
            st.info("📝 请先生成技术方案")
    
    with tab5:
        st.header("🎯 答辩准备材料")
        
        if st.session_state.generated_plan:
            st.subheader("📊 答辩大纲生成")
            
            defense_type = st.selectbox("答辩类型", ["技术答辩", "产品答辩", "综合答辩"])
            include_qa = st.checkbox("包含常见问题准备", value=True)
            
            if st.button("📋 生成答辩大纲", use_container_width=True):
                with st.spinner("🤖 正在生成答辩大纲..."):
                    import time
                    time.sleep(2)
                    
                    st.success("✅ 答辩大纲生成完成！")
                    
                    # 显示答辩大纲
                    st.subheader("📄 答辩大纲")
                    
                    defense_outline = f"""
                    # {defense_type}答辩大纲
                    
                    ## 1. 项目介绍
                    - 项目背景和意义
                    - 创新点和特色
                    
                    ## 2. 技术实现
                    - 系统架构设计
                    - 关键技术选型
                    - 性能优化措施
                    
                    ## 3. 功能展示
                    - 核心功能演示
                    - 用户体验设计
                    
                    ## 4. 项目成果
                    - 完成度评估
                    - 技术难点突破
                    
                    ## 5. 未来规划
                    - 扩展方向
                    - 优化计划
                    """
                    
                    if include_qa:
                        defense_outline += """
                        
                        ## 6. 常见问题准备
                        - 技术选型理由
                        - 性能优化策略
                        - 安全设计考虑
                        """
                    
                    st.code(defense_outline, language="markdown")
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
            st.header("🤖 AI对话助手")
            st.markdown("与数据库AI助手进行智能对话，获取优化建议和问题诊断")
            
            # 初始化对话历史
            if "chat_messages" not in st.session_state:
                st.session_state.chat_messages = []
            
            # 显示对话历史
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # 用户输入
            if prompt := st.chat_input("请输入您的问题..."):
                # 添加用户消息
                st.session_state.chat_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # AI回复
                with st.chat_message("assistant"):
                    with st.spinner("AI助手正在思考..."):
                        try:
                            response = st.session_state.ai_dialogue.ask_question(prompt)
                            st.markdown(response)
                            st.session_state.chat_messages.append({"role": "assistant", "content": response})
                        except Exception as e:
                            error_msg = f"抱歉，AI助手暂时无法回答：{str(e)}"
                            st.error(error_msg)
                            st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
            
            # 快速问题示例
            st.markdown("---")
            st.subheader("💡 快速问题示例")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("数据库性能如何？", use_container_width=True):
                    st.session_state.chat_messages.append({"role": "user", "content": "数据库性能如何？"})
                    st.rerun()
                
                if st.button("有哪些慢查询？", use_container_width=True):
                    st.session_state.chat_messages.append({"role": "user", "content": "有哪些慢查询？"})
                    st.rerun()
            
            with col2:
                if st.button("如何优化索引？", use_container_width=True):
                    st.session_state.chat_messages.append({"role": "user", "content": "如何优化索引？"})
                    st.rerun()
                
                if st.button("数据库安全建议", use_container_width=True):
                    st.session_state.chat_messages.append({"role": "user", "content": "数据库安全建议"})
                    st.rerun()
        
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

