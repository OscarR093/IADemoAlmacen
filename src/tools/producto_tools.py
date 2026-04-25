import logging
from typing import Optional

from langchain_core.tools import tool

from src.services.rag import buscar_productos, buscar_por_nombre_o_sku

logger = logging.getLogger(__name__)


@tool
def buscar_detalles_producto(query: str) -> str:
    """Busca productos del catálogo de refacciones automotrices y retorna información detallada.

    Utiliza esta herramienta cuando el usuario pregunte sobre:
    - Especificaciones técnicas de un producto
    - Descripción completa de un producto
    - Compatibilidad de piezas con vehículos
    - Información de precios de productos
    - Detalles de filtros, bujías, frenos, etc.

    Args:
        query: Términos de búsqueda del producto (puede ser nombre, SKU, o descripción)

    Returns:
        Returns información detallada del producto encontrado.
    """
    logger.info(f"Tool: buscar_detalles_producto - query: {query}")

    try:
        resultados = buscar_productos(query, top_k=5)

        if not resultados:
            return f"No encontré productos que coincidan con '{query}'. ¿Puedes dar más detalles?"

        respuesta = []
        for i, producto in enumerate(resultados, 1):
            specs = producto.get('especificaciones', '')
            compat = producto.get('compatibilidad', '')
            lineas = [
                f"## {i}. {producto['nombre']}",
                f"**SKU:** {producto['sku']}",
                f"**Categoría:** {producto['categoria']}",
                f"**Precio:** ${producto['precio_venta']:.2f}",
                f"",
                f"{producto['descripcion']}",
            ]
            if specs:
                lineas.append(f"\n**Especificaciones:** {specs}")
            if compat:
                lineas.append(f"**Compatibilidad:** {compat}")
            lineas.append(f"**Relevancia:** {producto['score']:.2f}")
            respuesta.append("\n".join(lineas))

        return "\n\n---\n\n".join(respuesta)

    except Exception as e:
        logger.error(f"Error en buscar_detalles_producto: {e}")
        return "Tuve un problema al buscar el producto. Intenta de nuevo."


@tool
def buscar_producto_por_sku(sku: str) -> str:
    """Busca un producto específico por su código SKU.

    Utiliza esta herramienta cuando el usuario proporcione un código SKU exacto
    (como FRB-001, FRB-002, etc.) para buscar un producto.

    Args:
        sku: Código SKU del producto (formato: FRB-XXX)

    Returns:
        Returns información del producto encontrado o mensaje de no encontrado.
    """
    logger.info(f"Tool: buscar_producto_por_sku - sku: {sku}")

    try:
        producto = buscar_por_nombre_o_sku(sku)

        if not producto:
            return f"No encontré el producto con SKU '{sku}'"

        return (
            f"## {producto['nombre']}\n"
            f"**SKU:** {producto['sku']}\n"
            f"**Categoría:** {producto['categoria']}\n"
            f"**Precio:** ${producto['precio_venta']:.2f}\n\n"
            f"{producto['descripcion']}"
        )

    except Exception as e:
        logger.error(f"Error en buscar_producto_por_sku: {e}")
        return "Tuve un problema al buscar el producto. Intenta de nuevo."


TOOLS = [buscar_detalles_producto, buscar_producto_por_sku]

TOOL_MAP = {
    "buscar_detalles_producto": buscar_detalles_producto,
    "buscar_producto_por_sku": buscar_producto_por_sku,
}