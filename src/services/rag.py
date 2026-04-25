import json
import logging
import os
import sys
from typing import Optional, List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from dotenv import load_dotenv

# LlamaIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.vector_stores.types import VectorStoreQuery

sys.path.insert(0, "/home/oscarr093/Proyectos/IaDemoAlmacen")
load_dotenv()

logger = logging.getLogger(__name__)

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "productos"
PRODUCTOS_JSON_PATH = os.getenv("PRODUCTOS_JSON_PATH", "db/productos_rag.json")

EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
MIN_SCORE = 0.55

# Singletons
_embed_model: Optional[HuggingFaceEmbedding] = None
_vector_store: Optional[QdrantVectorStore] = None


def get_embedding_model() -> HuggingFaceEmbedding:
    global _embed_model
    if _embed_model is None:
        logger.info(f"[RAG] Cargando modelo de embeddings: {EMBEDDING_MODEL}")
        _embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL)
    return _embed_model


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def get_vector_store(client: QdrantClient) -> QdrantVectorStore:
    """Retorna un QdrantVectorStore apuntando a la coleccion de productos."""
    global _vector_store
    if _vector_store is None:
        _vector_store = QdrantVectorStore(
            collection_name=COLLECTION_NAME,
            client=client,
        )
    return _vector_store


def load_json_documents(json_path: str) -> List[Dict[str, Any]]:
    full_path = "/home/oscarr093/Proyectos/IaDemoAlmacen/db/productos_rag.json"

    with open(full_path, "r", encoding="utf-8") as f:
        productos = json.load(f)

    documents = []
    for producto in productos:
        nombre = producto["nombre"]
        categoria = producto["categoria"]
        text_content = (
            f"{nombre}\n{nombre}\n{nombre}\n\n"
            f"Categoria: {categoria}\nCategoria: {categoria}\n"
            f"SKU: {producto['sku']}\n\n"
            f"Descripcion: {producto['descripcion']}\n\n"
            f"Especificaciones: {producto['especificaciones']}\n\n"
            f"Compatibilidad: {producto['compatibilidad']}"
        ).strip()

        documents.append(
            {
                "text": text_content,
                "id_producto": producto["id_producto"],
                "sku": producto["sku"],
                "nombre": nombre,
                "categoria": categoria,
                "precio_venta": producto["precio_venta"],
                "descripcion": producto["descripcion"],
                "especificaciones": producto["especificaciones"],
                "compatibilidad": producto["compatibilidad"],
            }
        )

    return documents


def init_rag_service(force_reload: bool = False):
    logger.info(f"[RAG] Inicializando... force_reload={force_reload}")

    client = get_qdrant_client()
    model = get_embedding_model()

    # Detectar dimension del modelo
    sample_vec = model.get_text_embedding("test")
    embedding_size = len(sample_vec)

    try:
        if force_reload and client.collection_exists(COLLECTION_NAME):
            logger.info(f"[RAG] Eliminando coleccion '{COLLECTION_NAME}'...")
            client.delete_collection(COLLECTION_NAME)
            global _vector_store
            _vector_store = None  # Resetear singleton
    except Exception as e:
        logger.warning(f"[RAG] Error al verificar coleccion: {e}")

    if not client.collection_exists(COLLECTION_NAME):
        logger.info(f"[RAG] Creando coleccion '{COLLECTION_NAME}'...")

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=embedding_size, distance=Distance.COSINE),
        )

        documents = load_json_documents(PRODUCTOS_JSON_PATH)
        logger.info(f"[RAG] Indexando {len(documents)} productos...")

        texts = [doc["text"] for doc in documents]
        embeddings = model.get_text_embedding_batch(texts, show_progress=False)

        points = [
            {"id": i, "vector": emb, "payload": doc}
            for i, (doc, emb) in enumerate(zip(documents, embeddings))
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.info(f"[RAG] Coleccion creada con {len(documents)} productos")
    else:
        logger.info(f"[RAG] Coleccion '{COLLECTION_NAME}' ya existe, omitiendo carga")


def buscar_productos(query: str, top_k: int = 5, min_score: float = MIN_SCORE) -> list:
    logger.info(f"[BUSCAR] query='{query}' top_k={top_k}")

    model = get_embedding_model()
    client = get_qdrant_client()
    vector_store = get_vector_store(client)

    # Embedding de la query via LlamaIndex (usa instruccion de busqueda para BGE)
    query_embedding = model.get_query_embedding(query)

    vsq = VectorStoreQuery(query_embedding=query_embedding, similarity_top_k=top_k)
    result = vector_store.query(vsq)

    productos_encontrados = []
    for node, score in zip(result.nodes, result.similarities or []):
        score = score or 0
        if score < min_score:
            logger.info(f"[BUSCAR] Descartando: {node.metadata.get('nombre', '?')} score={score:.3f}")
            continue

        payload = node.metadata
        producto = {
            "id_producto": payload.get("id_producto", ""),
            "sku": payload.get("sku", ""),
            "nombre": payload.get("nombre", ""),
            "categoria": payload.get("categoria", ""),
            "precio_venta": payload.get("precio_venta", 0),
            "descripcion": payload.get("descripcion") or payload.get("text", ""),
            "especificaciones": payload.get("especificaciones", ""),
            "compatibilidad": payload.get("compatibilidad", ""),
            "score": score,
        }
        productos_encontrados.append(producto)

    logger.info(f"[BUSCAR] Resultados: {len(productos_encontrados)}")
    return productos_encontrados


def buscar_por_nombre_o_sku(query: str) -> Optional[dict]:
    resultados = buscar_productos(query, top_k=1)
    if resultados and resultados[0]["score"] > 0.5:
        return resultados[0]
    return None