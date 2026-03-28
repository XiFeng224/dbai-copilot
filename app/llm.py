from __future__ import annotations

from dataclasses import dataclass

from config import LLM_PROVIDER, OPENAI_API_KEY, OLLAMA_BASE_URL, OLLAMA_MODEL

from langchain_core.messages import HumanMessage


@dataclass(frozen=True)
class LLMResult:
    text: str


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
            return ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

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

    # 备用方案：使用简单的模拟响应
    print("⚠️ 使用备用方案（模拟响应）")
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

