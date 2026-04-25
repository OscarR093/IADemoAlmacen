-- Esquema completo para base de datos de almacén de refacciones automotrices

-- Catálogos base
CREATE TABLE IF NOT EXISTS almacenes (
    id_almacen TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    ubicacion TEXT,
    capacidad_total INTEGER,
    capacidad_usada INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS proveedores (
    id_proveedor TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    ubicacion TEXT,
    tiempo_entrega_dias INTEGER DEFAULT 3,
    activo BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS clientes (
    id_cliente TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    rfc TEXT,
    direccion TEXT,
    email TEXT,
    activo BOOLEAN DEFAULT 1
);

-- Productos master
CREATE TABLE IF NOT EXISTS productos (
    id_producto TEXT PRIMARY KEY,
    sku TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    id_proveedor TEXT REFERENCES proveedores(id_proveedor),
    precio_compra REAL,
    precio_venta REAL,
    categoria TEXT,
    activo BOOLEAN DEFAULT 1
);

-- Stock por almacén
CREATE TABLE IF NOT EXISTS inventario (
    id_producto TEXT REFERENCES productos(id_producto),
    id_almacen TEXT REFERENCES almacenes(id_almacen),
    stock INTEGER DEFAULT 0,
    stock_en_curso INTEGER DEFAULT 0,
    PRIMARY KEY (id_producto, id_almacen)
);

-- Historial de inventario (auditoría)
CREATE TABLE IF NOT EXISTS inventario_historial (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto TEXT,
    id_almacen TEXT,
    cambio_stock INTEGER,
    cambio_stock_en_curso INTEGER,
    motivo TEXT,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Ventas
CREATE TABLE IF NOT EXISTS ventas (
    id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto TEXT REFERENCES productos(id_producto),
    id_almacen TEXT REFERENCES almacenes(id_almacen),
    id_cliente TEXT REFERENCES clientes(id_cliente),
    cantidad INTEGER,
    precio_unitario REAL,
    total REAL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Descripciones extensas para RAG
CREATE TABLE IF NOT EXISTS producto_descripciones (
    id_producto TEXT PRIMARY KEY REFERENCES productos(id_producto),
    descripcion TEXT,
    especificaciones TEXT,
    compatibilidad TEXT,
    categoria TEXT
);