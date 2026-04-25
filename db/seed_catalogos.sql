-- Datos iniciales: Almacenes
INSERT INTO almacenes (id_almacen, nombre, ubicacion, capacidad_total, capacidad_usada) VALUES
('ALM001', 'Almacén Central', 'Av. Principal 123, Ciudad de México', 10000, 0),
('ALM002', 'Almacén Norte', 'Blvd. Industrial 456, Monterrey', 5000, 0),
('ALM003', 'Almacén Sur', 'Carrtera Sur 789, Guadalajara', 5000, 0);

-- Datos iniciales: Proveedores
INSERT INTO proveedores (id_proveedor, nombre, ubicacion, tiempo_entrega_dias, activo) VALUES
('PROV001', 'Autopartes del Norte', 'Monterrey, NL', 2, 1),
('PROV002', 'Refacciones México', 'Ciudad de México', 1, 1),
('PROV003', 'Industrial de Occidente', 'Guadalajara, Jal', 3, 1),
('PROV004', 'AutoPartes del Pacífico', 'Tijuana, BC', 5, 1);

-- Datos iniciales: Clientes ficticios
INSERT INTO clientes (id_cliente, nombre, rfc, direccion, email, activo) VALUES
('CLI001', 'Taller Mecánica López', 'MLO850101ABC', 'Calle Obregón 45, CDMX', 'tallerlopez@email.com', 1),
('CLI002', 'Servicio Automotriz Torres', 'SAT920202DEF', 'Av. Juárez 78, Monterrey', 'satorres@email.com', 1),
('CLI003', 'Refaccionaria El Guajolote', 'RGU780505GHI', 'Mercado local 12, Guadalajara', 'elguajolote@email.com', 1),
('CLI004', 'AutoServicio del Centro', 'ASC800303JKL', 'Centro 23, Puebla', 'autoservicio@email.com', 1),
('CLI005', 'Mecánica Express', 'MEX910101MNO', 'Blvd. Horas 89, Tijuana', 'mexexpress@email.com', 1);