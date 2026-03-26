DROP DATABASE IF EXISTS logicarga_db;
CREATE DATABASE logicarga_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE logicarga_db;

CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(255) NULL
);

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rol_id INT NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    correo VARCHAR(120) NOT NULL UNIQUE,
    password VARCHAR(120) NOT NULL,
    telefono VARCHAR(30) NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rol_id) REFERENCES roles(id)
);

CREATE TABLE conductores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL UNIQUE,
    nombre_completo VARCHAR(120) NOT NULL,
    numero_licencia VARCHAR(60) NOT NULL UNIQUE,
    tipo_licencia ENUM('A1','A2','B1','B2','C1','C2','C3') NULL,
    telefono VARCHAR(30) NULL,
    email VARCHAR(120) NULL,
    direccion VARCHAR(255) NULL,
    ciudad VARCHAR(100) NULL,
    fecha_vencimiento_licencia DATE NULL,
    estado ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE vehiculos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    placa VARCHAR(20) NOT NULL UNIQUE,
    modelo VARCHAR(100) NOT NULL,
    anio SMALLINT NULL,
    capacidad_carga DECIMAL(10,2) NOT NULL,
    kilometraje_actual INT NOT NULL DEFAULT 0,
    estado ENUM('Disponible', 'En ruta', 'En mantenimiento', 'Fuera de servicio') DEFAULT 'Disponible',
    fecha_ultimo_mantenimiento DATE NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE viajes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehiculo_id INT NOT NULL,
    conductor_id INT NOT NULL,
    ciudad_origen VARCHAR(120) NOT NULL,
    ciudad_destino VARCHAR(120) NOT NULL,
    fecha_salida DATETIME NOT NULL,
    fecha_llegada DATETIME NULL,
    tipo_carga VARCHAR(120) NOT NULL,
    kilometraje_inicio INT NOT NULL,
    kilometraje_fin INT NULL,
    combustible_inicio DECIMAL(10,2) NOT NULL,
    combustible_fin DECIMAL(10,2) NULL,
    estado ENUM('Programado', 'En ruta', 'Finalizado', 'Cancelado') DEFAULT 'Programado',
    observaciones TEXT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id),
    FOREIGN KEY (conductor_id) REFERENCES conductores(id)
);

CREATE TABLE combustible (
    id INT AUTO_INCREMENT PRIMARY KEY,
    viaje_id INT NOT NULL,
    vehiculo_id INT NOT NULL,
    conductor_id INT NOT NULL,
    tipo_combustible ENUM('Diésel','Corriente','Extra','Gas Natural') DEFAULT 'Diésel',
    litros DECIMAL(10,2) NOT NULL,
    costo_total DECIMAL(12,2) NOT NULL,
    ciudad VARCHAR(120) NOT NULL,
    fecha_registro DATETIME NOT NULL,
    observaciones TEXT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (viaje_id) REFERENCES viajes(id),
    FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id),
    FOREIGN KEY (conductor_id) REFERENCES conductores(id)
);

CREATE TABLE viaticos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    viaje_id INT NOT NULL,
    conductor_id INT NOT NULL,
    tipo_gasto ENUM('Alimentación', 'Hospedaje', 'Peajes', 'Otros gastos operativos') NOT NULL,
    valor_gasto DECIMAL(12,2) NOT NULL,
    ciudad VARCHAR(120) NOT NULL,
    fecha_gasto DATETIME NOT NULL,
    comprobante VARCHAR(255) NULL,
    observaciones TEXT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (viaje_id) REFERENCES viajes(id),
    FOREIGN KEY (conductor_id) REFERENCES conductores(id)
);

CREATE TABLE incidentes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    viaje_id INT NOT NULL,
    conductor_id INT NOT NULL,
    tipo_incidente ENUM('Falla mecánica', 'Retraso en carretera', 'Accidente', 'Problema durante la entrega') NOT NULL,
    descripcion TEXT NOT NULL,
    ciudad VARCHAR(120) NULL,
    fecha_incidente DATETIME NOT NULL,
    severidad ENUM('Baja', 'Media', 'Alta') DEFAULT 'Media',
    estado ENUM('Reportado', 'En revisión', 'Cerrado') DEFAULT 'Reportado',
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (viaje_id) REFERENCES viajes(id),
    FOREIGN KEY (conductor_id) REFERENCES conductores(id)
);

