# 预测性分析模块
"""预测性分析模块 - 智能预测和预警功能"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import logging
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PredictiveAnalyzer:
    """预测性分析器"""
    
    def __init__(self):
        self.metrics_history = []
        self.models = {}
        self.scalers = {}
        self.anomaly_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 90.0,
            'qps': 1000.0,
            'slow_queries': 10
        }
        
    def add_metrics(self, metrics: Dict[str, Any]):
        """添加指标数据"""
        try:
            # 添加时间戳
            metrics['timestamp'] = datetime.now()
            self.metrics_history.append(metrics)
            
            # 保持历史数据长度（最多1000条）
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
                
            logger.info(f"已添加指标数据，当前历史记录数: {len(self.metrics_history)}")
        except Exception as e:
            logger.error(f"添加指标数据失败: {e}")
    
    def predict_trend(self, metric_name: str, hours_ahead: int = 1) -> Dict[str, Any]:
        """预测指标趋势"""
        try:
            if len(self.metrics_history) < 10:
                return {
                    'success': False,
                    'message': '历史数据不足，需要至少10个数据点'
                }
            
            # 提取指标数据
            data = []
            for metric in self.metrics_history:
                if metric_name in metric:
                    data.append({
                        'timestamp': metric['timestamp'],
                        'value': metric[metric_name]
                    })
            
            if len(data) < 10:
                return {
                    'success': False,
                    'message': f'指标 {metric_name} 的数据点不足'
                }
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            df = df.sort_values('timestamp')
            
            # 创建时间特征
            df['time_index'] = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds() / 3600
            
            # 训练线性回归模型
            X = df[['time_index']].values
            y = df['value'].values
            
            if metric_name not in self.models:
                self.models[metric_name] = LinearRegression()
                self.scalers[metric_name] = StandardScaler()
            
            # 标准化特征
            X_scaled = self.scalers[metric_name].fit_transform(X)
            self.models[metric_name].fit(X_scaled, y)
            
            # 预测未来值
            future_time = df['time_index'].max() + hours_ahead
            future_time_scaled = self.scalers[metric_name].transform([[future_time]])
            predicted_value = self.models[metric_name].predict(future_time_scaled)[0]
            
            # 计算趋势
            current_value = df['value'].iloc[-1]
            trend = '上升' if predicted_value > current_value else '下降'
            
            return {
                'success': True,
                'metric': metric_name,
                'current_value': current_value,
                'predicted_value': predicted_value,
                'trend': trend,
                'change_percent': ((predicted_value - current_value) / current_value * 100) if current_value != 0 else 0,
                'prediction_hours': hours_ahead
            }
        except Exception as e:
            logger.error(f"预测趋势失败: {e}")
            return {
                'success': False,
                'message': f'预测失败: {str(e)}'
            }
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """检测异常"""
        try:
            if len(self.metrics_history) < 20:
                return []
            
            anomalies = []
            
            # 提取最近的指标数据
            recent_metrics = self.metrics_history[-20:]
            
            # 为每个指标检测异常
            for metric_name in ['cpu_usage', 'memory_usage', 'qps', 'slow_queries']:
                values = []
                timestamps = []
                
                for metric in recent_metrics:
                    if metric_name in metric:
                        values.append(metric[metric_name])
                        timestamps.append(metric['timestamp'])
                
                if len(values) >= 10:
                    # 使用孤立森林检测异常
                    X = np.array(values).reshape(-1, 1)
                    
                    # 训练异常检测模型
                    iso_forest = IsolationForest(contamination=0.1, random_state=42)
                    predictions = iso_forest.fit_predict(X)
                    
                    # 找出异常点
                    for i, pred in enumerate(predictions):
                        if pred == -1:  # 异常点
                            anomalies.append({
                                'metric': metric_name,
                                'value': values[i],
                                'timestamp': timestamps[i],
                                'severity': 'high' if values[i] > self.anomaly_thresholds.get(metric_name, 0) else 'medium',
                                'message': f'{metric_name} 异常: {values[i]:.2f}'
                            })
            
            return anomalies
        except Exception as e:
            logger.error(f"检测异常失败: {e}")
            return []
    
    def generate_early_warning(self) -> Dict[str, Any]:
        """生成早期预警"""
        try:
            warnings = []
            
            # 预测关键指标趋势
            key_metrics = ['cpu_usage', 'memory_usage', 'qps', 'slow_queries']
            
            for metric in key_metrics:
                prediction = self.predict_trend(metric, hours_ahead=2)
                
                if prediction['success']:
                    current_value = prediction['current_value']
                    predicted_value = prediction['predicted_value']
                    threshold = self.anomaly_thresholds.get(metric, 0)
                    
                    # 检查是否可能超过阈值
                    if predicted_value > threshold * 0.8:  # 80%阈值时发出预警
                        warnings.append({
                            'metric': metric,
                            'current_value': current_value,
                            'predicted_value': predicted_value,
                            'threshold': threshold,
                            'warning_level': 'high' if predicted_value > threshold else 'medium',
                            'message': f'{metric} 预计在2小时内可能达到 {predicted_value:.2f}，接近阈值 {threshold}'
                        })
            
            # 检测当前异常
            current_anomalies = self.detect_anomalies()
            
            return {
                'timestamp': datetime.now(),
                'warnings': warnings,
                'anomalies': current_anomalies,
                'total_warnings': len(warnings),
                'total_anomalies': len(current_anomalies)
            }
        except Exception as e:
            logger.error(f"生成早期预警失败: {e}")
            return {
                'timestamp': datetime.now(),
                'warnings': [],
                'anomalies': [],
                'total_warnings': 0,
                'total_anomalies': 0,
                'error': str(e)
            }
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """获取性能洞察"""
        try:
            if len(self.metrics_history) < 10:
                return {'success': False, 'message': '数据不足'}
            
            insights = {}
            
            # 分析CPU使用率趋势
            cpu_data = [m.get('cpu_usage', 0) for m in self.metrics_history if 'cpu_usage' in m]
            if cpu_data:
                insights['cpu_avg'] = np.mean(cpu_data)
                insights['cpu_max'] = np.max(cpu_data)
                insights['cpu_trend'] = '上升' if cpu_data[-1] > cpu_data[0] else '下降'
            
            # 分析内存使用率趋势
            memory_data = [m.get('memory_usage', 0) for m in self.metrics_history if 'memory_usage' in m]
            if memory_data:
                insights['memory_avg'] = np.mean(memory_data)
                insights['memory_max'] = np.max(memory_data)
                insights['memory_trend'] = '上升' if memory_data[-1] > memory_data[0] else '下降'
            
            # 分析QPS趋势
            qps_data = [m.get('qps', 0) for m in self.metrics_history if 'qps' in m]
            if qps_data:
                insights['qps_avg'] = np.mean(qps_data)
                insights['qps_max'] = np.max(qps_data)
                insights['qps_trend'] = '上升' if qps_data[-1] > qps_data[0] else '下降'
            
            # 生成总体评估
            if insights:
                if insights.get('cpu_avg', 0) > 70:
                    insights['overall_health'] = '警告'
                    insights['health_message'] = 'CPU使用率较高，建议优化'
                elif insights.get('memory_avg', 0) > 80:
                    insights['overall_health'] = '警告'
                    insights['health_message'] = '内存使用率较高，建议扩容'
                else:
                    insights['overall_health'] = '良好'
                    insights['health_message'] = '系统运行状态良好'
            
            return {
                'success': True,
                'insights': insights,
                'data_points': len(self.metrics_history)
            }
        except Exception as e:
            logger.error(f"获取性能洞察失败: {e}")
            return {
                'success': False,
                'message': f'分析失败: {str(e)}'
            }
    
    def set_anomaly_thresholds(self, thresholds: Dict[str, float]):
        """设置异常检测阈值"""
        self.anomaly_thresholds.update(thresholds)
        logger.info(f"异常检测阈值已更新: {thresholds}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        return {
            'total_metrics': len(self.metrics_history),
            'time_range': {
                'start': self.metrics_history[0]['timestamp'] if self.metrics_history else None,
                'end': self.metrics_history[-1]['timestamp'] if self.metrics_history else None
            },
            'metrics_available': list(set(
                key for metric in self.metrics_history for key in metric.keys()
            ))
        }

class SmartAlertSystem:
    """智能告警系统"""
    
    def __init__(self, predictive_analyzer: PredictiveAnalyzer):
        self.analyzer = predictive_analyzer
        self.alerts_history = []
        self.alert_rules = {
            'cpu_high': {'metric': 'cpu_usage', 'threshold': 80, 'severity': 'high'},
            'memory_high': {'metric': 'memory_usage', 'threshold': 90, 'severity': 'high'},
            'qps_high': {'metric': 'qps', 'threshold': 1000, 'severity': 'medium'},
            'slow_queries_high': {'metric': 'slow_queries', 'threshold': 10, 'severity': 'medium'}
        }
        
    def check_alerts(self) -> List[Dict[str, Any]]:
        """检查告警"""
        try:
            current_alerts = []
            
            if not self.analyzer.metrics_history:
                return current_alerts
            
            latest_metrics = self.analyzer.metrics_history[-1]
            
            for rule_name, rule in self.alert_rules.items():
                metric = rule['metric']
                threshold = rule['threshold']
                severity = rule['severity']
                
                if metric in latest_metrics:
                    value = latest_metrics[metric]
                    if value > threshold:
                        alert = {
                            'id': len(self.alerts_history) + 1,
                            'rule': rule_name,
                            'metric': metric,
                            'value': value,
                            'threshold': threshold,
                            'severity': severity,
                            'timestamp': datetime.now(),
                            'message': f'{metric} 超过阈值: {value:.2f} > {threshold}'
                        }
                        current_alerts.append(alert)
            
            # 添加到历史记录
            self.alerts_history.extend(current_alerts)
            
            # 保持历史记录长度
            if len(self.alerts_history) > 100:
                self.alerts_history = self.alerts_history[-100:]
            
            return current_alerts
        except Exception as e:
            logger.error(f"检查告警失败: {e}")
            return []
    
    def get_alerts_summary(self) -> Dict[str, Any]:
        """获取告警摘要"""
        high_alerts = [a for a in self.alerts_history if a['severity'] == 'high']
        medium_alerts = [a for a in self.alerts_history if a['severity'] == 'medium']
        
        return {
            'total_alerts': len(self.alerts_history),
            'high_alerts': len(high_alerts),
            'medium_alerts': len(medium_alerts),
            'recent_alerts': self.alerts_history[-10:] if self.alerts_history else []
        }
    
    def add_alert_rule(self, rule_name: str, metric: str, threshold: float, severity: str):
        """添加告警规则"""
        self.alert_rules[rule_name] = {
            'metric': metric,
            'threshold': threshold,
            'severity': severity
        }
        logger.info(f"已添加告警规则: {rule_name}")
    
    def remove_alert_rule(self, rule_name: str):
        """移除告警规则"""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            logger.info(f"已移除告警规则: {rule_name}")
        else:
            logger.warning(f"告警规则 {rule_name} 不存在")
    
    def clear_alerts_history(self):
        """清除告警历史"""
        self.alerts_history.clear()
        logger.info("告警历史已清除")