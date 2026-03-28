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
    st.title("🔐 数据库AI助手 - DBAI-Copilot")
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("用户登录")
        username = st.text_input("用户名", placeholder="请输入用户名")
        password = st.text_input("密码", type="password", placeholder="请输入密码")
        
        if st.button("登录", type="primary", use_container_width=True):
            if username and password:
                session_token = st.session_state.security_manager.login(username, password)
                if session_token:
                    st.session_state.authenticated = True
                    st.session_state.session_token = session_token
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("用户名或密码错误")
            else:
                st.warning("请输入用户名和密码")
    
    with col2:
        st.markdown("### 💡 系统信息")
        st.info("""
        **默认账户:**
        - 用户名: admin
        - 密码: admin123
        
        **系统功能:**
        - 竞赛教练智能助手
        - 数据库运维智能助手
        - 多数据库支持
        - AI智能分析
        - 自动化运维
        """)
    
    st.stop()

# 主应用界面
NavigationManager.create_breadcrumb("主控制台")

# 添加欢迎页面选项到导航栏
pages = st.sidebar.selectbox(
    "选择功能",
    ["🏠 欢迎页面", "🎯 竞赛教练智能助手", "🛠️ 数据库运维智能助手", "⚙️ 系统管理"]
)

# 侧边栏用户信息
with st.sidebar:
    st.markdown("---")
    st.markdown(f"**👤 当前用户:** {st.session_state.username}")
    
    user_info = st.session_state.security_manager.get_user_info(st.session_state.session_token)
    if user_info:
        st.markdown(f"**🎯 角色:** {user_info['role']}")
    
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
    st.title("🎉 欢迎使用数据库AI助手 - DBAI-Copilot")
    st.markdown("---")
    
    # 项目介绍
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 📋 项目概述
        **DBAI-Copilot** 是一个集成了「竞赛教练智能助手」和「数据库运维智能助手」的双重功能智能系统，
        为计算机设计大赛和企业级数据库运维提供AI驱动的智能辅助。
        
        ### 🎯 核心功能
        - **🎯 竞赛教练智能助手** - 帮助参赛团队快速理解比赛需求，生成完整的技术方案
        - **🛠️ 数据库运维智能助手** - 提供智能化的数据库监控、诊断分析和自动化运维
        - **🤖 AI智能分析** - 结合RAG技术和机器学习算法实现智能分析
        - **🔒 安全可靠** - 完整的用户认证和权限管理系统
        """)
    
    with col2:
        st.image("https://via.placeholder.com/200x200/2c3e50/ffffff?text=DBAI-Copilot", 
                caption="数据库AI助手", width=200)
    
    # 功能卡片
    st.markdown("---")
    st.markdown("### 🚀 快速开始")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container():
            st.markdown("### 🎯 竞赛教练")
            st.markdown("上传比赛需求文档，智能生成技术方案和答辩材料")
            if st.button("开始使用", key="start_competition"):
                st.session_state.page = "竞赛教练智能助手"
                st.rerun()
    
    with col2:
        with st.container():
            st.markdown("### 🛠️ 数据库运维")
            st.markdown("实时监控、智能诊断、自动化优化数据库性能")
            if st.button("开始使用", key="start_database"):
                st.session_state.page = "数据库运维智能助手"
                st.rerun()
    
    with col3:
        with st.container():
            st.markdown("### ⚙️ 系统管理")
            st.markdown("用户管理、权限控制、系统监控和日志查看")
            if st.button("开始使用", key="start_management"):
                st.session_state.page = "系统管理"
                st.rerun()
    
    # 技术特色
    st.markdown("---")
    st.markdown("### 💡 技术特色")
    
    tech_features = [
        ("🔗 双重功能集成", "竞赛辅助与数据库运维完美结合"),
        ("🧠 AI智能驱动", "RAG技术 + 机器学习预测分析"),
        ("🌐 多数据库支持", "MySQL、PostgreSQL、SQL Server统一接口"),
        ("🎨 现代化界面", "Streamlit响应式Web应用"),
        ("⚡ 自动化运维", "定时任务调度和智能优化"),
        ("🔒 安全可靠", "完整的用户认证和权限管理")
    ]
    
    cols = st.columns(3)
    for i, (icon, desc) in enumerate(tech_features):
        with cols[i % 3]:
            st.markdown(f"**{icon} {desc.split(' - ')[0]}**")
            st.markdown(f"<small>{desc.split(' - ')[1] if ' - ' in desc else desc}</small>", unsafe_allow_html=True)

elif pages == "🎯 竞赛教练智能助手":
    st.title("🎯 竞赛教练智能助手")
    st.caption("上传比赛需求文件 -> 建立索引 -> 生成方案/功能/ Demo 剧本/评测/答辩大纲")
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
    
    # 系统管理功能
    tab1, tab2, tab3 = st.tabs(["👥 用户管理", "🔒 权限控制", "📊 系统监控"])
    
    with tab1:
        st.header("👥 用户管理")
        st.info("用户管理功能正在开发中...")
        
    with tab2:
        st.header("🔒 权限控制")
        st.info("权限控制功能正在开发中...")
        
    with tab3:
        st.header("📊 系统监控")
        if st.button("检查系统状态", use_container_width=True):
            try:
                system_status = st.session_state.system_monitor.get_system_status()
                st.success("✅ 系统运行正常")
                st.json(system_status)
            except Exception as e:
                st.error(f"❌ 获取系统状态失败: {str(e)}")
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

