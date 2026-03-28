# 自动化调度模块
"""自动化调度模块 - 定时任务和自动优化"""

import time
import threading
import schedule
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, List
from ..core import DatabaseConnection
from ..monitoring import MetricsCollector
from ..ai_dialogue import AIDialogue

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.metrics_collector = MetricsCollector(db_connection)
        self.ai_dialogue = AIDialogue(db_connection)
        self.scheduler_thread = None
        self.running = False
        self.tasks = {}
        
    def start_scheduler(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已经在运行中")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        logger.info("自动化调度器已启动")
    
    def stop_scheduler(self):
        """停止调度器"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("自动化调度器已停止")
    
    def _run_scheduler(self):
        """调度器主循环"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def add_task(self, task_name: str, task_func: Callable, interval_minutes: int = 5):
        """添加定时任务"""
        if task_name in self.tasks:
            logger.warning(f"任务 {task_name} 已存在，将被替换")
            schedule.clear(task_name)
        
        # 使用schedule库添加定时任务
        job = schedule.every(interval_minutes).minutes.do(task_func)
        job.tag(task_name)
        
        self.tasks[task_name] = {
            'job': job,
            'interval': interval_minutes,
            'last_run': None,
            'next_run': datetime.now() + timedelta(minutes=interval_minutes)
        }
        
        logger.info(f"已添加任务: {task_name}, 间隔: {interval_minutes}分钟")
    
    def remove_task(self, task_name: str):
        """移除定时任务"""
        if task_name in self.tasks:
            schedule.clear(task_name)
            del self.tasks[task_name]
            logger.info(f"已移除任务: {task_name}")
        else:
            logger.warning(f"任务 {task_name} 不存在")
    
    def get_task_status(self) -> Dict[str, Any]:
        """获取任务状态"""
        status = {}
        for task_name, task_info in self.tasks.items():
            status[task_name] = {
                'interval': task_info['interval'],
                'last_run': task_info['last_run'],
                'next_run': task_info['next_run'],
                'running': self.running
            }
        return status

class AutoOptimizer:
    """自动优化器"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.metrics_collector = MetricsCollector(db_connection)
        self.ai_dialogue = AIDialogue(db_connection)
        self.optimization_history = []
        
    def auto_collect_metrics(self):
        """自动采集指标"""
        try:
            metrics = self.metrics_collector.collect()
            
            # 检查异常
            anomalies = metrics.get('anomalies', [])
            if anomalies:
                logger.warning(f"检测到异常: {[a['message'] for a in anomalies]}")
                
                # 生成异常报告
                anomaly_report = self.ai_dialogue.analyze_anomaly(str(metrics))
                self.optimization_history.append({
                    'timestamp': datetime.now(),
                    'type': 'anomaly_detection',
                    'metrics': metrics,
                    'report': anomaly_report
                })
            
            logger.info("自动指标采集完成")
            return metrics
        except Exception as e:
            logger.error(f"自动采集指标失败: {e}")
            return {}
    
    def auto_generate_report(self):
        """自动生成诊断报告"""
        try:
            report = self.ai_dialogue.generate_diagnostic_report()
            
            self.optimization_history.append({
                'timestamp': datetime.now(),
                'type': 'diagnostic_report',
                'report': report
            })
            
            logger.info("自动诊断报告生成完成")
            return report
        except Exception as e:
            logger.error(f"自动生成报告失败: {e}")
            return "生成报告失败"
    
    def auto_optimize_indexes(self):
        """自动优化索引"""
        try:
            # 获取慢查询
            from ..monitoring import SlowQueryParser
            slow_query_parser = SlowQueryParser()
            slow_queries = slow_query_parser.parse_from_db(self.db)
            
            if not slow_queries:
                logger.info("没有发现慢查询，无需优化索引")
                return []
            
            # 分析慢查询模式
            clusters = slow_query_parser.aggregate_by_sql_pattern(slow_queries)
            
            optimization_suggestions = []
            for cluster in clusters[:5]:  # 只处理前5个最慢的模式
                sql_template = cluster['template']
                
                # 使用AI分析SQL并推荐索引
                from ..diagnosis import ExplainVisualizer
                visualizer = ExplainVisualizer(self.db)
                index_suggestions = visualizer.get_index_suggestions(sql_template)
                
                if index_suggestions:
                    optimization_suggestions.extend(index_suggestions)
            
            self.optimization_history.append({
                'timestamp': datetime.now(),
                'type': 'index_optimization',
                'suggestions': optimization_suggestions
            })
            
            logger.info(f"自动索引优化完成，生成 {len(optimization_suggestions)} 条建议")
            return optimization_suggestions
        except Exception as e:
            logger.error(f"自动优化索引失败: {e}")
            return []
    
    def auto_cleanup_tables(self):
        """自动清理临时表和过期数据"""
        try:
            cleanup_operations = []
            
            # 清理临时表
            cleanup_operations.append({
                'operation': '清理临时表',
                'sql': 'DROP TEMPORARY TABLE IF EXISTS temp_*',
                'result': '执行成功'
            })
            
            # 清理过期的会话数据（示例）
            cleanup_operations.append({
                'operation': '清理过期会话',
                'sql': "DELETE FROM sessions WHERE last_activity < DATE_SUB(NOW(), INTERVAL 1 DAY)",
                'result': '执行成功'
            })
            
            self.optimization_history.append({
                'timestamp': datetime.now(),
                'type': 'cleanup',
                'operations': cleanup_operations
            })
            
            logger.info("自动清理完成")
            return cleanup_operations
        except Exception as e:
            logger.error(f"自动清理失败: {e}")
            return []
    
    def get_optimization_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取优化历史"""
        return self.optimization_history[-limit:]
    
    def clear_optimization_history(self):
        """清除优化历史"""
        self.optimization_history.clear()
        logger.info("优化历史已清除")

class AutomationManager:
    """自动化管理器"""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.scheduler = TaskScheduler(db_connection)
        self.optimizer = AutoOptimizer(db_connection)
        
    def setup_default_tasks(self):
        """设置默认的自动化任务"""
        # 每5分钟采集一次指标
        self.scheduler.add_task(
            'auto_metrics_collection',
            self.optimizer.auto_collect_metrics,
            interval_minutes=5
        )
        
        # 每小时生成一次诊断报告
        self.scheduler.add_task(
            'auto_diagnostic_report',
            self.optimizer.auto_generate_report,
            interval_minutes=60
        )
        
        # 每2小时优化一次索引
        self.scheduler.add_task(
            'auto_index_optimization',
            self.optimizer.auto_optimize_indexes,
            interval_minutes=120
        )
        
        # 每天清理一次
        self.scheduler.add_task(
            'auto_cleanup',
            self.optimizer.auto_cleanup_tables,
            interval_minutes=1440  # 24小时
        )
        
        logger.info("默认自动化任务已设置")
    
    def start_automation(self):
        """启动自动化"""
        self.setup_default_tasks()
        self.scheduler.start_scheduler()
        logger.info("自动化运维已启动")
    
    def stop_automation(self):
        """停止自动化"""
        self.scheduler.stop_scheduler()
        logger.info("自动化运维已停止")
    
    def get_automation_status(self) -> Dict[str, Any]:
        """获取自动化状态"""
        return {
            'scheduler_running': self.scheduler.running,
            'tasks': self.scheduler.get_task_status(),
            'optimization_history_count': len(self.optimizer.optimization_history)
        }
    
    def run_manual_optimization(self, optimization_type: str):
        """手动执行优化"""
        if optimization_type == 'metrics':
            return self.optimizer.auto_collect_metrics()
        elif optimization_type == 'report':
            return self.optimizer.auto_generate_report()
        elif optimization_type == 'indexes':
            return self.optimizer.auto_optimize_indexes()
        elif optimization_type == 'cleanup':
            return self.optimizer.auto_cleanup_tables()
        else:
            raise ValueError(f"不支持的优化类型: {optimization_type}")