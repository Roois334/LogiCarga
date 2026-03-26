# LogiCarga - Proyecto básico

Proyecto base desarrollado con Flask, HTML, CSS, JavaScript, Python y MySQL para la gestión de flota y operaciones.

## Roles incluidos
- Administrador: acceso completo al sistema.
- Conductor: acceso a sus viajes, combustible, viáticos e incidentes.
- Supervisor: acceso a reportes y consultas.

## Módulos incluidos
- Login por rol
- Dashboard
- Gestión de usuarios
- Gestión de conductores
- Gestión de vehículos
- Registro de viajes
- Registro de combustible
- Registro de viáticos
- Registro de incidentes
- Mantenimientos
- Reportes y consultas

## Requisitos
- Python 3.11+
- MySQL 8+
- pip

## Instalación
1. Crear la base de datos ejecutando `database.sql`.
2. Crear entorno virtual:
   - `python -m venv venv`
   - Windows: `venv\Scripts\activate`
   - Linux/macOS: `source venv/bin/activate`
3. Instalar dependencias:
   - `pip install -r requirements.txt`
4. Configurar variables usando `.env.example`.
5. Ejecutar:
   - `python app.py`

## Credenciales de prueba
- Administrador: `admin@logicarga.com` / `123456`
- Conductor: `conductor1@logicarga.com` / `123456`
- Supervisor: `supervisor@logicarga.com` / `123456`

## Notas
- Esta es una base funcional inicial.
- Las contraseñas están en texto plano solo para pruebas.
- El campo de comprobante se deja preparado para integrar carga real de archivos en una siguiente fase.
