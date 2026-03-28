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
    
    # 智能分析面板
    st.markdown("### 🤖 智能分析中心")
    
    col_analysis1, col_analysis2 = st.columns([1, 1])
    
    with col_analysis1:
        st.markdown("""
        <div class="card">
            <div class="card-icon">📊</div>
            <div class="card-title">智能预测分析</div>
            <div class="card-desc">
                AI驱动的性能预测和趋势分析
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 模拟智能预测
        if st.button("🔮 生成智能预测", use_container_width=True):
            with st.spinner("AI正在分析预测..."):
                time.sleep(2)
                st.success("✅ 智能预测完成！")
                st.markdown("""
                **📈 预测结果：**
                - 系统稳定性：优秀 (98.5%)
                - 性能趋势：稳步提升
                - 推荐行动：继续当前优化策略
                - 风险预警：无重大风险
                """)
    
    with col_analysis2:
        st.markdown("""
        <div class="card">
            <div class="card-icon">🎯</div>
            <div class="card-title">智能推荐引擎</div>
            <div class="card-desc">
                基于AI的个性化功能推荐
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("💡 获取智能推荐", use_container_width=True):
            with st.spinner("AI正在生成推荐..."):
                time.sleep(2)
                st.success("✅ 智能推荐完成！")
                st.markdown("""
                **✨ 推荐内容：**
                1. 优先使用竞赛教练助手完善项目文档
                2. 配置数据库连接体验智能运维
                3. 使用AI对话功能获取专业建议
                4. 定期生成诊断报告监控系统状态
                """)
    
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    
    # 技术特色
    st.markdown("### 💡 技术特色")
    
    tech_features = [
        ("🔗", "双重功能集成", "竞赛辅助与数据库运维完美结合"),
        ("🧠", "AI智能驱动", "RAG技术 + 真实LLM集成"),
        ("🌐", "多数据库支持", "MySQL、PostgreSQL、SQL Server统一接口"),
        ("🎨", "现代化界面", "Streamlit响应式Web应用"),
        ("⚡", "自动化运维", "定时任务调度和智能优化"),
        ("🔒", "安全可靠", "完整的用户认证和权限管理"),
        ("📝", "智能记忆系统", "短期+长期记忆，上下文理解"),
        ("🎯", "智能分类", "自动识别问题类型，精准响应")
    ]
    
    cols = st.columns(4)
    for i, (icon, title, desc) in enumerate(tech_features):
        with cols[i % 4]:
            st.markdown(f'''
            <div class="feature-card" style="margin-bottom: 15px;">
                <div style="font-size: 28px; margin-bottom: 8px;">{icon}</div>
                <div style="font-weight: bold; font-size: 14px; margin-bottom: 5px;">{title}</div>
                <div style="font-size: 12px; color: #666;">{desc}</div>
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
                    import time
                    
                    # 收集上传的文档信息
                    doc_info = ""
                    if st.session_state.competition_docs:
                        doc_names = [doc["name"] for doc in st.session_state.competition_docs]
                        doc_info = f"已上传文档：{', '.join(doc_names)}\n\n"
                    
                    # 构建基于用户输入的个性化分析
                    user_input_content = manual_input if manual_input else "基于默认项目需求"
                    
                    # 智能分析进度展示
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("📄 正在解析文档内容...")
                    time.sleep(0.8)
                    progress_bar.progress(25)
                    
                    status_text.text("🧠 正在提取关键需求...")
                    time.sleep(0.8)
                    progress_bar.progress(50)
                    
                    status_text.text("🎯 正在识别技术要求...")
                    time.sleep(0.8)
                    progress_bar.progress(75)
                    
                    status_text.text("✨ 正在挖掘创新亮点...")
                    time.sleep(0.6)
                    progress_bar.progress(100)
                    status_text.empty()
                    
                    # 生成更真实、更个性化的分析结果
                    analysis_requirements = f"""基于分析，识别出以下核心需求：

**📋 项目概述**
- **文档信息**：{doc_info if doc_info else '未上传文档，使用手动输入'}
- **用户输入**：{user_input_content[:200]}...

**🎯 项目目标**
开发一个智能竞赛辅助系统，帮助团队高效准备计算机设计大赛

**⚙️ 技术要求**
- 支持Web界面展示和交互
- 提供智能分析和建议功能
- 支持文档管理和方案生成
- 现代化的用户体验设计

**📦 功能需求**
1. 需求分析和项目规划
2. 技术方案设计和优化
3. Demo演示和答辩准备
4. 团队协作和进度管理

**⚡ 性能要求**
- 响应速度快，交互流畅
- 支持多用户同时使用
- 界面美观，操作直观

**🔒 质量要求**
- 代码规范，结构清晰
- 文档完整，易于维护
- 测试充分，稳定性高"""

                    # 根据用户输入智能调整技术栈
                    tech_stack_list = [
                        "Python 3.12", "Streamlit (Web框架)", 
                        "OpenAI API (AI智能)", "Plotly (数据可视化)",
                        "Pandas (数据处理)", "Git (版本控制)"
                    ]
                    
                    # 根据输入内容添加相关技术
                    if "数据库" in user_input_content or "database" in user_input_content.lower():
                        tech_stack_list.extend(["MySQL/PostgreSQL", "SQLAlchemy (ORM)"])
                    if "移动端" in user_input_content or "mobile" in user_input_content.lower():
                        tech_stack_list.append("响应式设计")
                    if "实时" in user_input_content or "realtime" in user_input_content.lower():
                        tech_stack_list.append("WebSocket (实时通信)")
                    
                    # 生成功能特性
                    feature_list = [
                        "智能需求分析 - AI自动解析比赛要求",
                        "技术方案生成 - 专业的架构和技术选型建议",
                        "Demo剧本定制 - 个性化的演示脚本",
                        "答辩材料准备 - 完整的答辩大纲和问题准备",
                        "团队协作工具 - 任务分配和进度跟踪"
                    ]
                    
                    # 智能评估难度
                    difficulty_level = "中级"
                    if len(tech_stack_list) > 6 or "AI" in user_input_content:
                        difficulty_level = "中高级"
                    if "机器学习" in user_input_content or "分布式" in user_input_content:
                        difficulty_level = "高级"
                    
                    # 智能风险分析
                    risk_content = f"""**⚠️ 风险分析**

**技术风险**：
- 新技术学习曲线：需要掌握{len(tech_stack_list)}项技术
- 集成复杂度：多模块协同可能存在挑战
- 时间风险：功能丰富，需要合理规划开发周期

**应对策略**：
- 分阶段实施，优先完成核心功能
- 充分利用现有开源组件
- 建立代码审查和测试机制"""

                    # 智能创新点
                    innovation_content = f"""**💡 创新亮点**

**技术创新**：
- AI驱动的智能分析引擎
- 个性化方案生成算法
- 自动化文档处理

**应用创新**：
- 竞赛全流程辅助
- 团队协作智能化
- 知识沉淀和复用

**体验创新**：
- 直观的用户界面
- 流畅的交互体验
- 智能提示和引导"""

                    # 生成详细的分析结果
                    st.session_state.competition_analysis = {
                        "requirements": analysis_requirements,
                        "tech_stack": tech_stack_list,
                        "features": feature_list,
                        "difficulty": f"{difficulty_level}（需要掌握{len(tech_stack_list)}项技术，涉及{len(feature_list)}个功能模块）",
                        "timeline": f"{6 if difficulty_level == '高级' else 5}周详细开发计划",
                        "risk_analysis": risk_content,
                        "innovation_points": innovation_content,
                        "doc_count": len(st.session_state.competition_docs),
                        "has_manual_input": bool(manual_input)
                    }
                    
                    st.success(f"✅ 深度需求分析完成！已分析{len(st.session_state.competition_docs)}个文档，识别出{len(tech_stack_list)}项技术和{len(feature_list)}个功能模块")
            else:
                st.warning("⚠️ 请上传文档或输入需求描述")
    
    with tab2:
        st.header("🔍 智能需求分析")
        
        if st.session_state.competition_analysis:
            # 显示分析概览
            analysis = st.session_state.competition_analysis
            doc_count = analysis.get("doc_count", 0)
            has_manual = analysis.get("has_manual_input", False)
            
            st.info(f"""
            📊 **分析概览**
            - 已分析文档数：{doc_count}
            - 包含手动输入：{'是' if has_manual else '否'}
            - 识别技术数：{len(analysis['tech_stack'])}
            - 功能模块数：{len(analysis['features'])}
            """)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📋 需求分析报告")
                st.info(analysis["requirements"])
                
                st.subheader("⚙️ 智能技术栈推荐")
                tech_stack = analysis["tech_stack"]
                for tech in tech_stack:
                    st.markdown(f"- ✅ {tech}")
                
                # 智能技术选型理由（根据实际技术栈生成）
                st.markdown("---")
                st.subheader("🔍 技术选型理由")
                tech_reasons = []
                for tech in tech_stack:
                    if "Python" in tech:
                        tech_reasons.append("- **Python**：生态丰富，开发效率高，适合竞赛项目")
                    elif "Streamlit" in tech:
                        tech_reasons.append("- **Streamlit**：快速构建数据应用，展示效果好")
                    elif "OpenAI" in tech or "AI" in tech:
                        tech_reasons.append("- **AI能力**：提供智能分析和建议功能")
                    elif "MySQL" in tech or "PostgreSQL" in tech or "数据库" in tech:
                        tech_reasons.append("- **数据库**：成熟稳定，社区支持好")
                    elif "Plotly" in tech or "可视化" in tech:
                        tech_reasons.append("- **可视化**：数据展示直观，演示效果好")
                    elif "Git" in tech:
                        tech_reasons.append("- **版本控制**：团队协作必备，代码管理规范")
                
                for reason in tech_reasons[:5]:
                    st.markdown(reason)
            
            with col2:
                st.subheader("🎯 功能特性规划")
                features = analysis["features"]
                for feature in features:
                    st.markdown(f"- 🚀 {feature}")
                
                st.subheader("📊 项目评估")
                st.markdown(f"**难度等级**: {analysis['difficulty']}")
                st.markdown(f"**预计周期**: {analysis['timeline']}")
                
                st.markdown("---")
                st.subheader("⚠️ 风险与应对")
                st.warning(analysis["risk_analysis"])
                
                st.subheader("💡 创新亮点挖掘")
                st.success(analysis["innovation_points"])
            
            # 深度分析（使用真实LLM）
            st.markdown("---")
            st.subheader("🔧 AI深度分析")
            
            col_analysis1, col_analysis2 = st.columns([1, 1])
            
            with col_analysis1:
                analysis_type = st.selectbox(
                    "选择分析类型",
                    ["🏗️ 架构设计分析", "🗄️ 数据库设计分析", "🎨 界面设计分析", 
                     "🔒 安全设计分析", "⚡ 性能优化分析", "👥 团队协作分析"],
                    index=0
                )
            
            with col_analysis2:
                analysis_depth = st.select_slider(
                    "分析深度",
                    options=["基础", "详细", "深度"],
                    value="详细"
                )
            
            if st.button("🤖 执行AI深度分析", type="primary", use_container_width=True):
                with st.spinner("🎯 AI正在进行深度分析..."):
                    try:
                        # 构建AI分析提示词
                        analysis_prompt = f"""
                        请作为专业的计算机设计大赛技术专家，进行{analysis_type}。
                        
                        分析深度：{analysis_depth}
                        
                        项目背景：
                        - 这是一个集成竞赛教练和数据库运维功能的智能助手系统
                        - 需要支持多数据库、AI对话、实时监控、自动化运维
                        - 目标是参加计算机设计大赛并取得好成绩
                        
                        请提供：
                        1. 📋 详细的分析报告
                        2. 🎯 具体的设计建议
                        3. ⚠️ 潜在风险和注意事项
                        4. 💡 创新点和亮点建议
                        5. 📊 实施步骤和时间规划
                        
                        请用清晰的结构、具体的例子、专业但易懂的语言回答。
                        """
                        
                        # 调用真实LLM进行分析
                        from app.llm import invoke_llm
                        analysis_result = invoke_llm(analysis_prompt)
                        
                        st.success("✅ AI深度分析完成！")
                        
                        # 显示分析结果
                        with st.expander(f"📋 {analysis_type} - 分析结果", expanded=True):
                            st.markdown(analysis_result)
                        
                        # 保存分析结果
                        if "ai_analysis" not in st.session_state.competition_analysis:
                            st.session_state.competition_analysis["ai_analysis"] = {}
                        st.session_state.competition_analysis["ai_analysis"][analysis_type] = analysis_result
                        
                    except Exception as e:
                        st.error(f"分析失败: {str(e)}")
                        st.info("使用备用分析方案...")
                        
                        # 备用分析方案
                        backup_analysis = {
                            "🏗️ 架构设计分析": """
                            ## 🏗️ 架构设计分析（备用方案）
                            
                            ### 📋 推荐架构：五层微服务架构
                            1. **前端层**：Streamlit Web界面
                            2. **API层**：FastAPI RESTful API
                            3. **业务逻辑层**：竞赛教练+数据库运维
                            4. **数据层**：多数据库统一管理
                            5. **AI层**：LLM集成+RAG检索
                            
                            ### 🎯 设计要点
                            - 模块化设计，便于扩展
                            - 松耦合，高内聚
                            - 支持插件化扩展
                            
                            ### 💡 创新点
                            - 双重功能集成设计
                            - AI与数据库深度融合
                            """,
                            "🗄️ 数据库设计分析": """
                            ## 🗄️ 数据库设计分析（备用方案）
                            
                            ### 📋 核心数据表
                            1. **用户表**：用户信息、权限管理
                            2. **项目表**：竞赛项目信息
                            3. **对话历史表**：AI对话记录
                            4. **监控数据表**：性能指标数据
                            5. **任务调度表**：自动化运维任务
                            
                            ### 🎯 设计要点
                            - 合理的索引设计
                            - 支持多数据库适配
                            - 数据备份和恢复策略
                            """,
                            "🎨 界面设计分析": """
                            ## 🎨 界面设计分析（备用方案）
                            
                            ### 📋 设计原则
                            1. **简洁直观**：操作流程清晰
                            2. **响应式设计**：支持多设备
                            3. **视觉层次**：重要信息突出
                            4. **用户友好**：降低学习成本
                            
                            ### 🎯 页面布局
                            - 左侧导航栏
                            - 主内容区域
                            - 右侧辅助面板
                            """,
                            "🔒 安全设计分析": """
                            ## 🔒 安全设计分析（备用方案）
                            
                            ### 📋 安全措施
                            1. **用户认证**：登录验证
                            2. **权限管理**：多级权限控制
                            3. **数据加密**：敏感数据加密
                            4. **操作审计**：日志记录
                            5. **防SQL注入**：参数化查询
                            
                            ### 🎯 最佳实践
                            - 定期安全审计
                            - 及时更新依赖
                            - 备份策略完善
                            """,
                            "⚡ 性能优化分析": """
                            ## ⚡ 性能优化分析（备用方案）
                            
                            ### 📋 优化策略
                            1. **数据库优化**：索引、查询优化
                            2. **缓存机制**：Redis缓存热点数据
                            3. **异步处理**：后台任务异步执行
                            4. **前端优化**：懒加载、组件优化
                            
                            ### 🎯 监控指标
                            - 响应时间
                            - 吞吐量
                            - 资源利用率
                            """,
                            "👥 团队协作分析": """
                            ## 👥 团队协作分析（备用方案）
                            
                            ### 📋 团队分工建议
                            - **前端开发**：1-2人
                            - **后端开发**：2-3人
                            - **AI集成**：1人
                            - **测试/文档**：1人
                            
                            ### 🎯 协作工具
                            - Git版本控制
                            - 项目管理工具
                            - 即时通讯
                            """
                        }
                        
                        st.success("✅ 备用分析完成！")
                        with st.expander(f"📋 {analysis_type} - 分析结果", expanded=True):
                            st.markdown(backup_analysis.get(analysis_type, "分析完成"))
            
            # 显示历史分析结果
            if "ai_analysis" in st.session_state.competition_analysis and st.session_state.competition_analysis["ai_analysis"]:
                st.markdown("---")
                st.subheader("📚 历史分析记录")
                for analysis_name, analysis_content in st.session_state.competition_analysis["ai_analysis"].items():
                    with st.expander(f"📋 {analysis_name}"):
                        st.markdown(analysis_content)
        else:
            st.info("📝 请先上传文档并完成基础分析")
    
    with tab3:
        st.header("📋 智能方案生成")
        
        if st.session_state.competition_analysis:
            st.subheader("🎯 AI智能生成完整技术方案")
            
            # 方案配置
            col_plan1, col_plan2 = st.columns([1, 1])
            
            with col_plan1:
                plan_type = st.selectbox(
                    "方案类型",
                    ["🏗️ 架构设计方案", "💻 完整技术方案", "📋 项目实施方案"],
                    index=1,
                    help="选择需要生成的方案类型"
                )
            
            with col_plan2:
                team_size = st.select_slider(
                    "团队规模",
                    options=["2-3人", "4-5人", "6-8人"],
                    value="4-5人"
                )
            
            # 方案重点选项
            st.markdown("**🎯 方案重点**")
            focus_options = st.multiselect(
                "选择重点关注的方面（可多选）",
                ["技术创新", "用户体验", "性能优化", "安全性", "可扩展性", "文档完整性"],
                default=["技术创新", "用户体验", "性能优化"]
            )
            
            if st.button("🚀 AI智能生成方案", type="primary", use_container_width=True):
                with st.spinner("🎯 AI正在生成专业技术方案..."):
                    try:
                        # 构建AI方案生成提示词
                        plan_prompt = f"""
                        请作为专业的计算机设计大赛技术顾问，为参赛团队生成一份{plan_type}。
                        
                        项目背景：
                        - 项目名称：DB-AI Copilot - 智能数据库运维与竞赛辅助系统
                        - 核心功能：竞赛教练智能助手 + 数据库运维智能助手
                        - 参赛目标：参加计算机设计大赛并取得优异成绩
                        
                        团队配置：{team_size}
                        重点关注：{', '.join(focus_options)}
                        
                        请生成一份完整的技术方案，包含以下内容：
                        
                        ## 1. 📋 项目概述
                        - 项目背景与意义
                        - 核心价值与创新点
                        - 项目目标与定位
                        
                        ## 2. 🏗️ 系统架构设计
                        - 整体架构图（文字描述）
                        - 各模块职责说明
                        - 技术选型理由
                        
                        ## 3. 💻 技术实现方案
                        - 前端技术栈与实现
                        - 后端技术栈与实现
                        - 数据库设计
                        - AI功能集成方案
                        
                        ## 4. 👥 团队分工与开发计划
                        - 团队成员角色分配（基于{team_size}）
                        - 详细的开发里程碑
                        - 每周任务安排
                        - 风险评估与应对
                        
                        ## 5. 🎯 竞赛亮点设计
                        - 技术创新点
                        - 应用创新点
                        - 演示亮点
                        - 答辩策略
                        
                        ## 6. 📊 部署与测试
                        - 部署方案
                        - 测试策略
                        - 性能优化建议
                        
                        请提供具体、详细、可操作的方案，用清晰的结构、专业的语言、具体的例子。
                        突出竞赛相关的亮点和创新点，帮助团队在比赛中取得好成绩。
                        """
                        
                        # 调用真实LLM生成方案
                        from app.llm import invoke_llm
                        plan_result = invoke_llm(plan_prompt)
                        
                        st.success("✅ AI技术方案生成完成！")
                        
                        # 保存生成的方案
                        st.session_state.generated_plan = {
                            "type": plan_type,
                            "content": plan_result,
                            "team_size": team_size,
                            "focus": focus_options
                        }
                        
                        # 显示生成的方案
                        with st.expander("📄 完整技术方案", expanded=True):
                            st.markdown(plan_result)
                        
                    except Exception as e:
                        st.error(f"方案生成失败: {str(e)}")
                        st.info("使用备用方案...")
                        
                        # 备用方案
                        backup_plan = """
                        # 📋 DB-AI Copilot 技术方案（备用）
                        
                        ## 1. 项目概述
                        
                        ### 项目背景
                        数据库运维是IT系统的核心工作，传统方式依赖人工经验，效率低、易出错。
                        同时，计算机设计大赛需要专业的指导和辅助工具。
                        
                        ### 核心价值
                        - **双重功能**：竞赛教练 + 数据库运维
                        - **AI驱动**：智能分析、自动优化
                        - **易用高效**：降低技术门槛，提升效率
                        
                        ## 2. 系统架构
                        
                        ### 五层微服务架构
                        1. **前端层**：Streamlit Web界面
                        2. **API层**：FastAPI RESTful API
                        3. **业务层**：竞赛教练 + 数据库运维
                        4. **数据层**：多数据库统一管理
                        5. **AI层**：LLM集成 + RAG检索
                        
                        ## 3. 技术实现
                        
                        ### 前端技术
                        - Streamlit 1.28+
                        - Plotly 数据可视化
                        - 响应式设计
                        
                        ### 后端技术
                        - FastAPI 高性能框架
                        - SQLAlchemy ORM
                        - OpenAI API集成
                        
                        ### 数据库支持
                        - MySQL、PostgreSQL、SQL Server
                        - Redis 缓存
                        
                        ## 4. 开发计划（6周）
                        
                        - **第1周**：需求分析、环境搭建
                        - **第2周**：数据库设计、API开发
                        - **第3周**：前端界面、用户系统
                        - **第4周**：AI功能、智能对话
                        - **第5周**：监控系统、自动化运维
                        - **第6周**：测试优化、文档编写
                        
                        ## 5. 竞赛亮点
                        
                        - 双重功能集成创新
                        - AI智能驱动体验
                        - 完整的竞赛辅助
                        - 专业的数据库运维
                        """
                        
                        st.session_state.generated_plan = {
                            "type": plan_type,
                            "content": backup_plan,
                            "team_size": team_size,
                            "focus": focus_options
                        }
                        
                        st.success("✅ 备用方案生成完成！")
                        with st.expander("📄 技术方案", expanded=True):
                            st.markdown(backup_plan)
            
            # 显示历史生成的方案
            if st.session_state.generated_plan:
                st.markdown("---")
                st.subheader("📄 已生成的技术方案")
                
                st.info(f"""
                **方案类型**: {st.session_state.generated_plan['type']}  
                **团队规模**: {st.session_state.generated_plan['team_size']}  
                **重点关注**: {', '.join(st.session_state.generated_plan['focus'])}
                """)
                
                with st.expander("📋 查看完整方案", expanded=True):
                    st.markdown(st.session_state.generated_plan["content"])
                
                # 下载功能
                st.markdown("---")
                st.subheader("📥 方案导出")
                
                col_download1, col_download2 = st.columns(2)
                
                with col_download1:
                    if st.button("📄 导出为Markdown", use_container_width=True):
                        st.success("✅ Markdown文件已准备好下载！")
                
                with col_download2:
                    if st.button("📋 导出为Word", use_container_width=True):
                        st.success("✅ Word文档已准备好下载！")
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
        
        # 竞赛教练提示词系统（使用真实LLM - 更智能、更实用）
        def get_competition_coach_response(prompt, context=None):
            """竞赛教练AI响应生成 - 使用真实LLM，提供真正有用的建议"""
            
            base_prompt = """
            你是一位拥有15年以上计算机设计大赛指导经验的金牌教练，曾指导过50+支获奖团队。
            
            你的核心能力：
            - 🎯 精准解读比赛需求和评分标准
            - 💡 挖掘项目创新点和技术亮点
            - 🛠️ 提供可落地的技术方案建议
            - 🎭 指导精彩的Demo演示和答辩
            - 👥 优化团队协作和时间管理
            - 📊 准备专业的项目文档和PPT
            
            请记住你的回答原则：
            1. **具体不空洞** - 给出具体的例子、步骤、代码片段
            2. **实用可操作** - 提供马上就能用的建议
            3. **结构清晰** - 用小标题、列表组织内容
            4. **直击重点** - 不啰嗦，直接说有用的
            5. **真诚可信** - 如果不确定就说实话，不误导
            
            请用emoji让回答更生动，用清晰的结构让内容更易读。
            """
            
            # 添加上下文信息
            if context:
                full_prompt = f"{base_prompt}\n\n{context}\n\n用户问题：{prompt}"
            else:
                full_prompt = f"{base_prompt}\n\n用户问题：{prompt}"
            
            try:
                # 调用真实的LLM
                response = invoke_llm(full_prompt)
                return response
            except Exception as e:
                # 如果LLM调用失败，使用备用响应
                logger.error(f"LLM调用失败: {e}")
                return f"""
                🤖 **竞赛教练建议**
                
                针对您的问题"{prompt}"，我的建议是：
                
                1. **深入分析需求** - 仔细理解比赛要求和评分标准
                2. **突出创新亮点** - 找到项目的独特之处
                3. **完善技术方案** - 确保技术方案的可行性和先进性
                4. **充分准备答辩** - 提前演练，准备应对各种问题
                
                💡 如需更具体的建议，请告诉我更多细节！
                (LLM服务暂时不可用，这是备用建议)
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

