# Configuración de la base de datos

La aplicación utiliza PostgreSQL. Copia `.env.example` a `.env` en la raíz del
proyecto y configura los datos de conexión:

| Variable | Valor predeterminado |
| --- | --- |
| `DB_NAME` | `ipsis` |
| `DB_USER` | `ipsis_app` |
| `DB_PASSWORD` | Vacío |
| `DB_HOST` | `localhost` |
| `DB_PORT` | `5432` |

Define `DB_PASSWORD` con la contraseña de PostgreSQL cuando se requiera.
El archivo `.env` no se incluye en Git ni en la imagen de Docker. También se
pueden definir las variables directamente en el entorno; estas prevalecen
sobre las del archivo `.env`. En Docker, proporciónalas al ejecutar el
contenedor, por ejemplo con `--env-file .env`; usa como `DB_HOST` un servidor
de PostgreSQL accesible desde el contenedor, no `localhost` si está fuera de él.

## Despliegue en un Droplet

Cada `push` a `main` ejecuta las pruebas con PostgreSQL, publica en GHCR una
imagen etiquetada con el SHA del commit y la despliega mediante SSH. El entorno
de GitHub `production` puede configurarse con revisores para aprobar despliegues.
No se ejecuta en pull requests.

### Preparación del servidor

1. Instala Docker y Docker Compose v2 (con soporte para `up --wait`). Crea el
   usuario de despliegue con permisos para usar Docker y escribe
   `/opt/ipsismanager/.env`, accesible solo por ese usuario. El directorio
   `/opt/ipsismanager` debe permitir que ese usuario escriba archivos.
2. Configura en `.env` las variables `DB_*` y añade:

   ```dotenv
   DJANGO_DEBUG=false
   DJANGO_SECRET_KEY=una-clave-aleatoria-larga-y-unica
   DJANGO_ALLOWED_HOSTS=api.ejemplo.com
   DJANGO_CSRF_TRUSTED_ORIGINS=https://api.ejemplo.com
   ```

   Genera una clave real, por ejemplo con
   `python -c "import secrets; print(secrets.token_urlsafe(64))"`. La base de
   datos debe existir y permitir conexiones del contenedor; el usuario necesita
   permisos para aplicar migraciones. Si PostgreSQL está en el propio servidor,
   `DB_HOST=host.docker.internal` apunta al host de Docker; configura PostgreSQL
   y el cortafuegos para aceptar esa conexión sin exponerla públicamente.
3. Crea `/opt/ipsismanager/media`, `/opt/ipsismanager/staticfiles` y
   `/opt/ipsismanager/.secrets` con permisos adecuados. Estos directorios
   persisten entre despliegues; coloca en `.secrets` el token de Google Drive
   si se utiliza esa integración. Incluye la base de datos, `media` y
   `.secrets` en las copias de seguridad.
4. Si el paquete GHCR es privado, autentica **en el servidor y como el usuario
   de despliegue** con `docker login ghcr.io` y un token con permiso
   `read:packages` y acceso al paquete. Mantén ese token fuera del repositorio.
   Si el paquete es público no se necesita autenticación para descargarlo.
5. Configura un proxy HTTPS, por ejemplo Nginx, hacia `127.0.0.1:8000` y para
   servir `/static/` desde `/opt/ipsismanager/staticfiles/` y `/media/` desde
   `/opt/ipsismanager/media/`. Revisa la política de acceso a los archivos
   multimedia antes de publicarlos. El contenedor solo escucha en localhost;
   el proxy debe tener permisos de lectura en esos directorios y redirigir
   HTTP a HTTPS. En producción, las cookies de sesión y CSRF requieren HTTPS.

Antes de poner el servicio en producción, revisa `python manage.py check
--deploy`: la configuración actual del correo usa el backend de consola y
requiere sustituirse por uno real si se envían correos. Configura HSTS en el
proxy solo después de comprobar que todo el sitio funciona correctamente con
HTTPS. Ajusta también `CORS_ALLOWED_ORIGINS` si el frontend se sirve desde otro
origen; actualmente solo permite `http://localhost:4200`.

### Configuración en GitHub

En el repositorio o en el entorno `production`, define los secretos
`DROPLET_HOST`, `DROPLET_USER`, `DROPLET_SSH_PRIVATE_KEY` y
`DROPLET_SSH_KNOWN_HOSTS`. La clave pública correspondiente debe estar en
`authorized_keys` en el servidor. `DROPLET_SSH_KNOWN_HOSTS` debe contener la
línea completa de `known_hosts`, cuya huella se haya verificado por un canal
seguro; para un puerto no predeterminado usa el formato `[host]:puerto`.
Opcionalmente define la variable `DROPLET_SSH_PORT`; por defecto es `22`.
El token automático de GitHub Actions publica en GHCR con permiso
`packages: write`.

El despliegue descarga la imagen, verifica que `DJANGO_DEBUG=false`, ejecuta
`migrate --noinput` y `collectstatic --noinput`, y solo entonces reemplaza el
contenedor. La comprobación de salud verifica que Gunicorn acepte conexiones,
no que la base de datos o el proxy funcionen. Un fallo detiene el flujo, pero
no revierte migraciones ni garantiza restaurar el contenedor anterior. Haz
copias de seguridad y usa migraciones compatibles con la versión anterior,
que sigue atendiendo solicitudes mientras se aplican. Mantén también las
versiones de archivos estáticos compatibles durante la actualización.