CREATE TABLE mantenimientos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehiculo_id INT NOT NULL,
    fecha_mantenimiento DATE NULL,
    tipo_mantenimiento ENUM('Preventivo', 'Correctivo') NOT NULL,
    descripcion TEXT NULL,
    kilometraje_programado INT NOT NULL,
    costo DECIMAL(12,2) NOT NULL DEFAULT 0,
    estado ENUM('Pendiente', 'Programado', 'Completado') DEFAULT 'Pendiente',
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id)
);

CREATE TABLE auditoria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL,
    modulo VARCHAR(80) NOT NULL,
    accion VARCHAR(80) NOT NULL,
    detalle TEXT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- ─── Roles ────────────────────────────────────────────────────────────────────
INSERT INTO roles (nombre, descripcion) VALUES
('Administrador', 'Acceso completo a todo el sistema'),
('Conductor',     'Acceso a viajes, combustible, viáticos e incidentes propios'),
('Supervisor',    'Acceso a reportes y consultas');

-- ─── Usuarios (contraseña: logi2026) ─────────────────────────────────────────
-- Contraseña de todos: logi2026  (almacenada con bcrypt rounds=12)
INSERT INTO usuarios (rol_id, nombre, correo, password, telefono) VALUES
(1, 'Administrador General',  'adminlogi@yopmail.com',       '$2b$12$Pys48Du1jdiaYOcPJ4abq.TWhoYCFxH4J/WuTxaoRKB2r9PI9Zh9K', '3001000001'),
(2, 'Andrés Felipe Moreno',   'conductor1.logi@yopmail.com', '$2b$12$UHLP4xizJdMbaegwsZN9degfDR6YOSzYqEx09muf0RYH5NLhfnw3m',  '3001000002'),
(2, 'Carlos Darío Quintero',  'conductor2.logi@yopmail.com', '$2b$12$IvJeEwjxR7o2k2T75lyWEeincP.dXXVx.7mkVZaatJ067hB6lS/d6',  '3001000003'),
(2, 'Jhon Sebastián Vargas',  'conductor3.logi@yopmail.com', '$2b$12$hXPslNDVOnQsjTY.SLa.X.NA73l9FmCwJoNW/i7e2H9vlgTVpvlom',  '3001000004'),
(3, 'Supervisor General',     'supervisor.logi@yopmail.com', '$2b$12$LXTqefPOFmONqJz4RXsZSe4QcvEqAjd/pvngEF6HaB2QlKoqeDCCW',  '3001000005');

-- ─── Conductores ─────────────────────────────────────────────────────────────
INSERT INTO conductores (usuario_id, nombre_completo, numero_licencia, tipo_licencia, telefono, email, direccion, ciudad, fecha_vencimiento_licencia, estado) VALUES
(2, 'Andrés Felipe Moreno',  'LIC-1001', 'C3', '3001000002', 'conductor1.logi@yopmail.com', 'Cra 5 # 10-20',   'Bogotá',   '2028-12-31', 'Activo'),
(3, 'Carlos Darío Quintero', 'LIC-1002', 'C2', '3001000003', 'conductor2.logi@yopmail.com', 'Cll 30 # 45-12',  'Medellín', '2027-09-30', 'Activo'),
(4, 'Jhon Sebastián Vargas', 'LIC-1003', 'C1', '3001000004', 'conductor3.logi@yopmail.com', 'Av 68 # 22-15',   'Cali',     '2029-06-30', 'Activo');

-- ─── Vehículos ────────────────────────────────────────────────────────────────
INSERT INTO vehiculos (placa, modelo, anio, capacidad_carga, kilometraje_actual, estado, fecha_ultimo_mantenimiento) VALUES
('ABC123', 'Volvo FH',           2021, 20.00, 28000, 'Disponible',       '2026-01-10'),
('XYZ789', 'Kenworth T800',      2019, 18.50, 30500, 'En mantenimiento', '2025-12-20'),
('LMN456', 'International LT',   2022, 22.00, 15000, 'En ruta',          '2026-02-15');

