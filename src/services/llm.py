import os
import logging
from typing import Optional, List, Dict, Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

try:
    from langchain_ollama import ChatOllama
    logger.info("ChatOllama imported successfully")
except ImportError as e:
    logger.error(f"ChatOllama import failed: {e}")
    ChatOllama = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")


class LLMClient:
    def __init__(self, provider: str = None):
        self.provider = provider or LLM_PROVIDER
        self.client = None
        self._init_client()

    def _init_client(self):
        if self.provider == "openai":
            if not OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY no configurado, usando Ollama")
                self.provider = "ollama"
            else:
                logger.info(f"Inicializando ChatOpenAI con modelo: {OPENAI_MODEL}")
                self.client = ChatOpenAI(
                    api_key=OPENAI_API_KEY,
                    model=OPENAI_MODEL,
                    temperature=0.7,
                )
                return

        if self.provider == "ollama":
            logger.info(f"Inicializando ChatOllama con modelo: {OLLAMA_MODEL}")
            self.client = ChatOllama(
                base_url=OLLAMA_BASE_URL,
                model=OLLAMA_MODEL,
                temperature=0.7,
            )
        else:
            raise ValueError(f"Proveedor LLM no soportado: {self.provider}")

    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        langchain_messages = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(BaseMessage(content=content, type="ai"))
        
        try:
            response = self.client.invoke(langchain_messages)
            return response.content
        except Exception as e:
            logger.error(f"Error al invocar LLM: {e}")
            return "Lo siento, tuve un problema al procesar tu mensaje. Intenta de nuevo."

    def invoke_with_history(
        self,
        user_message: str,
        history: List[Dict[str, str]] = None,
        system_prompt: str = None,
    ) -> str:
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if history:
            messages.extend(history)
        
        messages.append({"role": "user", "content": user_message})
        
        return self.invoke(messages)

    def __repr__(self):
        return f"LLMClient(provider={self.provider}, model={self.client.model_name if self.client else 'N/A'})"


def get_llm_client() -> LLMClient:
    return LLMClient()