import os
import sys
import asyncio
import logging
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)).replace("/src", ""))

from telegramify_markdown import telegramify
from telegramify_markdown.content import ContentType

from src.services.rag import init_rag_service, buscar_productos
from src.services.llm import LLMClient

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

RECOMMENDED_MODELS = ["llama3.1", "mistral", "qwen2.5", "phi3"]

FORCE_RELOAD_RAG = os.getenv("FORCE_RELOAD_RAG", "false").lower() == "true"

user_sessions = {}
llm_client: LLMClient = None

chat_model = None
chat_model_with_tools = None


# Patrones que indican CLARAMENTE una referencia contextual (sin ambigüedad)
CONTEXT_REFERENCE_PATTERNS = [
    r"\bopci[oó]n\s*(\d+)\b",          # "opción 1", "opcion 2"
    r"\bnumero\s*(\d+)\b",              # "numero 3"
    r"\bn[uuú]mero\s*(\d+)\b",         # "número 2"
    r"\bel\s+primero\b",               # "el primero"
    r"\bla\s+primera\b",               # "la primera"
    r"\bprimera\s+opci[oó]n\b",       # "primera opción"
    r"\bprimer\s+resultado\b",          # "primer resultado"
    r"\bese\s+producto\b",             # "ese producto"
    r"\besa\s+opci[oó]n\b",           # "esa opción"
    r"\bel\s+de\s+arriba\b",           # "el de arriba"
    r"\bla\s+anterior\b",              # "la anterior"
    r"\b[aá]quel\s+producto\b",        # "aquel producto" (requiere 'producto')
    r"\bel\s+anterior\b",              # "el anterior"
    r"\bese\b",                        # "ese" solo (sin 'catalogo', 'precio', etc.)
    r"\besa\b",                        # "esa" sola
]


def extract_context_reference(message: str, user_id: int, user_sessions: dict) -> tuple:
    import re
    msg_lower = message.lower().strip()
    last_search = None

    if user_id in user_sessions:
        last_search = user_sessions[user_id].get("last_search")

    if not last_search:
        return None, msg_lower

    # Si el mensaje contiene palabras de producto claras, el usuario está haciendo
    # una nueva búsqueda — NO aplicar contexto del turno anterior.
    product_terms = set(PRODUCT_KEYWORDS) - {"buscar", "buscame", "hay", "tienen", "tienes",
                                              "quiero", "necesito", "existe", "en stock",
                                              "disponible", "catalogo", "catálogo"}
    if any(kw in msg_lower for kw in product_terms):
        logger.debug(f"[CONTEXT] Mensaje contiene términos de producto → omitir contexto")
        return None, msg_lower

    for pattern in CONTEXT_REFERENCE_PATTERNS:
        match = re.search(pattern, msg_lower, re.IGNORECASE)
        if match:
            if match.groups():
                index = int(match.group(1)) - 1
                if 0 <= index < len(last_search):
                    ref_product = last_search[index]
                    ref_text = f"{ref_product.get('nombre', ref_product.get('sku', '?'))} (SKU: {ref_product.get('sku', '?')})"
                    logger.info(f"[CONTEXT] Referencia detectada: opción {match.group(0)} → {ref_text}")
                    return ref_product, msg_lower
            else:
                if last_search:
                    ref_product = last_search[0]
                    ref_text = f"{ref_product.get('nombre', ref_product.get('sku', '?'))} (SKU: {ref_product.get('sku', '?')})"
                    logger.info(f"[CONTEXT] Referencia detectada: '{match.group(0)}' → {ref_text}")
                    return ref_product, msg_lower

    return None, msg_lower


def rewrite_query_with_context(original_query: str, context_product: dict) -> str:
    if not context_product:
        return original_query
    
    sku = context_product.get("sku", "")
    nombre = context_product.get("nombre", "")
    categoria = context_product.get("categoria", "")
    
    context_hint = f"[Contexto: el usuario se refiere a '{nombre}' (SKU: {sku})] "
    return context_hint + original_query

SYSTEM_PROMPT = """Eres un asistente de almacén de refacciones automotrices. Tu trabajo es ayudar a los clientes a encontrar productos.

REGLAS:
1. Usa las herramientas SOLO cuando el usuario pregunte sobre productos específicos (filtros, bujías, precios, especificaciones, compatibilidad)
2. Si es una pregunta general o conversación, NO uses herramientas
3. Usa buscar_detalles_producto para consultas sobre productos
4. Usa buscar_producto_por_sku solo si el usuario proporciona un código SKU exacto

Ejemplos de cuándo USAR herramientas:
- "¿Tienen filtros?" → buscar_detalles_producto("filtros")
- "¿Precio del aceite?" → buscar_detalles_producto("aceite")
- "¿Es compatible con Honda Civic?" → buscar_detalles_producto("filtro aceite Honda Civic")
- "FRB-001" → buscar_producto_por_sku("FRB-001")

Ejemplos de cuándo NO usar herramientas:
- "Hola", "Gracias", "¿Cómo estás?", "¿Puedes ayudarme con algo más?"
- Preguntas sobre el almacén (horarios, ubicación)
- Conversación general

Si no necesitas herramientas, responde de manera amigable y natural."""