-- ─── Viajes ───────────────────────────────────────────────────────────────────
INSERT INTO viajes (vehiculo_id, conductor_id, ciudad_origen, ciudad_destino, fecha_salida, fecha_llegada, tipo_carga, kilometraje_inicio, kilometraje_fin, combustible_inicio, combustible_fin, estado, observaciones) VALUES
(1, 1, 'Bogotá',   'Cali',         '2026-03-20 06:00:00', '2026-03-20 18:30:00', 'Alimentos',       28000, 28480, 95.00, 32.00, 'Finalizado', 'Viaje completado sin novedad.'),
(3, 2, 'Medellín', 'Barranquilla', '2026-03-23 05:30:00', NULL,                  'Electrodomésticos',15000, NULL,  100.00, NULL, 'En ruta',    'Entrega programada para mañana.'),
(1, 1, 'Bogotá',   'Bucaramanga',  '2026-03-25 07:00:00', NULL,                  'Repuestos',        28480, NULL,  90.00,  NULL, 'Programado', 'Pendiente salida.');

-- ─── Combustible ──────────────────────────────────────────────────────────────
INSERT INTO combustible (viaje_id, vehiculo_id, conductor_id, tipo_combustible, litros, costo_total, ciudad, fecha_registro, observaciones) VALUES
(1, 1, 1, 'Diésel', 60.00,  720000.00, 'Ibagué',   '2026-03-20 11:30:00', 'Carga intermedia'),
(2, 3, 2, 'Diésel', 80.00,  960000.00, 'Montería',  '2026-03-23 14:20:00', 'Carga completa');

-- ─── Viáticos ─────────────────────────────────────────────────────────────────
INSERT INTO viaticos (viaje_id, conductor_id, tipo_gasto, valor_gasto, ciudad, fecha_gasto, comprobante, observaciones) VALUES
(1, 1, 'Alimentación', 45000.00,  'Ibagué',       '2026-03-20 12:10:00', 'uploads/viaticos/almuerzo_1.jpg', 'Almuerzo del conductor'),
(1, 1, 'Peajes',       98000.00,  'Cali',          '2026-03-20 17:50:00', 'uploads/viaticos/peaje_1.jpg',    'Peajes del trayecto'),
(2, 2, 'Hospedaje',   130000.00, 'Barranquilla',   '2026-03-23 22:00:00', 'uploads/viaticos/hotel_2.jpg',   'Hospedaje por cierre de ruta');

-- ─── Incidentes ───────────────────────────────────────────────────────────────
INSERT INTO incidentes (viaje_id, conductor_id, tipo_incidente, descripcion, ciudad, fecha_incidente, severidad, estado) VALUES
(2, 2, 'Retraso en carretera', 'Congestión vehicular y cierre parcial de vía.', 'Sincelejo', '2026-03-23 16:30:00', 'Media', 'En revisión');

-- ─── Mantenimientos ───────────────────────────────────────────────────────────
INSERT INTO mantenimientos (vehiculo_id, fecha_mantenimiento, tipo_mantenimiento, descripcion, kilometraje_programado, costo, estado) VALUES
(2, '2026-03-26', 'Preventivo', 'Cambio de aceite y revisión general.', 30000, 850000.00, 'Programado'),
(1, NULL,         'Preventivo', 'Programar mantenimiento por kilometraje.',  30000, 0.00,      'Pendiente');

-- ─── Vista operativa ──────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_costos_operacion_ruta AS
SELECT v.id AS viaje_id,
       CONCAT(v.ciudad_origen, ' - ', v.ciudad_destino) AS ruta,
       COALESCE(SUM(DISTINCT cb.costo_total), 0)                                                   AS costo_combustible,
       COALESCE(SUM(DISTINCT vt.valor_gasto),  0)                                                  AS costo_viaticos,
       COALESCE(SUM(DISTINCT cb.costo_total), 0) + COALESCE(SUM(DISTINCT vt.valor_gasto), 0)      AS costo_total_operacion
FROM   viajes v
LEFT   JOIN combustible cb ON cb.viaje_id = v.id
LEFT   JOIN viaticos    vt ON vt.viaje_id = v.id
GROUP  BY v.id, v.ciudad_origen, v.ciudad_destino;
