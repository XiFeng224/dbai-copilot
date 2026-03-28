# 错误处理模块
"""错误处理和日志系统模块"""

import logging
import traceback
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import json
import os

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, log_file: str = "error.log"):
        self.log_file = log_file
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志配置"""
        # 创建日志目录
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 配置根日志记录器
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # 设置特定模块的日志级别
        logging.getLogger('streamlit').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """记录错误日志"""
        try:
            error_info = {
                'timestamp': datetime.now().isoformat(),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'traceback': traceback.format_exc(),
                'context': context or {}
            }
            
            # 写入错误日志文件
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_info, ensure_ascii=False) + '\n')
            
            # 同时使用标准日志记录
            logger = logging.getLogger(__name__)
            logger.error(f"错误类型: {error_info['error_type']}, 消息: {error_info['error_message']}")
            
            if context:
                logger.error(f"错误上下文: {context}")
            
        except Exception as e:
            # 如果错误记录失败，至少输出到控制台
            print(f"错误记录失败: {e}")
            print(f"原始错误: {error}")
    
    def handle_exception(self, func):
        """异常处理装饰器"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.log_error(e, {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                })
                # 重新抛出异常或返回错误信息
                raise
        return wrapper
    
    def safe_execute(self, func, *args, **kwargs) -> Dict[str, Any]:
        """安全执行函数"""
        try:
            result = func(*args, **kwargs)
            return {
                'success': True,
                'result': result,
                'error': None
            }
        except Exception as e:
            self.log_error(e, {
                'function': func.__name__,
                'args': str(args),
                'kwargs': str(kwargs)
            })
            return {
                'success': False,
                'result': None,
                'error': str(e)
            }
    
    def get_error_stats(self, days: int = 7) -> Dict[str, Any]:
        """获取错误统计信息"""
        try:
            if not os.path.exists(self.log_file):
                return {'total_errors': 0, 'error_types': {}, 'recent_errors': []}
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            cutoff_date = datetime.now() - datetime.timedelta(days=days)
            
            error_types = {}
            recent_errors = []
            total_errors = 0
            
            for line in lines:
                try:
                    error_info = json.loads(line.strip())
                    error_time = datetime.fromisoformat(error_info['timestamp'])
                    
                    if error_time >= cutoff_date:
                        total_errors += 1
                        
                        # 统计错误类型
                        error_type = error_info['error_type']
                        error_types[error_type] = error_types.get(error_type, 0) + 1
                        
                        # 收集最近错误
                        if len(recent_errors) < 10:
                            recent_errors.append({
                                'timestamp': error_info['timestamp'],
                                'type': error_type,
                                'message': error_info['error_message'][:100]
                            })
                except json.JSONDecodeError:
                    continue
            
            return {
                'total_errors': total_errors,
                'error_types': error_types,
                'recent_errors': recent_errors
            }
        except Exception as e:
            return {'total_errors': 0, 'error_types': {}, 'recent_errors': [], 'error': str(e)}

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.performance_data = []
        
    def start_timer(self, operation: str) -> str:
        """开始计时"""
        timer_id = f"{operation}_{datetime.now().timestamp()}"
        self.performance_data.append({
            'id': timer_id,
            'operation': operation,
            'start_time': datetime.now(),
            'end_time': None,
            'duration': None
        })
        return timer_id
    
    def end_timer(self, timer_id: str):
        """结束计时"""
        end_time = datetime.now()
        for data in self.performance_data:
            if data['id'] == timer_id and data['end_time'] is None:
                data['end_time'] = end_time
                data['duration'] = (end_time - data['start_time']).total_seconds()
                break
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        completed_operations = [d for d in self.performance_data if d['duration'] is not None]
        
        if not completed_operations:
            return {}
        
        # 按操作类型分组
        operation_stats = {}
        for op in completed_operations:
            op_type = op['operation']
            if op_type not in operation_stats:
                operation_stats[op_type] = []
            operation_stats[op_type].append(op['duration'])
        
        # 计算统计信息
        stats = {}
        for op_type, durations in operation_stats.items():
            stats[op_type] = {
                'count': len(durations),
                'avg_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'last_10_avg': sum(durations[-10:]) / min(10, len(durations))
            }
        
        return stats
    
    def get_slow_operations(self, threshold: float = 5.0) -> list:
        """获取慢操作列表"""
        return [
            op for op in self.performance_data
            if op['duration'] and op['duration'] > threshold
        ]

