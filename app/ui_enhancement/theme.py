# 主题模块
"""界面主题和样式模块"""

import streamlit as st
from typing import Dict, Any

class ThemeManager:
    """主题管理器"""
    
    @staticmethod
    def apply_custom_theme():
        """应用自定义主题"""
        st.markdown("""
        <style>
        /* 主容器样式 */
        .main {
            background-color: #f8f9fa;
        }
        
        /* 侧边栏样式 */
        .css-1d391kg {
            background-color: #2c3e50;
        }
        
        /* 标题样式 */
        h1, h2, h3 {
            color: #2c3e50;
            font-weight: 600;
        }
        
        /* 按钮样式 */
        .stButton > button {
            background-color: #3498db;
            color: white;
            border-radius: 8px;
            border: none;
            padding: 10px 20px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            background-color: #2980b9;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        
        /* 输入框样式 */
        .stTextInput > div > div > input {
            border-radius: 8px;
            border: 2px solid #ecf0f1;
            padding: 10px;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #3498db;
            box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
        }
        
        /* 选项卡样式 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: #ecf0f1;
            border-radius: 8px 8px 0 0;
            padding: 10px 20px;
            font-weight: 500;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #3498db;
            color: white;
        }
        
        /* 指标卡片样式 */
        .metric-container {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin: 10px 0;
        }
        
        /* 警告和成功消息样式 */
        .stAlert {
            border-radius: 8px;
            padding: 15px;
        }
        
        /* 加载动画 */
        .stSpinner {
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
            .metric-container {
                margin: 5px 0;
                padding: 15px;
            }
            
            .stButton > button {
                width: 100%;
                margin: 5px 0;
            }
            
            /* 移动端导航优化 */
            .css-1d391kg {
                width: 280px;
            }
        }
        
        /* 卡片样式优化 */
        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin: 15px 0;
            transition: transform 0.3s ease;
            border: 1px solid #e1e8ed;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }
        
        /* 导航样式优化 */
        .css-1d391kg {
            padding: 20px;
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
        }
        
        /* 改进的滚动条 */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #3498db;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #2980b9;
        }
        
        /* 欢迎页面特殊样式 */
        .welcome-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 15px;
            margin-bottom: 30px;
        }
        
        .feature-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin: 15px 0;
            transition: all 0.3s ease;
            border-left: 5px solid #3498db;
        }
        
        .feature-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        /* 登录页面优化 */
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 30px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        /* 外部地址访问优化 */
        .external-access {
            background: #e8f4fd;
            border: 2px dashed #3498db;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def create_metric_card(title: str, value: Any, delta: Any = None, help_text: str = None):
        """创建美观的指标卡片"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"""
            <div class="metric-container">
                <h4 style="margin: 0; color: #2c3e50;">{title}</h4>
                <h2 style="margin: 10px 0; color: #3498db;">{value}</h2>
                {f'<p style="margin: 0; color: #27ae60;">{delta}</p>' if delta else ''}
                {f'<p style="margin: 5px 0 0 0; font-size: 12px; color: #7f8c8d;">{help_text}</p>' if help_text else ''}
            </div>
            """, unsafe_allow_html=True)
    
    @staticmethod
    def create_status_indicator(status: str, message: str):
        """创建状态指示器"""
        colors = {
            'success': '#27ae60',
            'warning': '#f39c12',
            'error': '#e74c3c',
            'info': '#3498db'
        }
        
        color = colors.get(status, '#95a5a6')
        
        st.markdown(f"""
        <div style="
            background-color: {color}20;
            border-left: 4px solid {color};
            padding: 12px;
            border-radius: 4px;
            margin: 10px 0;
        ">
            <strong style="color: {color};">{status.upper()}</strong>
            <p style="margin: 5px 0 0 0; color: #2c3e50;">{message}</p>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def create_progress_bar(value: float, max_value: float, label: str):
        """创建进度条"""
        percentage = (value / max_value) * 100
        color = '#27ae60' if percentage < 70 else '#f39c12' if percentage < 90 else '#e74c3c'
        
        st.markdown(f"""
        <div style="margin: 10px 0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-weight: 500;">{label}</span>
                <span style="color: {color};">{percentage:.1f}%</span>
            </div>
            <div style="
                background-color: #ecf0f1;
                border-radius: 10px;
                height: 8px;
                overflow: hidden;
            ">
                <div style="
                    background-color: {color};
                    height: 100%;
                    width: {percentage}%;
                    border-radius: 10px;
                    transition: width 0.3s ease;
                "></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

class NavigationManager:
    """导航管理器"""
    
    @staticmethod
    def create_breadcrumb(current_page: str):
        """创建面包屑导航"""
        st.markdown(f"""
        <div style="
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <span style="color: #7f8c8d;">首页</span>
            <span style="color: #7f8c8d; margin: 0 10px;">›</span>
            <span style="color: #3498db; font-weight: 500;">{current_page}</span>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def create_quick_actions():
        """创建快速操作按钮"""
        st.markdown("### 🚀 快速操作")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 采集指标", use_container_width=True):
                st.session_state.quick_action = "collect_metrics"
        
        with col2:
            if st.button("🔍 生成报告", use_container_width=True):
                st.session_state.quick_action = "generate_report"
        
        with col3:
            if st.button("⚡ 一键优化", use_container_width=True):
                st.session_state.quick_action = "auto_optimize"

class ResponsiveLayout:
    """响应式布局管理器"""
    
    @staticmethod
    def create_metrics_grid(metrics: Dict[str, Any]):
        """创建响应式指标网格"""
        cols = st.columns(4)
        
        metric_configs = [
            ('QPS', metrics.get('qps', 0), 'queries/sec'),
            ('TPS', metrics.get('tps', 0), 'transactions/sec'),
            ('CPU使用率', metrics.get('cpu_usage', 0), '%'),
            ('内存使用率', metrics.get('memory_usage', 0), '%'),
            ('连接数', metrics.get('connections', {}).get('current', 0), ''),
            ('慢查询', metrics.get('slow_queries', 0), ''),
            ('缓冲池命中率', metrics.get('innodb_buffer_pool_hit_rate', 0), '%'),
            ('磁盘使用率', metrics.get('disk_usage', 0), '%')
        ]
        
        for i, (title, value, unit) in enumerate(metric_configs):
            with cols[i % 4]:
                ThemeManager.create_metric_card(
                    title,
                    f"{value:.2f}{unit}",
                    help_text=f"当前{title}"
                )
    
    @staticmethod
    def create_dashboard_overview():
        """创建仪表板概览"""
        # 顶部状态栏
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            ThemeManager.create_status_indicator('success', '数据库连接正常')
        
        with col2:
            ThemeManager.create_status_indicator('info', '监控运行中')
        
        with col3:
            ThemeManager.create_status_indicator('warning', '2个警告需要关注')
        
        with col4:
            ThemeManager.create_status_indicator('success', '系统负载正常')
        
        # 性能指标进度条
        st.markdown("### 📈 性能指标")
        
        # 模拟数据
        ThemeManager.create_progress_bar(65, 100, 'CPU使用率')
        ThemeManager.create_progress_bar(78, 100, '内存使用率')
        ThemeManager.create_progress_bar(45, 100, '磁盘使用率')
        ThemeManager.create_progress_bar(92, 100, '缓冲池命中率')

class AnimationEffects:
    """动画效果管理器"""
    
    @staticmethod
    def add_loading_animation():
        """添加加载动画"""
        st.markdown("""
        <style>
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .loading-spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 2s linear infinite;
            margin: 20px auto;
        }
        
        .fade-in {
            animation: fadeIn 0.5s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def create_success_animation():
        """创建成功动画"""
        st.markdown("""
        <style>
        .success-checkmark {
            width: 80px;
            height: 80px;
            margin: 0 auto;
        }
        
        .success-checkmark .check {
            stroke: #27ae60;
            stroke-width: 2;
            stroke-linecap: round;
            animation: draw 0.5s ease-in-out;
        }
        
        @keyframes draw {
            to {
                stroke-dashoffset: 0;
            }
        }
        </style>
        """, unsafe_allow_html=True)