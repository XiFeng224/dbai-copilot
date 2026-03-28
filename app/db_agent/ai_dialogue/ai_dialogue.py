# AI dialogue module
"""AI对话模块"""

import time
import logging
from collections import deque
from ...llm import invoke_llm
from ..core import DatabaseConnection
from ..monitoring import MetricsCollector, SlowQueryParser
from ..diagnosis import ExplainVisualizer, SQLFingerprint, LockAnalyzer
from ..optimization import IndexRecommender, SQLRewriter, ParamTuner

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIDialogue:
    """AI对话引擎"""
    
    def __init__(self, db_connection):
        """初始化AI对话引擎"""
        self.db = db_connection
        self.metrics_collector = MetricsCollector(db_connection)
        self.slow_query_parser = SlowQueryParser()
        self.explain_visualizer = ExplainVisualizer(db_connection)
        self.sql_fingerprint = SQLFingerprint()
        self.lock_analyzer = LockAnalyzer(db_connection)
        self.index_recommender = IndexRecommender(db_connection)
        self.sql_rewriter = SQLRewriter(db_connection)
        self.param_tuner = ParamTuner(db_connection)
        self.dialogue_history = deque(maxlen=10)  # 保存最近10轮对话
        self.cache = {}  # 缓存常见问题的回答
        self.last_metrics_time = 0
        self.metrics_cache = None
    
    def answer_question(self, question, use_history=True):
        """回答用户问题"""
        try:
            # 检查缓存
            cache_key = f"q_{hash(question)}"
            if cache_key in self.cache:
                logger.info("使用缓存回答问题")
                return self.cache[cache_key]
            
            # 收集数据库状态信息
            metrics = self._get_metrics()
            slow_queries = self.slow_query_parser.parse_from_db(self.db)
            lock_waits = self.lock_analyzer.analyze_lock_waits()
            
            # 构建上下文
            context = f"""
            数据库状态信息：
            - QPS: {metrics.get('qps', 0):.2f}
            - TPS: {metrics.get('tps', 0):.2f}
            - CPU使用率: {metrics.get('cpu_usage', 0):.2f}%
            - 内存使用率: {metrics.get('memory_usage', 0):.2f}%
            - 连接数: {metrics.get('connections', {}).get('current', 0)}/{metrics.get('connections', {}).get('max', 0)}
            - 慢查询数: {metrics.get('slow_queries', 0)}
            
            最近慢查询: {len(slow_queries)}条
            锁等待: {len(lock_waits)}个
            """
            
            # 添加对话历史
            if use_history and self.dialogue_history:
                history = "\n对话历史：\n"
                for idx, (q, a) in enumerate(self.dialogue_history):
                    history += f"用户: {q}\n助手: {a}\n"
                context += history
            
            # 构建提示词
            prompt = f"""
            你是一个专业的数据库运维专家，根据以下数据库状态信息回答用户问题：
            
            {context}
            
            用户问题：{question}
            
            请提供详细、专业的回答，包括：
            1. 问题的分析
            2. 可能的原因
            3. 解决方案建议
            4. 相关的技术细节
            
            请使用专业但易于理解的语言，结构清晰，重点突出。
            """
            
            # 调用LLM
            response = invoke_llm(prompt)
            
            # 保存到缓存和对话历史
            self.cache[cache_key] = response
            self.dialogue_history.append((question, response))
            
            return response
        except Exception as e:
            logger.error(f"回答问题时出错: {e}")
            return f"抱歉，处理您的问题时出错：{str(e)}"
    
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

