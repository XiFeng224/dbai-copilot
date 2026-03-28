# 认证和安全模块
"""认证和安全模块 - 用户管理和权限控制"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
import json
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UserManager:
    """用户管理器"""
    
    def __init__(self, data_file: str = "users.json"):
        self.data_file = data_file
        self.users = self._load_users()
        self.sessions = {}
        
    def _load_users(self) -> Dict[str, Dict[str, Any]]:
        """加载用户数据"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 创建默认管理员用户
                default_users = {
                    'admin': {
                        'username': 'admin',
                        'password_hash': self._hash_password('admin123'),
                        'role': 'admin',
                        'created_at': datetime.now().isoformat(),
                        'last_login': None
                    }
                }
                self._save_users(default_users)
                return default_users
        except Exception as e:
            logger.error(f"加载用户数据失败: {e}")
            return {}
    
    def _save_users(self, users: Dict[str, Dict[str, Any]]):
        """保存用户数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户数据失败: {e}")
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = secrets.token_hex(16)
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex() + ':' + salt
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            hash_part, salt = password_hash.split(':')
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
            return new_hash == hash_part
        except Exception:
            return False
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """用户认证"""
        if username not in self.users:
            return None
        
        user = self.users[username]
        if not self._verify_password(password, user['password_hash']):
            return None
        
        # 生成会话令牌
        session_token = secrets.token_urlsafe(32)
        self.sessions[session_token] = {
            'username': username,
            'role': user['role'],
            'login_time': datetime.now(),
            'last_activity': datetime.now()
        }
        
        # 更新最后登录时间
        user['last_login'] = datetime.now().isoformat()
        self._save_users(self.users)
        
        logger.info(f"用户 {username} 登录成功")
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """验证会话"""
        if session_token not in self.sessions:
            return None
        
        session = self.sessions[session_token]
        
        # 检查会话是否过期（24小时）
        if datetime.now() - session['login_time'] > timedelta(hours=24):
            del self.sessions[session_token]
            return None
        
        # 更新最后活动时间
        session['last_activity'] = datetime.now()
        
        return {
            'username': session['username'],
            'role': session['role'],
            'login_time': session['login_time']
        }
    
    def logout(self, session_token: str):
        """用户登出"""
        if session_token in self.sessions:
            username = self.sessions[session_token]['username']
            del self.sessions[session_token]
            logger.info(f"用户 {username} 已登出")
    
    def create_user(self, username: str, password: str, role: str = 'user') -> bool:
        """创建用户"""
        if username in self.users:
            return False
        
        self.users[username] = {
            'username': username,
            'password_hash': self._hash_password(password),
            'role': role,
            'created_at': datetime.now().isoformat(),
            'last_login': None
        }
        
        self._save_users(self.users)
        logger.info(f"已创建用户: {username}, 角色: {role}")
        return True
    
    def delete_user(self, username: str) -> bool:
        """删除用户"""
        if username not in self.users:
            return False
        
        del self.users[username]
        self._save_users(self.users)
        
        # 删除相关会话
        tokens_to_remove = [
            token for token, session in self.sessions.items()
            if session['username'] == username
        ]
        for token in tokens_to_remove:
            del self.sessions[token]
        
        logger.info(f"已删除用户: {username}")
        return True
    
    def get_users(self) -> List[Dict[str, Any]]:
        """获取用户列表"""
        return [
            {
                'username': user['username'],
                'role': user['role'],
                'created_at': user['created_at'],
                'last_login': user['last_login']
            }
            for user in self.users.values()
        ]
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """获取活跃会话"""
        return [
            {
                'username': session['username'],
                'role': session['role'],
                'login_time': session['login_time'],
                'last_activity': session['last_activity']
            }
            for session in self.sessions.values()
        ]

class PermissionManager:
    """权限管理器"""
    
    def __init__(self):
        self.permissions = {
            'admin': [
                'view_dashboard',
                'manage_users',
                'configure_system',
                'execute_queries',
                'modify_data',
                'view_logs',
                'manage_automation'
            ],
            'operator': [
                'view_dashboard',
                'execute_queries',
                'view_logs',
                'manage_automation'
            ],
            'viewer': [
                'view_dashboard',
                'view_logs'
            ]
        }
    
    def has_permission(self, role: str, permission: str) -> bool:
        """检查权限"""
        return permission in self.permissions.get(role, [])
    
    def get_role_permissions(self, role: str) -> List[str]:
        """获取角色权限"""
        return self.permissions.get(role, [])
    
    def add_permission(self, role: str, permission: str):
        """添加权限"""
        if role not in self.permissions:
            self.permissions[role] = []
        
        if permission not in self.permissions[role]:
            self.permissions[role].append(permission)
            logger.info(f"已为角色 {role} 添加权限: {permission}")
    
    def remove_permission(self, role: str, permission: str):
        """移除权限"""
        if role in self.permissions and permission in self.permissions[role]:
            self.permissions[role].remove(permission)
            logger.info(f"已从角色 {role} 移除权限: {permission}")

class AuditLogger:
    """审计日志管理器"""
    
    def __init__(self, log_file: str = "audit.log"):
        self.log_file = log_file
        
    def log_event(self, username: str, action: str, details: str, status: str = 'success'):
        """记录审计事件"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'username': username,
                'action': action,
                'details': details,
                'status': status
            }
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            logger.info(f"审计日志: {username} {action} - {status}")
        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")
    
    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志"""
        try:
            if not os.path.exists(self.log_file):
                return []
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            logs = []
            for line in lines[-limit:]:
                try:
                    log_entry = json.loads(line.strip())
                    logs.append(log_entry)
                except json.JSONDecodeError:
                    continue
            
            return logs[::-1]  # 返回最新的日志在前
        except Exception as e:
            logger.error(f"读取审计日志失败: {e}")
            return []

class SecurityManager:
    """安全管理器"""
    
    def __init__(self):
        self.user_manager = UserManager()
        self.permission_manager = PermissionManager()
        self.audit_logger = AuditLogger()
        
    def login(self, username: str, password: str) -> Optional[str]:
        """用户登录"""
        session_token = self.user_manager.authenticate(username, password)
        if session_token:
            self.audit_logger.log_event(username, 'login', '用户登录系统')
        else:
            self.audit_logger.log_event(username, 'login', '登录失败', 'failed')
        
        return session_token
    
    def logout(self, session_token: str):
        """用户登出"""
        session = self.user_manager.validate_session(session_token)
        if session:
            self.audit_logger.log_event(session['username'], 'logout', '用户登出系统')
        self.user_manager.logout(session_token)
    
    def check_permission(self, session_token: str, permission: str) -> bool:
        """检查权限"""
        session = self.user_manager.validate_session(session_token)
        if not session:
            return False
        
        has_perm = self.permission_manager.has_permission(session['role'], permission)
        
        if not has_perm:
            self.audit_logger.log_event(
                session['username'],
                'permission_denied',
                f"尝试访问无权限功能: {permission}",
                'denied'
            )
        
        return has_perm
    
    def get_user_info(self, session_token: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        session = self.user_manager.validate_session(session_token)
        if not session:
            return None
        
        return {
            'username': session['username'],
            'role': session['role'],
            'login_time': session['login_time'],
            'permissions': self.permission_manager.get_role_permissions(session['role'])
        }
    
    def create_user(self, current_session_token: str, username: str, password: str, role: str) -> bool:
        """创建用户（需要管理员权限）"""
        if not self.check_permission(current_session_token, 'manage_users'):
            return False
        
        current_user = self.get_user_info(current_session_token)
        if current_user:
            self.audit_logger.log_event(
                current_user['username'],
                'create_user',
                f"创建用户: {username}, 角色: {role}"
            )
        
        return self.user_manager.create_user(username, password, role)
    
    def get_audit_logs(self, session_token: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志（需要查看日志权限）"""
        if not self.check_permission(session_token, 'view_logs'):
            return []
        
        return self.audit_logger.get_audit_logs(limit)
    
    def get_system_status(self, session_token: str) -> Dict[str, Any]:
        """获取系统状态"""
        if not self.check_permission(session_token, 'view_dashboard'):
            return {}
        
        return {
            'total_users': len(self.user_manager.users),
            'active_sessions': len(self.user_manager.sessions),
            'audit_logs_count': len(self.audit_logger.get_audit_logs())
        }