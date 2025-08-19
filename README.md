Crear entorno virtual:

.\.venv\Scripts\Activate

Activar entorno:

.\.venv\Scripts\Activate

Crear BD y tablas:

python scripts\migrate.py
python scripts\seeder.py

Comando para levantar el proyecto:

uvicorn app.main:app --reload

URL Local para pruebas:

http://127.0.0.1:8000/docs