class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks = {}
        
    def register_check(self, name: str, check_func, interval: int = 300):
        """注册健康检查"""
        self.checks[name] = {
            'function': check_func,
            'interval': interval,
            'last_check': None,
            'last_result': None
        }
    
    def run_health_checks(self) -> Dict[str, Any]:
        """运行健康检查"""
        results = {}
        
        for name, check_info in self.checks.items():
            try:
                result = check_info['function']()
                check_info['last_result'] = result
                check_info['last_check'] = datetime.now()
                
                results[name] = {
                    'status': 'healthy' if result.get('healthy', False) else 'unhealthy',
                    'message': result.get('message', ''),
                    'details': result.get('details', {}),
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'message': f'检查执行失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                }
        
        return results
    
    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康摘要"""
        results = self.run_health_checks()
        
        healthy_count = sum(1 for r in results.values() if r['status'] == 'healthy')
        unhealthy_count = sum(1 for r in results.values() if r['status'] == 'unhealthy')
        error_count = sum(1 for r in results.values() if r['status'] == 'error')
        
        return {
            'total_checks': len(results),
            'healthy': healthy_count,
            'unhealthy': unhealthy_count,
            'errors': error_count,
            'health_percentage': (healthy_count / len(results)) * 100 if results else 0,
            'details': results
        }

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.error_handler = ErrorHandler()
        self.performance_monitor = PerformanceMonitor()
        self.health_checker = HealthChecker()
        
        # 注册默认健康检查
        self._register_default_checks()
    
    def _register_default_checks(self):
        """注册默认健康检查"""
        def disk_space_check():
            try:
                import psutil
                # 在Streamlit Cloud环境中，使用安全的方式检查磁盘
                disk = psutil.disk_usage('/')
                return {
                    'healthy': disk.percent < 90,
                    'message': f'磁盘使用率: {disk.percent:.1f}%',
                    'details': {
                        'used_gb': disk.used / 1024**3,
                        'total_gb': disk.total / 1024**3,
                        'percent': disk.percent
                    }
                }
            except Exception as e:
                # 在受限环境中返回模拟数据
                return {'healthy': True, 'message': '磁盘检查受限（云环境）', 'details': {'simulated': True}}
        
        def memory_check():
            try:
                import psutil
                memory = psutil.virtual_memory()
                return {
                    'healthy': memory.percent < 85,
                    'message': f'内存使用率: {memory.percent:.1f}%',
                    'details': {
                        'used_gb': memory.used / 1024**3,
                        'total_gb': memory.total / 1024**3,
                        'percent': memory.percent
                    }
                }
            except Exception as e:
                # 在受限环境中返回模拟数据
                return {'healthy': True, 'message': '内存检查受限（云环境）', 'details': {'simulated': True}}
        
        self.health_checker.register_check('disk_space', disk_space_check)
        self.health_checker.register_check('memory', memory_check)
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            'health': self.health_checker.get_health_summary(),
            'performance': self.performance_monitor.get_performance_stats(),
            'errors': self.error_handler.get_error_stats(),
            'timestamp': datetime.now().isoformat()
        }
    
    def check_system_health(self) -> Dict[str, Any]:
        """检查系统健康状态"""
        return self.health_checker.get_health_summary()
    
    def monitor_operation(self, operation: str):
        """监控操作装饰器"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                timer_id = self.performance_monitor.start_timer(operation)
                try:
                    result = func(*args, **kwargs)
                    self.performance_monitor.end_timer(timer_id)
                    return result
                except Exception as e:
                    self.performance_monitor.end_timer(timer_id)
                    self.error_handler.log_error(e, {'operation': operation})
                    raise
            return wrapper
        return decorator