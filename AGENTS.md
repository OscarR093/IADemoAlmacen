# Agente de Almacén - Documentación del Proyecto

## Estructura del Proyecto

```
IaDemoAlmacen/
├── .env.example          # Variables de entorno (copiar a .env)
├── requirements.txt    # Dependencias Python
├── AGENTS.md          # Este archivo
├── docker/
│   └── docker-compose.yml  # Qdrant vector database
├── db/
│   ├── almacen.db           # Base de datos SQLite
│   ├── esquema.sql         # Esquema de tablas
│   ├── seed_*.sql         # Datos iniciales
│   └── productos_rag.json  # Datos para embeddar en Qdrant
└── src/
    ├── bot.py              # Bot de Telegram conversacional
    ├── services/
    │   ├── rag.py         # Servicio RAG (Qdrant + sentence-transformers)
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
| 3 | RAG con Qdrant + LangChain | Completado |
| 4 | SQL con VannaAI | Pendiente |
| 5 | Reportes con templates | Pendiente |

## Dependencias

```
python-telegram-bot==20.8
langchain-core>=0.2.43
langchain>=0.2.0
langchain-community>=0.2.0
langchain-ollama
langchain-openai
langchain
llama-index>=0.10.0
llama-index-vector-stores-qdrant>=0.1.0
qdrant-client>=1.7.0
sentence-transformers>=2.2.0
sqlalchemy==2.0.35
python-dotenv==1.0.1
pydantic==2.9.2
requests
telegramify-markdown>=1.1.0
```

## Módulos

### src/services/rag.py
- `init_rag_service(force_reload=False)` - Inicializa/carga embeddings en Qdrant
- `buscar_productos(query, top_k=5)` - Búsqueda semántica de productos
- `buscar_por_nombre_o_sku(query)` - Busca por nombre o SKU exacto

### src/services/llm.py
- `LLMClient` - Abstracción de LLM (soporta Ollama y OpenAI)
- `get_llm_client()` - Factory para obtener cliente

### src/tools/producto_tools.py
- `buscar_detalles_producto` - Tool para buscar información de productos
- `buscar_producto_por_sku` - Tool para buscar por SKU

### src/bot.py
- Usa LangChain con tool calling
- Integration con telegramify-markdown para renderizar markdown
- Detección automática de intención via LLM

## Workflow

```
Usuario → Bot → LLM (con tools)
              ↓
         ¿Necesita buscar producto?
              ↓ (sí/no)
         buscar_detalles_producto → Qdrant → Embeddings
              ↓
         LLM genera respuesta final
              ↓
         telegramify → Usuario
```