# Itinerario de Eventos

Este proyecto tiene el objetivo de desarrollar una aplicación que facilite la consulta del itinerario de eventos para la Semana de la Ingeniería.

Además, implementa un *pipeline* que toma como entrada una serie de datos definidos en un archivo de Excel, los procesa con el fin de generar archivos de salida utilizables y, finalmente, los sube a una base de datos.

## Base de Datos

La base de datos utiliza PostgreSQL y está desplegada en un VPS. El esquema se puede obtener ejecutando [este script](/dump_database.sh) o consultando la definición incluida en el repositorio: [postgres_db.sql](/postgres_db.sql).

## Pipeline

El *pipeline* fue escrito en Python y tiene múltiples dependencias, las cuales están especificadas en el archivo [requirements.txt](/pipeline/requirements.txt).

### Instrucciones de uso

**Clona el repositorio:**

```bash
git clone https://github.com/maximoaxel2/event_schedule_api
cd event_schedule_api
```

**Crea un entorno virtual para Python:**

```bash
python3 -m venv .venv
```

**Activa el entorno virtual:**

En Linux:

```bash
source .venv/bin/activate
```

En Windows:

```bash
.venv/Scripts/activate.bat
```

**Instala las dependencias:**

```bash
pip install -r pipeline/requirements.txt
```

**Ejecutar el script:**

```bash
python ./pipeline/main.py
```
