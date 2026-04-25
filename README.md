# Agente de Almacén IA - Demo

Este proyecto es un bot conversacional para Telegram que actúa como asistente de refacciones automotrices. Utiliza un modelo LLM (Ollama) junto con una base de datos vectorial (Qdrant) para realizar **Búsqueda Aumentada por Generación (RAG)** y proveer información precisa sobre productos automotrices.

## Características

- 🤖 **Bot Conversacional:** Integración con Telegram usando `python-telegram-bot`.
- 🧠 **RAG con LlamaIndex Puro:** Utiliza `llama-index` y `HuggingFaceEmbedding` (`BAAI/bge-base-en-v1.5`) para generar embeddings localmente de alta calidad.
- 🔍 **Vector DB Local:** Backend de vectores robusto y rápido impulsado por `Qdrant` en Docker.
- 🛠️ **Tool Calling Inteligente:** El LLM determina automáticamente cuándo buscar información específica usando Tools de `langchain_core`, con fallback forzado cuando se detectan palabras clave de producto.
- 📝 **Markdown Nativo:** Renderizado enriquecido en Telegram vía `telegramify-markdown`.
- 🔄 **Sistema de Contexto:** Mantiene historial de conversación y detecta referencias implícitas como "el primero", "esa opción", "número 2".
- ⚙️ **Resilient y Robusto:** Validación de servicios al inicio, reintentos con backoff exponencial, logging detallado y manejo de errores gracioso.
- 🔁 **Sesiones de Usuario:** Maneja contexto por usuario con historial de últimos 10 intercambios.

## Estructura del Proyecto

```
IaDemoAlmacen/
├── .env.example          # Variables de entorno (copiar a .env)
├── requirements.txt    # Dependencias Python
├── AGENTS.md          # Documentación detallada para agentes
├── reportissue.md     # Plantilla para reportar issues
├── setup.sh           # Script de inicialización
├── docker/
│   └── docker-compose.yml  # Qdrant vector database
├── db/
│   ├── almacen.db           # Base de datos SQLite
│   ├── esquema.sql         # Esquema de tablas
│   ├── seed_catalogos.sql  # Datos iniciales de catálogos
│   ├── seed_productos.sql  # Datos iniciales de productos
│   ├── seed_ventas.sql     # Datos iniciales de ventas
│   └── productos_rag.json  # Datos para embeddar en Qdrant
└── src/
    ├── bot.py              # Bot de Telegram conversacional
    ├── services/
    │   ├── rag.py         # Servicio RAG (Qdrant + LlamaIndex + sentence-transformers)
    │   └── llm.py        # Abstracción LLM (Ollama/OpenAI)
    └── tools/
        └── producto_tools.py  # Tools para LangChain
```

## Requisitos y Configuración

### 1. Clonar e instalar dependencias:
Se recomienda usar un entorno virtual administrado con `conda`:
```bash
conda create -n reportesIA python=3.13
conda activate reportesIA
pip install -r requirements.txt
```

### 2. Levantar Qdrant:
```bash
cd docker
docker-compose up -d
```

### 3. Variables de Entorno (`.env`):
Copia el `.env.example` a `.env` y configura tus opciones, especialmente:
- `TELEGRAM_BOT_TOKEN`: Tu token generado con BotFather
- `OLLAMA_BASE_URL`: Url de tu instancia de Ollama (ej. `http://localhost:11434`)
- `OLLAMA_MODEL`: Modelo a usar (default: `gemma4`)
- `FORCE_RELOAD_RAG`: En `true` si quieres recrear la colección en cada reinicio.
- `LLM_PROVIDER`: Proveedor LLM (`ollama` o `openai`)
- `OPENAI_API_KEY`: Clave de API de OpenAI (si se usa OpenAI)

## Ejecución

Simplemente arranca el script principal:
```bash
conda activate reportesIA
python src/bot.py
```

El agente inicializará LlamaIndex, verificará Qdrant y Ollama, y quedará a la espera de mensajes de Telegram.

## Flujo de Trabajo (Workflow)

1. **Recepción**: El usuario envía un mensaje en lenguaje natural.
2. **Pre-procesamiento**: El bot verifica referencias contextuales (ej: "el primero", "esa opción") usando el historial de conversación.
3. **Detección de Intención**: 
   - Primer filtro: Se buscan palabras clave específicas de productos (filtro, bujía, aceite, etc.)
   - Segundo filtro: El LLM extrae el término de búsqueda optimizado para RAG
   - Tercer filtro: Se aplica contexto de conversación si es apropiado
4. **Decisión de Herramientas**: El LLM decide si usar herramientas basado en la intención detectada.
5. **Ejecución de Búsqueda** (si es necesario):
   - Se usa `buscar_detalles_producto` para búsquedas semánticas
   - Se usa `buscar_producto_por_sku` para búsquedas por SKU exacto
   - Si el LLM no usa herramientas pero se detectaron palabras clave, se fuerza la búsqueda
6. **Generación de Respuesta**:
   - Si se usaron herramientas: El LLM genera una respuesta final basada en los resultados
   - Si no se usaron herramientas: Respuesta directa del LLM (conversación general)
   - En caso de forzado: Se usa un prompt de resumen para evitar confusión
7. **Entrega**: La respuesta se formatea con `telegramify-markdown` y se envía a Telegram.
8. **Actualización de Sesión**: Se guarda el historial y los últimos resultados de búsqueda para referencia futura.

### Manejo de Errores y Resiliencia
- **Validación de Servicios**: Al iniciar, verifica que Qdrant y Ollama estén disponibles
- **Reintentos**: Las llamadas al LLM usan backoff exponencial (2s, 4s, 8s) ante fallos
- **Fallbacks**: Si el modelo recomendado no está disponible, se advierte pero continúa
- **Logging**: Trazabilidad detallada para depuración

## Fases del Proyecto

| Fase | Descripción | Estado |
|------|-----------|--------|
| 1 | Diseño DB SQLite | Completado |
| 2 | Bot conversacional | Completado |
| 3 | RAG con Qdrant + LlamaIndex | Completado |
| 4 | SQL con VannaAI | Pendiente |
| 5 | Reportes con templates | Pendiente |

## Detalles Técnicos

### RAG Service (`src/services/rag.py`)
- Embeddings: `BAAI/bge-base-en-v1.5` mediante LlamaIndex
- Vector Store: Qdrant con similitud coseno
- Umbral de relevancia: 0.55 (configurable)
- Funciones principales:
  - `init_rag_service(force_reload=False)`: Inicializa/carga embeddings
  - `buscar_productos(query, top_k=5, min_score=0.55)`: Búsqueda semántica
  - `buscar_por_nombre_o_sku(query)`: Búsqueda exacta por nombre/SKU

### LLM Service (`src/services/llm.py`)
- Proveedores soportados: Ollama y OpenAI
- Fallback automático: Si OpenAI no está configurado, usa Ollama
- Abstracción: `LLMClient` con métodos `invoke` y `invoke_with_history`

### Bot Logic (`src/bot.py`)
- Tool Calling: Integración con LangChain para decidir cuándo usar herramientas
- Contexto Conversacional: Historial de últimos 10 mensajes por usuario
- Patrones de Referencia: Detecta frases como "el primero", "esa opción", "número 2"
- Sistema de Reintentos: Backoff exponencial para llamadas al LLM
- Renderizado: Uso de `telegramify-markdown` para compatibilidad con Telegram
- Sesiones: Almacenamiento en memoria de historial y últimos resultados por usuario