SUMMARY_PROMPT = """Eres un asistente de almacén de refacciones automotrices. El sistema ya realizó una búsqueda en el catálogo y encontró los siguientes productos.
Tu única tarea es presentar estos resultados de forma clara, amigable y organizada al usuario.
NO uses herramientas. NO llames funciones. Solo redacta una respuesta basada en los datos que se te proporcionan."""



def extract_rag_query(user_message: str) -> str:
    """Usa el LLM para extraer el término de búsqueda de producto del mensaje del usuario.
    Retorna 1-3 palabras clave para buscar en Qdrant. Si falla, retorna el mensaje original."""
    import re
    if chat_model is None:
        return user_message

    # Eliminar prefijo [Contexto:...] si existe antes de enviarlo al LLM
    message = re.sub(r"^\[Contexto:[^\]]*\]\s*", "", user_message.strip(), flags=re.IGNORECASE)

    try:
        extraction_prompt = (
            "Extrae SOLO el término de búsqueda de producto automotriz del siguiente mensaje. "
            "Responde ÚNICAMENTE con 1 a 4 palabras que describan el producto, sin explicaciones ni puntuación. "
            "Ejemplos: 'bujías', 'filtro de aceite', 'pastillas de freno delanteras', 'batería 12V'.\n\n"
            f"Mensaje: {message}"
        )
        result = chat_model.invoke([HumanMessage(content=extraction_prompt)])
        extracted = result.content.strip().lower()
        # Sanidad: si la respuesta es demasiado larga o vacía, usar el mensaje original
        if extracted and len(extracted.split()) <= 6:
            logger.info(f"[RAG EXTRACT] '{message}' → '{extracted}'")
            return extracted
    except Exception as e:
        logger.warning(f"[RAG EXTRACT] Error extrayendo término: {e}")

    return message



PRODUCT_KEYWORDS = [
    "filtro", "bujía", "bujia", "freno", "aceite", "batería", "bateria",
    "radiador", "correa", "cadena", "buje", "suspensión", "amortiguador",
    "pastilla", "tambor", "disco", "pinza", "manguera", "termostato",
    "bomba", "catalizador", "escape", "embrague", "platino", "cable",
    "precio", "costo", "cuánto", "cuanto", " cuesta", "SKU", "sku",
    "tienen", "buscar", "buscame", "necesito", "quiero", "buscar",
    "compatible", "motor", "vehículo", "vehiculo", "carro", "auto",
    "refacción", "refaccion", "pieza", "partes", "catalogo", "catálogo",
    "existe", "hay", "en stock", "disponible", "marca", "modelo"
]


def should_search(message: str) -> bool:
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in PRODUCT_KEYWORDS)


def check_services():
    errors = []
    warnings = []
    
    logger.info("[CHECK] Verificando Qdrant...")
    try:
        from src.services.rag import get_qdrant_client
        client = get_qdrant_client()
        exists = client.collection_exists("productos")
        logger.info(f"[CHECK] Qdrant OK - colección existe: {exists}")
        if not exists:
            errors.append("Qdrant: colección 'productos' no existe")
    except Exception as e:
        logger.error(f"[CHECK] Qdrant error: {e}")
        errors.append(f"Qdrant: {e}")
    
    logger.info("[CHECK] Verificando Ollama...")
    try:
        import requests
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        logger.info(f"[CHECK] Ollama OK - status: {response.status_code}")
        if response.status_code != 200:
            errors.append("Ollama: no responde correctamente")
        else:
            models_data = response.json()
            available_models = [m.get("name", "") for m in models_data.get("models", [])]
            logger.info(f"[CHECK] Modelos disponibles: {available_models}")
            
            if OLLAMA_MODEL not in available_models:
                warnings.append(f"Modelo '{OLLAMA_MODEL}' no está en Ollama. Disponibles: {available_models}")
            
            if OLLAMA_MODEL.startswith("gemma"):
                warnings.append(f"ADVERTENCIA: gemma tiene tool calling limitado. Considera usar: {RECOMMENDED_MODELS}")
    except Exception as e:
        logger.error(f"[CHECK] Ollama error: {e}")
        errors.append(f"Ollama: {e}")
    
    return errors, warnings


