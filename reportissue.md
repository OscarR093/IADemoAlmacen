# Reporte de Issue: Incompatibilidad entre llama-index-vector-stores-qdrant y qdrant-client

## Fecha
25 de Abril 2026

## Entorno

### Paquetes instalados
```
llama-index                        0.14.21
llama-index-core                   0.14.21
llama-index-embeddings-huggingface 0.7.0
llama-index-embeddings-openai      0.6.0
llama-index-instrumentation        0.5.0
llama-index-llms-ollama            0.10.1
llama-index-llms-openai            0.7.5
llama-index-vector-stores-qdrant   0.10.0
llama-index-workflows              2.20.0
qdrant-client                      1.17.1
```

### Python
- Versión: 3.13.11
- Ubicación: /opt/miniconda3/bin/python

### Entorno virtual
- Conda environment: reportesIA

## Descripción del Problema

Al intentar usar llama-index con QdrantVectorStore para realizar búsquedas, se produce un error:

```
AttributeError: 'QdrantClient' object has no attribute 'search'
```

## Traza del Error

```
File "...llama_index/vector_stores/qdrant/base.py", line 908, in query
    response = self._client.search(
               ^^^^^^^^^^^^^^^^^^^
AttributeError: 'QdrantClient' object has no attribute 'search'
```

Call stack completo:
```
llama_index.core.indices.vector_store.retrievers.retriever.py:115 in _get_nodes_with_embeddings
    return self._get_nodes_with_embeddings(query_bundle)
llama_index.core.base.base_retriever.py:216 in _retrieve
    nodes = self._retrieve(query_bundle)
llama_index.core.query_engine.retriever_query_engine.py:149 in retrieve
    nodes = self._retriever.retrieve(query_bundle)
llama_index.core.query_engine.retriever_query_engine.py:196 in _query
    nodes = self.retrieve(query_bundle)
llama_index.core.base.base_query_engine.py:44 in query
    query_result = self._query(str_or_query_bundle)
llama_index.core.query_engine.retriever_query_engine.py:196 in _query
    nodes = self.retrieve(query_bundle)
llama_index_instrumentation/dispatcher.py:413 in wrapper
    result = func(*args, **kwargs)
src/services/rag.py:205 in buscar_productos
    response = query_engine.query(query)
```

## Análisis

### Método que falla

El método `QdrantVectorStore.query()` en llama-index intenta llamar a `self._client.search()` en la línea 908 de `base.py`.

### Métodos disponibles en QdrantClient 1.17.1

Al inspeccionar la clase QdrantClient:

```python
from qdrant_client import QdrantClient
methods = [m for m in dir(QdrantClient) if 'query' in m.lower() or 'search' in m.lower()]
```

Resultado:
- `query`
- `query_batch`
- `query_batch_points`
- `query_points`
- `query_points_groups`

**No existe `search()` en qdrant-client 1.17.1**

## Contexto del Código

### Código que falla (llama-index-vector-stores-qdrant 0.10.0)

ubicación: `/home/oscarr093/.local/lib/python3.13/site-packages/llama_index/vector_stores/qdrant/base.py`

```python
def query(
    self,
    query: VectorStoreQuery,
    **kwargs: Any,
) -> VectorStoreQueryResult:
    query_embedding = cast(List[float], query.query_embedding)
    # ... filtering logic ...
    
    # Línea 1154 (versión actual del código)
    response = self._client.query_points(
        collection_name=self.collection_name,
        query=query_embedding,
        using=self.dense_vector_name,
        limit=query.similarity_top_k,
        query_filter=query_filter,
    )
```

**Observación:** El código actual en el archivo fuente usa `query_points()`, no `search()`.

El error en la traza indica línea 908 con `search()`, pero el código actual muestra `query_points()` en línea 1154.
Esto sugiere que el bytecode cacheado (.pyc) puede estar desincronizado con el código fuente.

## Versiones Probadas

| Paquete | Versión | Resultado |
|--------|--------|---------|
| llama-index-vector-stores-qdrant | 0.10.0 | Error |
| qdrant-client | 1.17.1 | Error (sin método search) |
| qdrant-client | 1.16.x | Sin probar |
| qdrant-client | < 1.10.x | Sin probar |

## Alternativa que funciona

La implementación directa con sentence-transformers + qdrant-client (sin usar QdrantVectorStore de llama-index) funciona correctamente:

```python
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
MIN_SCORE = 0.55

model = SentenceTransformer(EMBEDDING_MODEL)
client = QdrantClient(host="localhost", port=6333)

# Buscar
query_embedding = model.encode(query, convert_to_numpy=True).tolist()
results = client.query_points(
    collection_name="productos",
    query=query_embedding,
    limit=5,
)
```

Esta implementación retorna correctamente los productos de bujías:
- Bujía de iridio premium (score=0.679)
- Cable de bujía juegos 4pzs (score=0.671)
- Bujía de ignición platino (score=0.657)

## Archivos Relevantes

- Archivo problemático: `llama_index/vector_stores/qdrant/base.py`
- Ubicación: `/home/oscarr093/.local/lib/python3.13/site-packages/llama_index/vector_stores/qdrant/base.py`
- Línea aproximada del error según traza: 908
- Línea en código fuente actual: ~1154

## Notas Adicionales

1. La limpieza de cache de Python (`__pycache__`) no resolvió el problema
2. Intentar reinstalar (`pip install --force-reinstall`) no resolvió el problema
3. El problema persiste con `force_reload=True` y `force_reload=False`