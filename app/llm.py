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
    """
    provider = LLM_PROVIDER

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if not OPENAI_API_KEY.strip():
            raise RuntimeError(
                "OPENAI_API_KEY is empty. 请在 .env 或系统环境变量设置后再执行。"
            )
        return ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    if provider == "ollama":
        # langchain-ollama（新版本）通常放在 langchain_ollama
        try:
            from langchain_ollama import ChatOllama
        except Exception as e:
            raise RuntimeError(
                f"未能加载 Ollama LLM（langchain_ollama）。请确认已安装依赖。原始错误: {e}"
            )

        return ChatOllama(
            model=OLLAMA_MODEL,
            temperature=0.2,
            base_url=OLLAMA_BASE_URL,
        )

    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")


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