def init_llm():
    global chat_model, chat_model_with_tools
    
    logger.info(f"[INIT] LLM: {OLLAMA_MODEL} @ {OLLAMA_BASE_URL} (timeout={OLLAMA_TIMEOUT}s)")
    
    try:
        chat_model = ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
            temperature=0.3,
            timeout=OLLAMA_TIMEOUT,
        )
        logger.info("[INIT] ChatOllama creado OK")
    except Exception as e:
        logger.error(f"[INIT] Error creando ChatOllama: {e}")
        raise
    
    from src.tools.producto_tools import TOOLS
    chat_model_with_tools = chat_model.bind_tools(TOOLS)
    logger.info(f"[INIT] bind_tools aplicado - {len(TOOLS)} tools")
    
    logger.info("[INIT] LLM inicializado correctamente")


def init_rag_on_startup():
    global llm_client
    
    logger.info("[INIT] === Verificando servicios ===")
    errors, warnings = check_services()
    for err in errors:
        logger.error(f"[INIT] ERROR: {err}")
    for warn in warnings:
        logger.warning(f"[INIT] WARNING: {warn}")
    
    if errors:
        logger.error("[INIT] Servicios críticos no disponibles. El bot puede no funcionar correctamente.")
    
    logger.info("[INIT] === Iniciando servicio RAG ===")
    try:
        init_rag_service(force_reload=FORCE_RELOAD_RAG)
        logger.info("[INIT] RAG inicializado correctamente")
    except Exception as e:
        import traceback
        logger.error(f"[INIT] Error al inicializar RAG: {e}")
        logger.error(traceback.format_exc())
    
    logger.info("[INIT] === Inicializando cliente LLM ===")
    try:
        llm_client = LLMClient()
        logger.info("[INIT] LLMClient OK")
    except Exception as e:
        import traceback
        logger.error(f"[INIT] Error en LLMClient: {e}")
        logger.error(traceback.format_exc())
    
    logger.info("[INIT] === Inicializando ChatOllama ===")
    init_llm()
    logger.info(f"[INIT] chat_model_with_tools = {chat_model_with_tools}")
    
    return chat_model_with_tools


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*¡Hola!* 👋\n\n"
        "Soy el asistente de tu almacén de refacciones automotrices.\n\n"
        "*Puedo ayudarte con:*\n"
        "• Información de productos\n"
        "• Stock en almacenes\n"
        "• Consultas de ventas\n"
        "• Reportes\n\n"
        "¿En qué puedo ayudarte?",
        parse_mode="MarkdownV2"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Comandos disponibles:*\n"
        "/start - Iniciar conversación\n"
        "/help - Mostrar ayuda\n\n"
        "También puedes escribirme en lenguaje natural.",
        parse_mode="MarkdownV2"
    )


async def send_markdown_message(update: Update, text: str):
    results = await telegramify(text, max_message_length=4090)
    for item in results:
        if item.content_type == ContentType.TEXT:
            await update.message.reply_text(
                item.text,
                entities=[e.to_dict() for e in item.entities]
            )
        elif item.content_type == ContentType.PHOTO:
            await update.message.reply_photo(
                (item.file_name, item.file_data),
                caption=item.caption_text or None,
                caption_entities=[e.to_dict() for e in item.caption_entities] if item.caption_entities else None
            )
        elif item.content_type == ContentType.FILE:
            await update.message.reply_document(
                (item.file_name, item.file_data),
                caption=item.caption_text or None,
                caption_entities=[e.to_dict() for e in item.caption_entities] if item.caption_entities else None
            )


