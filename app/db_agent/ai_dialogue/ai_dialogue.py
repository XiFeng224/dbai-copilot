# AI dialogue module
"""增强的智能AI对话模块"""

import time
import logging
import json
from collections import deque
from typing import Dict, List, Any, Optional
from ...llm import invoke_llm
from ..core import DatabaseConnection
from ..monitoring import MetricsCollector, SlowQueryParser
from ..diagnosis import ExplainVisualizer, SQLFingerprint, LockAnalyzer
from ..optimization import IndexRecommender, SQLRewriter, ParamTuner

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIDialogue:
    """增强的智能AI对话引擎"""
    
    def __init__(self, db_connection):
        """初始化增强的AI对话引擎"""
        self.db = db_connection
        self.metrics_collector = MetricsCollector(db_connection)
        self.slow_query_parser = SlowQueryParser()
        self.explain_visualizer = ExplainVisualizer(db_connection)
        self.sql_fingerprint = SQLFingerprint()
        self.lock_analyzer = LockAnalyzer(db_connection)
        self.index_recommender = IndexRecommender(db_connection)
        self.sql_rewriter = SQLRewriter(db_connection)
        self.param_tuner = ParamTuner(db_connection)
        
        # 增强的记忆系统
        self.short_term_memory = deque(maxlen=20)  # 短期记忆：最近20轮对话
        self.long_term_memory = deque(maxlen=100)  # 长期记忆：重要信息
        self.conversation_context = {}  # 会话上下文
        self.user_profile = {}  # 用户画像
        
        # 智能缓存系统
        self.cache = {}
        self.cache_ttl = 300  # 5分钟缓存
        self.cache_timestamp = {}
        
        # 性能指标
        self.last_metrics_time = 0
        self.metrics_cache = None
        self.metrics_history = deque(maxlen=50)  # 保存50条历史指标
        
        # 分析能力
        self.analysis_capabilities = {
            "diagnosis": True,
            "optimization": True,
            "prediction": True,
            "security": True,
            "performance": True
        }
        
        # 主动学习
        self.learned_insights = deque(maxlen=50)
    
    def answer_question(self, question, use_history=True, use_long_term_memory=True):
        """增强的智能问答功能"""
        try:
            # 检查缓存
            cache_key = f"q_{hash(question)}"
            if self._check_cache(cache_key):
                logger.info("使用缓存回答问题")
                return self.cache[cache_key]
            
            # 智能问题分类
            question_type = self._classify_question(question)
            
            # 收集全面的上下文信息
            context = self._build_enhanced_context(question, question_type)
            
            # 添加对话记忆
            if use_history:
                context += self._build_memory_context()
            
            # 添加长期记忆
            if use_long_term_memory:
                context += self._build_long_term_context()
            
            # 构建增强的提示词
            prompt = self._build_enhanced_prompt(question, question_type, context)
            
            # 调用LLM
            response = invoke_llm(prompt)
            
            # 增强的响应处理
            response = self._enhance_response(response, question_type)
            
            # 智能记忆管理
            self._update_memory(question, response, question_type)
            
            # 缓存管理
            self._update_cache(cache_key, response)
            
            # 主动学习和建议
            self._active_learning(question, response, question_type)
            
            return response
        except Exception as e:
            logger.error(f"回答问题时出错: {e}")
            return self._handle_error(e)
    
    def _classify_question(self, question: str) -> str:
        """智能问题分类"""
        question_lower = question.lower()
        keywords = {
            "performance": ["性能", "慢", "响应", "qps", "tps", "cpu", "内存", "memory", "performance"],
            "optimization": ["优化", "索引", "index", "sql", "查询", "优化建议", "optimization"],
            "diagnosis": ["诊断", "错误", "问题", "故障", "诊断报告", "diagnosis", "error"],
            "security": ["安全", "权限", "访问", "加密", "安全问题", "security"],
            "backup": ["备份", "恢复", "backup", "restore"],
            "monitoring": ["监控", "指标", "监控告警", "monitoring", "metrics"],
            "general": ["介绍", "使用", "功能", "帮助", "怎么", "如何", "help", "what"]
        }
        
        for qtype, keys in keywords.items():
            if any(key in question_lower for key in keys):
                return qtype
        return "general"
    
    def _build_enhanced_context(self, question: str, question_type: str) -> str:
        """构建增强的上下文"""
        metrics = self._get_metrics()
        context_parts = []
        
        # 基础数据库状态
        context_parts.append(f"""
        ## 数据库实时状态
        - QPS: {metrics.get('qps', 0):.2f}
        - TPS: {metrics.get('tps', 0):.2f}
        - CPU使用率: {metrics.get('cpu_usage', 0):.2f}%
        - 内存使用率: {metrics.get('memory_usage', 0):.2f}%
        - 连接数: {metrics.get('connections', {}).get('current', 0)}/{metrics.get('connections', {}).get('max', 0)}
        - 慢查询数: {metrics.get('slow_queries', 0)}
        - 磁盘使用率: {metrics.get('disk_usage', 0):.2f}%
        """)
        
        # 根据问题类型添加专用上下文
        if question_type in ["performance", "diagnosis", "optimization"]:
            try:
                slow_queries = self.slow_query_parser.parse_from_db(self.db)
                lock_waits = self.lock_analyzer.analyze_lock_waits()
                
                if slow_queries:
                    top_slow = self.slow_query_parser.get_top_slow_queries(slow_queries, 3)
                    context_parts.append("""
                    ## 慢查询分析
                    """)
                    for i, query in enumerate(top_slow):
                        context_parts.append(f"""
                        {i+1}. 执行时间: {query['query_time']:.2f}秒
                           SQL: {query['sql'][:150]}...
                        """)
                
                context_parts.append(f"""
                ## 锁分析
                - 锁等待数: {len(lock_waits)}
                """)
            except Exception as e:
                logger.warning(f"获取诊断信息失败: {e}")
        
        if question_type == "optimization":
            try:
                param_recommendations = self.param_tuner.recommend_parameters()
                if param_recommendations:
                    context_parts.append("""
                    ## 参数优化建议
                    """)
                    for param in param_recommendations[:5]:
                        context_parts.append(f"""
                        - {param['parameter']}: 当前值={param['current']}, 建议值={param['recommended']}
                        """)
            except Exception as e:
                logger.warning(f"获取优化建议失败: {e}")
        
        return "\n".join(context_parts)
    
    def _build_memory_context(self) -> str:
        """构建短期记忆上下文"""
        if not self.short_term_memory:
            return ""
        
        context = """
        
        ## 近期对话历史
        """
        for idx, (q, a) in enumerate(list(self.short_term_memory)[-5:]):
            context += f"""
            用户[{idx+1}]: {q[:100]}...
            助手[{idx+1}]: {a[:150]}...
            """
        return context
    
    def _build_long_term_context(self) -> str:
        """构建长期记忆上下文"""
        if not self.long_term_memory and not self.learned_insights:
            return ""
        
        context = """
        
        ## 重要历史信息
        """
        if self.long_term_memory:
            for memory in list(self.long_term_memory)[-3:]:
                context += f"- {memory}\n"
        
        if self.learned_insights:
            context += """
            ## 学习到的洞察
            """
            for insight in list(self.learned_insights)[-3:]:
                context += f"- {insight}\n"
        
        return context
    
    def _build_enhanced_prompt(self, question: str, question_type: str, context: str) -> str:
        """构建增强的提示词 - 更专业、更实用"""
        prompts = {
            "performance": """
            你是一位拥有10年以上经验的数据库性能优化专家，曾服务过多家大型企业。你的回答必须专业、具体、可操作。
            
            请按照以下结构回答：
            
            ## 🎯 问题分析
            - 精准定位性能瓶颈
            - 分析根因
            - 评估影响范围
            
            ## 📊 性能优化方案（按优先级排序）
            - P0（紧急）：必须立即处理的问题
            - P1（重要）：应该优先处理的问题
            - P2（一般）：可以稍后处理的优化
            
            ## 🛠️ 具体实施步骤
            - 详细的操作命令
            - 执行顺序和注意事项
            - 验证方法
            """,
            "optimization": """
            你是一位顶级数据库优化专家，精通MySQL、PostgreSQL、SQL Server等主流数据库。
            
            请提供真正有用的优化方案：
            
            ## 🔍 问题深度分析
            - 当前问题的根本原因
            - 性能影响评估
            - 风险点识别
            
            ## 💡 优化方案
            - SQL优化建议（具体的SQL改写示例）
            - 索引优化建议（具体的CREATE INDEX语句）
            - 参数优化建议（具体的参数值和理由）
            
            ## 📋 实施计划
            - 步骤1、2、3...
            - 每个步骤的预期效果
            - 回滚方案
            """,
            "diagnosis": """
            你是一位数据库诊断专家，擅长快速定位和解决复杂的数据库问题。
            
            请进行全面诊断：
            
            ## 🚨 问题现状
            - 现象描述
            - 严重程度评估
            - 影响范围
            
            ## 🔬 根因分析
            - 可能的原因1
            - 可能的原因2
            - 验证方法
            
            ## 💊 解决方案
            - 紧急处理方案（立即执行）
            - 彻底解决方案（根本解决）
            - 预防措施（避免再发）
            """,
            "security": """
            你是一位数据库安全专家，熟悉各类安全漏洞和最佳实践。
            
            请提供实用的安全建议：
            
            ## 🔒 安全现状评估
            - 发现的安全问题
            - 风险等级
            - 潜在影响
            
            ## 🛡️ 安全加固方案
            - 具体的配置修改
            - 权限设置建议
            - 审计和监控建议
            
            ## 📋 安全最佳实践
            - 日常安全检查清单
            - 应急响应流程
            """,
            "general": """
            你是一位专业、友好、经验丰富的数据库技术顾问。
            
            请提供实用、可操作的建议：
            
            - 用清晰的结构组织回答
            - 提供具体的例子
            - 给出可执行的步骤
            - 语言通俗易懂但保持专业
            """
        }
        
        base_prompt = prompts.get(question_type, prompts["general"])
        
        return f"""
        {base_prompt}
        
        {context}
        
        用户问题：{question}
        
        问题类型：{question_type}
        
        请记住：
        1. 回答要具体，不要空泛
        2. 给出可操作的步骤，不是理论
        3. 用清晰的格式，方便阅读
        4. 提供实用的建议，真正能解决问题
        5. 如果不确定，就诚实说出来，不要误导
        6. 用emoji图标让回答更生动
        """
    
    def _enhance_response(self, response: str, question_type: str) -> str:
        """增强响应内容"""
        enhancements = {
            "performance": "\n\n💡 **性能优化小贴士**：建议定期监控性能指标，建立性能基线，以便及时发现异常。",
            "optimization": "\n\n⚠️ **优化注意事项**：在生产环境实施优化前，请先在测试环境验证，并准备好回滚方案。",
            "diagnosis": "\n\n🔍 **诊断建议**：建议记录完整的问题现象、发生时间、影响范围，便于后续分析。",
            "security": "\n\n🛡️ **安全提醒**：定期进行安全审计，更新补丁，遵循最小权限原则。"
        }
        
        if question_type in enhancements:
            response += enhancements[question_type]
        
        return response
    
    def _update_memory(self, question: str, response: str, question_type: str):
        """更新记忆系统"""
        # 短期记忆
        self.short_term_memory.append((question, response))
        
        # 重要信息保存到长期记忆
        if question_type in ["diagnosis", "optimization", "security"]:
            memory_key = f"{question_type}: {question[:50]}"
            self.long_term_memory.append(memory_key)
    
    def _check_cache(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self.cache:
            return False
        if cache_key not in self.cache_timestamp:
            return False
        return time.time() - self.cache_timestamp[cache_key] < self.cache_ttl
    
    def _update_cache(self, cache_key: str, response: str):
        """更新缓存"""
        self.cache[cache_key] = response
        self.cache_timestamp[cache_key] = time.time()
    
    def _active_learning(self, question: str, response: str, question_type: str):
        """主动学习机制"""
        if question_type in ["diagnosis", "optimization"]:
            insight = f"用户关注{question_type}问题：{question[:30]}..."
            self.learned_insights.append(insight)
    
    def _handle_error(self, error: Exception) -> str:
        """智能错误处理"""
        return f"""
        😔 抱歉，处理您的问题时遇到了一些小问题。
        
        错误信息：{str(error)}
        
        💡 建议您：
        1. 检查数据库连接是否正常
        2. 尝试简化您的问题
        3. 稍后再试
        
        如果问题持续存在，请告诉我具体的错误信息，我会尽力帮助您！
        """
    
    def generate_diagnostic_report(self, detailed=True):
        """生成智能诊断报告"""
        try:
            # 收集各种诊断信息
            metrics = self._get_metrics()
            slow_queries = self.slow_query_parser.parse_from_db(self.db)
            lock_waits = self.lock_analyzer.analyze_lock_waits()
            deadlocks = self.lock_analyzer.detect_deadlocks()
            long_transactions = self.lock_analyzer.get_long_running_transactions()
            
            # 分析慢查询
            if slow_queries:
                top_slow = self.slow_query_parser.get_top_slow_queries(slow_queries, 5)
                clusters = self.slow_query_parser.aggregate_by_sql_pattern(slow_queries)
            else:
                top_slow = []
                clusters = []
            
            # 收集优化建议
            param_recommendations = self.param_tuner.recommend_parameters()
            
            # 构建诊断报告内容
            report_content = f"""
            # 数据库诊断报告
            
            ## 1. 性能概览
            - QPS: {metrics.get('qps', 0):.2f}
            - TPS: {metrics.get('tps', 0):.2f}
            - CPU使用率: {metrics.get('cpu_usage', 0):.2f}%
            - 内存使用率: {metrics.get('memory_usage', 0):.2f}%
            - 连接数: {metrics.get('connections', {}).get('current', 0)}/{metrics.get('connections', {}).get('max', 0)}
            - 慢查询数: {metrics.get('slow_queries', 0)}
            
            ## 2. 慢查询分析
            - 慢查询总数: {len(slow_queries)}
            
            ### 2.1  Top 5 慢查询
            """
            
            # 添加Top 5慢查询
            for i, query in enumerate(top_slow):
                report_content += f"""
            {i+1}. 执行时间: {query['query_time']:.2f}秒
               扫描行数: {query['rows_examined']}
               返回行数: {query['rows_sent']}
               SQL: {query['sql'][:200]}...
            """
            
            # 添加SQL模式分析
            report_content += """
            
            ### 2.2 SQL模式分析
            """
            
            for i, cluster in enumerate(clusters[:5]):
                report_content += f"""
            {i+1}. 模式: {cluster['template'][:100]}...
               执行次数: {cluster['count']}
               平均执行时间: {cluster['avg_time']:.2f}秒
            """
            
            # 添加锁分析
            report_content += f"""
            
            ## 3. 锁分析
            - 锁等待数: {len(lock_waits)}
            - 死锁数: {len(deadlocks)}
            - 长时间运行事务: {len(long_transactions)}
            """
            
            # 添加参数调优建议
            report_content += """
            
            ## 4. 参数调优建议
            """
            
            for param in param_recommendations[:10]:
                report_content += f"""
            - {param['parameter']}: 当前值={param['current']}, 建议值={param['recommended']}
              原因: {param['reason']}
            """
            
            # 构建提示词，让LLM生成最终报告
            prompt = f"""
            请根据以下数据库诊断信息，生成一份专业、详细的诊断报告：
            
            {report_content}
            
            报告应包括：
            1. 总体健康状况评估
            2. 主要问题识别
            3. 详细的优化建议
            4. 优先级排序
            5. 长期维护建议
            
            请使用专业但易于理解的语言，结构清晰，重点突出。
            """
            
            # 调用LLM生成最终报告
            final_report = invoke_llm(prompt)
            
            # 保存到对话历史
            self.dialogue_history.append(("生成诊断报告", final_report[:100] + "..."))
            
            return final_report
        except Exception as e:
            logger.error(f"生成诊断报告时出错: {e}")
            return f"抱歉，生成诊断报告时出错：{str(e)}"
    
    def analyze_anomaly(self, metrics_history):
        """分析异常并提供根因分析"""
        try:
            # 构建上下文
            context = f"""
            数据库指标历史数据：
            {metrics_history}
            
            请分析可能的异常原因，并提供根因分析和解决方案。
            """
            
            # 构建提示词
            prompt = f"""
            你是一个专业的数据库运维专家，负责分析数据库异常。
            
            {context}
            
            请提供：
            1. 异常现象描述
            2. 可能的根因分析
            3. 验证方法
            4. 解决方案
            5. 预防措施
            
            请使用专业但易于理解的语言，结构清晰，重点突出。
            """
            
            # 调用LLM
            response = invoke_llm(prompt)
            
            # 保存到对话历史
            self.dialogue_history.append(("分析异常", response[:100] + "..."))
            
            return response
        except Exception as e:
            logger.error(f"分析异常时出错: {e}")
            return f"抱歉，分析异常时出错：{str(e)}"
    
    def _get_metrics(self):
        """获取数据库指标，带缓存机制"""
        current_time = time.time()
        # 缓存有效期为30秒
        if current_time - self.last_metrics_time < 30 and self.metrics_cache:
            return self.metrics_cache
        
        try:
            metrics = self.metrics_collector.collect()
            self.metrics_cache = metrics
            self.last_metrics_time = current_time
            return metrics
        except Exception as e:
            logger.error(f"获取指标时出错: {e}")
            return {}
    
    def clear_history(self):
        """清除对话历史"""
        self.dialogue_history.clear()
        return "对话历史已清除"
    
    def get_history(self):
        """获取对话历史"""
        return list(self.dialogue_history)
    
    def optimize_query(self, sql):
        """优化SQL语句"""
        try:
            # 获取SQL改写建议
            rewrite_result = self.sql_rewriter.rewrite_sql(sql)
            
            # 获取索引推荐
            index_recommendations = self.index_recommender.recommend_indexes(sql)
            
            # 构建上下文
            context = f"""
            原始SQL: {sql}
            
            SQL改写建议:
            {rewrite_result['rewritten_sql']}
            
            索引推荐:
            {index_recommendations}
            
            请提供详细的SQL优化建议，包括改写后的SQL、推荐的索引以及优化理由。
            """
            
            # 构建提示词
            prompt = f"""
            你是一个专业的SQL优化专家，根据以下信息提供SQL优化建议：
            
            {context}
            
            请提供：
            1. 原始SQL的问题分析
            2. 优化后的SQL
            3. 推荐的索引
            4. 优化理由
            5. 预期性能提升
            
            请使用专业但易于理解的语言，结构清晰，重点突出。
            """
            
            # 调用LLM
            response = invoke_llm(prompt)
            
            # 保存到对话历史
            self.dialogue_history.append((f"优化SQL: {sql[:50]}...", response[:100] + "..."))
            
            return response
        except Exception as e:
            logger.error(f"优化SQL时出错: {e}")
            return f"抱歉，优化SQL时出错：{str(e)}"

