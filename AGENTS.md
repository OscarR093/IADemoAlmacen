# Agente de Almacén - Documentación del Proyecto

## Estructura del Proyecto

```
IaDemoAlmacen/
├── .env.example          # Variables de entorno (copiar a .env)
├── requirements.txt    # Dependencias Python
├── AGENTS.md          # Este archivo
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

## Configuración

### Variables de Entorno (.env)
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=tu_token

# Ollama LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4

# Qdrant (RAG)
QDRANT_HOST=localhost
QDRANT_PORT=6333
FORCE_RELOAD_RAG=false
PRODUCTOS_JSON_PATH=db/productos_rag.json

# Database
DATABASE_PATH=db/almacen.db

# LLM Provider (opcional para producción)
LLM_PROVIDER=ollama
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4
```

### Docker - Levantar Qdrant
```bash
cd docker
docker-compose up -d
```

### Instalar Dependencias
```bash
pip install -r requirements.txt
```

### Ejecutar el Bot
```bash
conda activate reportesIA
python src/bot.py
```

## Fases del Proyecto

| Fase | Descripción | Estado |
|------|-----------|--------|
| 1 | Diseño DB SQLite | Completado |
| 2 | Bot conversacional | Completado |
| 3 | RAG con Qdrant + LlamaIndex | Completado |
| 4 | SQL con VannaAI | Pendiente |
| 5 | Reportes con templates | Pendiente |

## Dependencias

```
python-telegram-bot>=21.0
langchain-core>=0.2.43
sqlalchemy>=2.0.35
python-dotenv==1.0.1
pydantic>=2.11.5
requests
telegramify-markdown>=1.1.0
llama-index>=0.12.0
llama-index-embeddings-huggingface>=0.4.0
llama-index-vector-stores-qdrant>=0.10.0
qdrant-client>=1.7.0
langchain-community>=0.2.0
langchain-ollama>=0.1.0
sentence-transformers>=2.2.0
```

## Módulos

### src/services/rag.py
- `init_rag_service(force_reload=False)` - Inicializa/carga embeddings en Qdrant usando LlamaIndex
- `buscar_productos(query, top_k=5, min_score=0.55)` - Búsqueda semántica de productos con filtrado por score
- `buscar_por_nombre_o_sku(query)` - Busca por nombre o SKU exacto (retorna el mejor match si score > 0.5)

### src/services/llm.py
- `LLMClient` - Abstracción de LLM (soporta Ollama y OpenAI con fallback automático)
- `get_llm_client()` - Factory para obtener cliente LLM configurado

### src/tools/producto_tools.py
- `buscar_detalles_producto` - Tool para buscar información de productos mediante RAG
- `buscar_producto_por_sku` - Tool para buscar producto específico por SKU

### src/bot.py
- Usa LangChain con tool calling para determinar cuándo buscar información
- Integración con telegramify-markdown para renderizar mensajes en Telegram
- Sistema de contexto para referencias a búsquedas previas (ej: "el primero", "esa opción")
- Manejo de sesiones de usuario para mantener historial y último search
- Validación de servicios al inicio (Qdrant, Ollama)
- Reintentos automáticos con backoff exponencial para llamadas al LLM

## Workflow

```
Usuario → Bot → LLM (con tools)
              ↓
      ¿Necesita buscar producto? (detección vía palabras clave + LLM)
              ↓ (sí/no)
   buscar_detalles_producto → Qdrant → Embeddings (LlamaIndex)
              ↓
      LLM genera respuesta final (o resumen directo si se forzaron tools)
              ↓
      telegramify → Usuario (con soporte para markdown, fotos, files)
```

### Detalles de Implementación

1. **Detección de Intención**: 
   - Primer filtro: palabras clave específicas de productos (filtro, bujía, aceite, etc.)
   - Segundo filtro: LLM extrae término de búsqueda optimizado para RAG
   - Tercer filtro: sistema de contexto para referencias implícitas a búsquedas previas

2. **Tool Calling**:
   - El LLM decide automáticamente cuándo usar `buscar_detalles_producto` o `buscar_producto_por_sku`
   - Fallback: si se detectan palabras clave de producto pero LLM no usa tools, se fuerza la búsqueda

3. **Contexto de Conversación**:
   - Sistema mantiene historial de últimos 10 intercambios por usuario
   - Detecta referencias contextuales como "el primero", "esa opción", "número 2"
   - Reescribe queries incorporando contexto cuando es apropiado

4. **Manejo de Errores y Salud**:
   - Verificación de servicios al inicio (Qdrant collections, Ollama availability)
   - Advertencias si el modelo recomendado no está disponible
   - Sistema de reintentos con backoff exponencial para llamadas al LLM
   - Logging detallado para depuración