def invoke_with_retry(model, messages, max_retries=3, initial_delay=2):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"[INVOKE] Intento {attempt + 1}/{max_retries} - Mensajes: {len(messages)}")
            result = model.invoke(messages)
            logger.info(f"[INVOKE] Respuesta recibida OK - Tool calls: {len(result.additional_kwargs.get('tool_calls', []))}")
            return result
        except Exception as e:
            last_exception = e
            delay = initial_delay * (2 ** attempt)
            logger.warning(f"[INVOKE] Intento {attempt + 1}/{max_retries} falló: {type(e).__name__}: {e}")
            logger.warning(f"[INVOKE] Reintentando en {delay}s...")
            time.sleep(delay)
    
    logger.error(f"[INVOKE] Todos los intentos fallaron: {last_exception}")
    raise last_exception


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_sessions
    user_id = update.effective_user.id
    user_message = update.message.text
    
    logger.info(f"[HANDLE] User {user_id} | Mensaje: '{user_message}'")
    
    session = user_sessions.get(user_id, {"messages": [], "last_search": None})
    history = session.get("messages", [])
    logger.info(f"[HANDLE] Historial: {len(history)} mensajes | last_search: {session.get('last_search') is not None}")
    
    if chat_model_with_tools is None:
        logger.error("[HANDLE] ERROR: chat_model_with_tools es None!")
        await update.message.reply_text("Error: LLM no inicializado. Reinicia el bot.")
        return
    
    try:
        logger.info("[HANDLE] Extrayendo referencias contextuales...")
        context_product, clean_query = extract_context_reference(user_message, user_id, user_sessions)
        
        if context_product:
            search_query = rewrite_query_with_context(clean_query, context_product)
            logger.info(f"[HANDLE] Query reescrita: '{search_query}'")
        else:
            search_query = user_message
        
        logger.info("[HANDLE] Construyendo mensajes...")
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        messages.append(HumanMessage(content=search_query))
        
        logger.info(f"[HANDLE] Invocando LLM con {len(messages)} mensajes...")
        response = invoke_with_retry(chat_model_with_tools, messages)
        
        tool_calls = response.additional_kwargs.get("tool_calls", [])
        logger.info(f"[HANDLE] LLM respondió - Tool calls: {len(tool_calls)}")
        
        current_search_results = []
        
        if tool_calls:
            logger.info(f"[HANDLE] Ejecutando {len(tool_calls)} tools...")
            
            messages.append(response)
            
            from src.tools.producto_tools import TOOL_MAP
            import json
            
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args = tool_call["function"]["arguments"]
                
                logger.info(f"[HANDLE] Ejecutando tool: {tool_name} | args: {tool_args}")
                
                if tool_name in TOOL_MAP:
                    tool_func = TOOL_MAP[tool_name]
                    args_dict = json.loads(tool_args) if isinstance(tool_args, str) else tool_args
                    result = tool_func.invoke(args_dict)
                    logger.info(f"[HANDLE] Tool {tool_name} resultado: {result[:200]}...")
                    
                    if tool_name == "buscar_detalles_producto":
                        current_search_results = _parse_search_results_from_rag(args_dict.get("query", ""))
                    
                    messages.append(
                        HumanMessage(content=f"Tool result from {tool_name}: {result}")
                    )
                else:
                    logger.warning(f"[HANDLE] Tool desconocido: {tool_name}")
            
            logger.info("[HANDLE] Invocando LLM final...")
            final_response = invoke_with_retry(chat_model, messages)
            response_text = final_response.content
        else:
            if should_search(user_message):
                logger.info(f"[HANDLE] Mensaje parece ser sobre productos - forzando búsqueda")
                from src.tools.producto_tools import TOOL_MAP
                rag_query = search_query
                logger.info(f"[HANDLE] RAG query limpia: '{rag_query}'")
                tool_func = TOOL_MAP["buscar_detalles_producto"]
                result = tool_func.invoke({"query": rag_query})
                current_search_results = _parse_search_results_from_rag(rag_query)
                # Usar SUMMARY_PROMPT para evitar que el LLM confunda con tool calls
                summary_messages = [
                    SystemMessage(content=SUMMARY_PROMPT),
                    HumanMessage(content=f"El usuario preguntó: '{user_message}'\n\nResultados encontrados en el catálogo:\n\n{result}"),
                ]
                final_response = invoke_with_retry(chat_model, summary_messages)
                response_text = final_response.content if final_response.content else result
            else:
                logger.info("[HANDLE] Conversación general - usando respuesta directa del LLM")
                response_text = response.content
        
        logger.info(f"[HANDLE] Guardando en historial y actualizando sesión...")
        
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": response_text})
        
        if len(history) > 20:
            history = history[-20:]
        
        user_sessions[user_id] = {
            "messages": history,
            "last_search": current_search_results if current_search_results else session.get("last_search")
        }
        
        await send_markdown_message(update, response_text)
        logger.info("[HANDLE] Mensaje enviado OK")
        
    except Exception as e:
        logger.error(f"[HANDLE] ERROR: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("Tuve un problema al procesar tu mensaje. Intenta de nuevo.")


def _parse_search_results_from_rag(query: str) -> list:
    """Obtiene los resultados estructurados directos de Qdrant para guardar en sesión."""
    try:
        from src.services.rag import buscar_productos
        resultados = buscar_productos(query, top_k=5)
        return resultados  # lista de dicts con 'nombre', 'sku', 'categoria', etc.
    except Exception as e:
        logger.warning(f"[SESSION] No se pudieron guardar resultados RAG en sesión: {e}")
        return []


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")


def main():
    logger.info("Iniciando bot de Telegram...")
    
    chat_model_with_tools = init_rag_on_startup()
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    logger.info("Bot iniciado. Esperando mensajes...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()