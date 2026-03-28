from __future__ import annotations

from dataclasses import dataclass

from config import LLM_PROVIDER, OPENAI_API_KEY, OLLAMA_BASE_URL, OLLAMA_MODEL

from langchain_core.messages import HumanMessage


@dataclass(frozen=True)
class LLMResult:
    text: str


class MockLLM:
    """模拟LLM，在没有API Key时使用"""
    
    def invoke(self, messages):
        if isinstance(messages, list) and len(messages) > 0:
            prompt = messages[0].content if hasattr(messages[0], 'content') else str(messages[0])
        else:
            prompt = str(messages)
        
        # 根据提示词生成智能响应
        if "架构设计" in prompt:
            return """## 🏗️ 架构设计分析

### 推荐架构：微服务五层架构
1. **前端层**：Streamlit Web界面，提供用户交互
2. **API层**：FastAPI RESTful API，处理业务逻辑
3. **业务层**：核心业务逻辑模块
4. **数据层**：数据库访问和缓存管理
5. **AI层**：LLM集成和智能分析

### 技术选型理由
- **Streamlit**：快速构建数据应用，适合竞赛项目
- **FastAPI**：高性能异步框架，适合Web服务
- **MySQL**：成熟稳定，社区支持好
- **Redis**：缓存热点数据，提升性能

### 创新亮点
- 双重功能集成设计
- AI与数据库深度融合
- 模块化可扩展架构"""
        
        elif "数据库设计" in prompt:
            return """## 🗄️ 数据库设计分析

### 核心数据表设计
1. **用户表**：用户信息、权限管理
2. **项目表**：项目信息、状态管理
3. **对话历史表**：AI对话记录
4. **监控数据表**：性能指标数据
5. **任务调度表**：自动化运维任务

### 索引优化策略
- 主键索引：所有表的主键
- 外键索引：关联查询优化
- 复合索引：常用查询字段组合
- 全文索引：文档内容搜索

### 安全设计
- 用户认证和权限控制
- 数据加密存储
- SQL注入防护
- 操作审计日志"""
        
        elif "Demo剧本" in prompt or "演示" in prompt:
            return """## 🎭 Demo演示剧本

### 演示流程（15分钟）
1. **开场介绍**（2分钟）：项目背景和创新亮点
2. **架构展示**（3分钟）：系统架构和技术选型
3. **功能演示**（7分钟）：核心功能展示
4. **技术亮点**（2分钟）：关键技术实现
5. **总结展望**（1分钟）：项目成果和未来规划

### 演示技巧
- 使用震撼的开场数据
- 突出技术创新点
- 展示用户友好体验
- 准备应急预案"""
        
        else:
            # 通用智能响应
            return f"""## 🤖 AI智能分析

基于您的需求分析，这是一个非常有价值的项目！

### 项目亮点
- **技术创新**：结合AI和数据库技术
- **实用价值**：解决实际问题
- **竞赛优势**：技术深度和应用广度兼备

### 建议方案
1. 采用现代化的技术栈
2. 设计模块化系统架构
3. 注重用户体验设计
4. 考虑可扩展性和维护性

### 开发建议
- 分阶段实施，优先核心功能
- 建立完善的测试机制
- 注重代码质量和文档

这是一个很有潜力的项目，期待看到您的实现！"""


def get_chat_model():
    """
    依据环境变量 LLM_PROVIDER 加载 Chat LLM。
    - openai: 需要 OPENAI_API_KEY
    - ollama: 需要本机 Ollama 可用
    - 如果都没有，使用备用方案
    """
    provider = LLM_PROVIDER

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if not OPENAI_API_KEY.strip():
            # 如果没有API Key，尝试使用Ollama作为备用
            print("⚠️ OpenAI API Key未设置，尝试使用Ollama作为备用方案...")
            provider = "ollama"
        else:
            try:
                # 测试OpenAI API是否可用
                import openai
                openai.api_key = OPENAI_API_KEY
                
                # 简单的API测试
                test_response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5
                )
                
                # 如果测试成功，返回ChatOpenAI
                return ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
                
            except Exception as e:
                print(f"⚠️ OpenAI API调用失败: {e}")
                print("⚠️ 尝试使用Ollama作为备用方案...")
                provider = "ollama"

    if provider == "ollama":
        # langchain-ollama（新版本）通常放在 langchain_ollama
        try:
            from langchain_ollama import ChatOllama
            
            # 测试Ollama是否可用
            import requests
            try:
                response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
                if response.status_code == 200:
                    return ChatOllama(
                        model=OLLAMA_MODEL,
                        temperature=0.2,
                        base_url=OLLAMA_BASE_URL,
                    )
            except:
                print("⚠️ Ollama服务不可用，使用备用方案...")
                
        except Exception as e:
            print(f"⚠️ 未能加载 Ollama LLM: {e}")

    # 备用方案：使用智能模拟响应
    print("⚠️ 使用智能模拟响应（备用方案）")
    return MockLLM()


def invoke_llm(messages) -> str:
    """
    messages 可以是：
    - LangChain messages list（最常见）
    - 纯字符串 prompt（这里会自动包成 HumanMessage）
    """
    llm = get_chat_model()

    payload = messages
    if isinstance(messages, str):
        payload = [HumanMessage(content=messages)]

    resp = llm.invoke(payload)
    return getattr(resp, "content", str(resp))

