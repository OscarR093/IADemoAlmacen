# Agente de Almacén IA - Demo

Este proyecto es un bot conversacional para Telegram que actúa como asistente de refacciones automotrices. Utiliza un modelo LLM (Ollama) junto con una base de datos vectorial (Qdrant) para realizar **Búsqueda Aumentada por Generación (RAG)** y proveer información precisa sobre productos automotrices.

## Características

- 🤖 **Bot Conversacional:** Integración con Telegram usando `python-telegram-bot`.
- 🧠 **RAG con LlamaIndex Puro:** Utiliza `llama-index` y `HuggingFaceEmbedding` (`BAAI/bge-base-en-v1.5`) para generar embeddings localmente de alta calidad.
- 🔍 **Vector DB Local:** Backend de vectores robusto y rápido impulsado por `Qdrant` en Docker.
- 🛠️ **Tool Calling:** El LLM determina automáticamente cuándo buscar información específica usando Tools de `langchain_core`.
- 📝 **Markdown Nativo:** Renderizado enriquecido en Telegram vía `telegramify-markdown`.

## Estructura del Proyecto

```text
IaDemoAlmacen/
├── .env.example          # Variables de entorno (copiar a .env)
├── requirements.txt      # Dependencias Python actualizadas
├── docker/
│   └── docker-compose.yml# Qdrant vector database local
├── db/
│   └── productos_rag.json # Catálogo de productos para RAG
└── src/
    ├── bot.py            # Servidor del Bot de Telegram principal
    ├── services/
    │   ├── rag.py        # Motor RAG usando LlamaIndex + QdrantClient
    │   └── llm.py        # Abstracción de conexión a Ollama
    └── tools/
        └── producto_tools.py # Definición de Tools para el LLM
```

## Requisitos y Configuración

1. **Clonar e instalar dependencias:**
   Se recomienda usar un entorno virtual administrado con `conda` o `uv`:
   ```bash
   conda create -n reportesIA python=3.13
   conda activate reportesIA
   uv pip install -r requirements.txt
   ```

2. **Levantar Qdrant:**
   ```bash
   cd docker
   docker-compose up -d
   ```

3. **Variables de Entorno (`.env`):**
   Copia el `.env.example` a `.env` y configura tus opciones, especialmente:
   - `TELEGRAM_BOT_TOKEN`: Tu token generado con BotFather
   - `OLLAMA_BASE_URL`: Url de tu instancia de Ollama (ej. `http://localhost:11434`)
   - `FORCE_RELOAD_RAG`: En `true` si quieres recrear la colección en cada reinicio.

## Ejecución

Simplemente arranca el script principal:

```bash
conda activate reportesIA
python src/bot.py
```
El agente inicializará LlamaIndex, verificará Qdrant y quedará a la espera de mensajes de Telegram.

## Flujo de Trabajo (Workflow)

1. El **Usuario** envía un mensaje en lenguaje natural.
2. El bot utiliza el **LLM de Ollama** para deducir la intención.
3. Si el usuario pregunta por refacciones, el LLM decide usar una `Tool` (ej: `buscar_detalles_producto`).
4. La petición llega al servicio **RAG** (`rag.py`) procesando la query con LlamaIndex y enviándola a **Qdrant**.
5. Qdrant devuelve la similitud del coseno de los productos.
6. El LLM ensambla y formatea la **respuesta final** al usuario mediante Telegram.
