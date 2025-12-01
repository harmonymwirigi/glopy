from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # <-- NUEVO para migraciones
from flask_mail import Mail, Message
from sqlalchemy.orm import joinedload
import os
from datetime import datetime, timedelta
import threading
import time
import functools
from apis.inmobiliaria.api_inmobiliaria import api_inmobiliaria_bp
from apis.vehicles.api_vehicles import api_vehicles_bp

# Importamos todo lo necesario de models.py
from models import db, Sector, Announcement, RealEstateCategory,  Geoname
from models import User, SavedAd, SavedSearch, Invitation, PointsTransaction
from models import PricingPlan, Payment, PremiumAd, AdminLog
from models import CommercialAd, CommercialAdView, CommercialAdClick
from models import VehicleCategory, VehicleMake, VehicleModel, Vehicle, VehicleImage, SavedVehicle, VehicleVector, VehicleSimilarity

# COMENTADO (para que no choquen):
# from models import Provincia, MunicipioSQL

# NUEVO (autoload):
from models import ProvinciaAuto, MunicipioAuto
# NUEVO: Importamos el modelo para las imágenes adicionales de cada anuncio
from models import AnnouncementImage
from dotenv import load_dotenv
from flask_mail import Mail, Message
basedir = os.path.abspath(os.path.dirname(__file__))
# db_path = os.path.join(basedir, 'instance', 'glopy.db')
# Carga el .env usando ruta absoluta para entornos como cPanel/Passenger
load_dotenv(os.path.join(basedir, '.env'))
app = Flask(__name__)


database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Si estamos en PRODUCCIÓN (cPanel), usamos la variable de entorno.
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Si estamos en DESARROLLO (local), usamos la base de datos SQLite como antes.
    print("ADVERTENCIA: No se encontro DATABASE_URL. Usando base de datos SQLite local.")
    # Asegúrate de que la carpeta 'instance' exista
    instance_path = os.path.join(basedir, 'instance')
    os.makedirs(instance_path, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'glopy.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enhanced database connection configuration for production stability
# Only apply connection pooling settings for non-SQLite databases
database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
if not database_uri.startswith('sqlite'):
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 280  # Recycle connections every 280 seconds
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 20   # Timeout for getting connection from pool
    app.config['SQLALCHEMY_POOL_PRE_PING'] = True  # Verify connections before use
    app.config['SQLALCHEMY_POOL_SIZE'] = 10       # Number of connections to maintain
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20    # Additional connections beyond pool_size
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
        'pool_timeout': 20,
        'max_overflow': 20,
        'pool_size': 10
    }
# Clave de sesión
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')

# Configuración de email
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME') or 'glopy.alerts@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') or 'your-app-password'
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME') or 'glopy.alerts@gmail.com'

# Stripe configuration
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# Nombre de la app para emails y títulos
APP_NAME = os.environ.get('APP_NAME', 'Glopy')
APP_PRIMARY_COLOR = os.environ.get('APP_PRIMARY_COLOR', '#1060ff')
APP_SECONDARY_COLOR = os.environ.get('APP_SECONDARY_COLOR', '#0b4ad6')
APP_PUBLIC_URL = os.environ.get('APP_PUBLIC_URL', '')  # e.g. https://glopy.app
LOGO_URL = os.environ.get('LOGO_URL', '')  # URL absoluta al logo público
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', os.environ.get('MAIL_FROM', ''))

def _brand_ctx():
    return dict(
        app_name=APP_NAME,
        primary_color=APP_PRIMARY_COLOR,
        secondary_color=APP_SECONDARY_COLOR,
        app_url=APP_PUBLIC_URL,
        logo_url=LOGO_URL,
        support_email=SUPPORT_EMAIL,
    )

"""Configuración de correo con Flask-Mail"""
# Configuración de Flask-Mail basada en las variables existentes
app.config['MAIL_SERVER'] = os.environ.get('SMTP_HOST')
app.config['MAIL_PORT'] = int(os.environ.get('SMTP_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.environ.get('SMTP_USE_TLS', 'true').lower() in ('1', 'true', 'yes')
app.config['MAIL_USE_SSL'] = os.environ.get('SMTP_USE_SSL', 'false').lower() in ('1', 'true', 'yes')
app.config['MAIL_USERNAME'] = os.environ.get('SMTP_USER')
app.config['MAIL_PASSWORD'] = os.environ.get('SMTP_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = (APP_NAME, os.environ.get('MAIL_FROM', os.environ.get('SMTP_USER')))
app.config['MAIL_SUPPRESS_SEND'] = False

# Inicializar Flask-Mail
mail = Mail(app)

def send_email_smtp(to_email: str, subject: str, html_body: str, text_body: str | None = None):
    """Enviar email usando Flask-Mail (recipientes únicos)."""
    msg = Message(subject=subject, recipients=[to_email])
    if text_body:
        msg.body = text_body
    msg.html = html_body
    mail.send(msg)


# Ruta de prueba para envío de email (desactivada por defecto).
# Activar estableciendo ENABLE_EMAIL_TEST_ROUTE=1 y definiendo EMAIL_TEST_KEY para acceso básico.
import functools

def _email_test_route_enabled():
    return os.environ.get('ENABLE_EMAIL_TEST_ROUTE', '0').lower() in ('1', 'true', 'yes')

def _require_test_key(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        key = request.args.get('key')
        expected = os.environ.get('EMAIL_TEST_KEY')
        if not expected or key != expected:
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper

if _email_test_route_enabled():
    @app.route('/admin/test-email')
    @_require_test_key
    def admin_test_email():
        to = request.args.get('to')
        if not to:
            return jsonify({"error": "Missing 'to' param"}), 400
        try:
            with app.app_context():
                send_email_smtp(to, f"Prueba SMTP {APP_NAME}", "<b>Prueba</b>", "Prueba")
            return jsonify({
                "status": "sent",
                "to": to,
                "host": app.config.get('MAIL_SERVER'),
                "port": app.config.get('MAIL_PORT'),
                "ssl": app.config.get('MAIL_USE_SSL'),
                "tls": app.config.get('MAIL_USE_TLS'),
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": str(e),
                "host": app.config.get('MAIL_SERVER'),
                "port": app.config.get('MAIL_PORT'),
                "ssl": app.config.get('MAIL_USE_SSL'),
                "tls": app.config.get('MAIL_USE_TLS'),
            }), 500
# Inicializamos la base de datos con la configuración de la app
db.init_app(app)

# Database connection retry mechanism
def init_db_with_retry():
    """Initialize database with retry mechanism for production stability"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            with app.app_context():
                # Test the connection
                with db.engine.connect() as connection:
                    connection.execute(db.text('SELECT 1'))
                print(f"Database connection successful on attempt {attempt + 1}")
                return True
        except Exception as e:
            print(f"Database connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print("All database connection attempts failed")
                return False

# Initialize database with retry
init_db_with_retry()

# Database retry decorator for production stability
def db_retry(max_retries=3, delay=1):
    """Decorator to retry database operations on connection failures"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'mysql server has gone away' in error_msg or 'broken pipe' in error_msg or 'connection' in error_msg:
                        print(f"Database connection error on attempt {attempt + 1}: {str(e)}")
                        if attempt < max_retries - 1:
                            print(f"Retrying in {delay} seconds...")
                            time.sleep(delay)
                            # Force database engine to reconnect
                            try:
                                db.engine.dispose()
                            except:
                                pass
                        else:
                            print("All database retry attempts failed")
                            raise e
                    else:
                        # Re-raise non-connection errors immediately
                        raise e
            return None
        return wrapper
    return decorator

# NUEVO: Configuramos Flask-Migrate
migrate = Migrate(app, db)

# Inicializamos Flask-Mail
mail = Mail(app)

# Initialize OAuth
from oauth_config import init_oauth
oauth = init_oauth(app)

# Register OAuth blueprint
from oauth_routes import oauth_bp
app.register_blueprint(oauth_bp)

# Registrar el Blueprint de la api de inmobiliaira
app.register_blueprint(api_inmobiliaria_bp)
app.register_blueprint(api_vehicles_bp)
# ------------------------------
# TU CÓDIGO ORIGINAL A PARTIR DE AQUÍ (sin eliminar nada)
# ------------------------------

# Ruta base para imágenes
IMAGE_PATH = '/static/images/'

# Datos de ejemplo para cada sector
sectores = {
    'inmobiliaria': {
        'nombre': 'Inmobiliaria',
        'imagen_sector': IMAGE_PATH + 'inmobiliaria.jpg',
        'anuncios': [
            {
                'titulo': 'Apartamento en el centro de Madrid',
                'descripcion': '2 habitaciones, 1 baño, 85m². Cerca de transporte público.',
                'precio': '€250,000',  # Ojo: Está en formato string
                'imagen': IMAGE_PATH + 'inmobiliaria.jpg',
                # NUEVO: Agregamos una lista de imágenes adicionales para la galería de este anuncio
                'imagenes': [
                    IMAGE_PATH + 'inmobiliaria.jpg',
                    IMAGE_PATH + 'inmobiliaria.jpg',
                    IMAGE_PATH + 'inmobiliaria.jpg'
                ]
            },
            {
                'titulo': 'Casa con jardín en Barcelona',
                'descripcion': '3 habitaciones, 2 baños, 120m². Ideal para familias.',
                'precio': '€450,000',
                'imagen': IMAGE_PATH + 'inmobiliaria.jpg'
            },
            {
                'titulo': 'Piso moderno en Valencia',
                'descripcion': '1 habitación, 1 baño, 60m². Vista al mar.',
                'precio': '€180,000',
                'imagen': IMAGE_PATH + 'inmobiliaria.jpg'
            },
            {
                'titulo': 'Villa de lujo en Marbella',
                'descripcion': '5 habitaciones, 4 baños, 350m². Piscina y garaje.',
                'precio': '€1,200,000',
                'imagen': IMAGE_PATH + 'inmobiliaria.jpg'
            },
            # Añade más anuncios según sea necesario
        ]
    },
    'coches': {
        'nombre': 'Coches',
        'imagen_sector': IMAGE_PATH + 'coches.jpg',
        'anuncios': [
            {
                'titulo': 'Toyota Corolla 2018',
                'descripcion': 'Motor 1.8L, 50,000 km, color blanco.',
                'precio': '€15,000',
                'imagen': IMAGE_PATH + 'coches.jpg',
                # NUEVO: También añadimos imágenes adicionales de prueba para este anuncio
                'imagenes': [
                    IMAGE_PATH + 'coches.jpg',
                    IMAGE_PATH + 'coches2.jpg'
                ]
            },
            {
                'titulo': 'Volkswagen Golf 2020',
                'descripcion': 'Motor 2.0L, 30,000 km, color negro.',
                'precio': '€20,000',
                'imagen': IMAGE_PATH + 'coches.jpg'
            },
            {
                'titulo': 'BMW Serie 3 2019',
                'descripcion': 'Motor 2.0L, 40,000 km, color azul.',
                'precio': '€28,000',
                'imagen': IMAGE_PATH + 'coches.jpg'
            },
            {
                'titulo': 'Audi A4 2021',
                'descripcion': 'Motor 2.0L, 10,000 km, color rojo.',
                'precio': '€35,000',
                'imagen': IMAGE_PATH + 'coches.jpg'
            },
            # Añade más anuncios según sea necesario
        ]
    },
    'electronica': {
        'nombre': 'Electrónica',
        'imagen_sector': IMAGE_PATH + 'tecnologia.jpg',
        'anuncios': [
            {
                'titulo': 'Smartphone Samsung Galaxy S21',
                'descripcion': '128GB, color azul, sin contrato.',
                'precio': '€700',
                'imagen': IMAGE_PATH + 'tecnologia.jpg'
            },
            {
                'titulo': 'Laptop Dell XPS 13',
                'descripcion': 'Intel i7, 16GB RAM, 512GB SSD.',
                'precio': '€1,200',
                'imagen': IMAGE_PATH + 'tecnologia.jpg'
            },
            {
                'titulo': 'Televisor LG OLED 55"',
                'descripcion': 'Resolución 4K, Smart TV, HDR.',
                'precio': '€1,500',
                'imagen': IMAGE_PATH + 'tecnologia.jpg'
            },
            {
                'titulo': 'Tablet Apple iPad Pro',
                'descripcion': '256GB, color plata, Wi-Fi.',
                'precio': '€900',
                'imagen': IMAGE_PATH + 'tecnologia.jpg'
            },
            # Añade más anuncios según sea necesario
        ]
    },
    # Puedes añadir más sectores aquí
}

# NUEVO: Lista de categorías para Inmobiliaria
REAL_ESTATE_CATEGORIES_DATA = [
    {
        "name": "Inmuebles en Venta",
        "description": "Categoría para la compra de propiedades (pisos, casas, chalets...)"
    },
    {
        "name": "Inmuebles en Alquiler",
        "description": "Para alquiler de corto y largo plazo."
    },
    {
        "name": "Inmuebles de Lujo",
        "description": "Propiedades con un precio alto y características premium."
    },
    {
        "name": "Inmuebles Bancarios",
        "description": "Inmuebles ofrecidos por bancos o fondos de inversión."
    },
    {
        "name": "Inmuebles en Subasta",
        "description": "Propiedades subastadas, con fecha de cierre cercana."
    },
    {
        "name": "Terrenos y Parcelas",
        "description": "Solares, terrenos rústicos o industriales."
    },
    {
        "name": "Locales Comerciales y Oficinas",
        "description": "Negocios, locales a pie de calle, oficinas en centros empresariales."
    },
    {
        "name": "Alquiler Vacacional",
        "description": "Propiedades para alquiler temporal, vacacional o turístico."
    },
    {
        "name": "Inmuebles Industriales",
        "description": "Naves, almacenes, solares industriales."
    }
]

def to_numeric(value, num_type=float):
    default = None
    if value is None or value == '':
        return default
    try:
        return num_type(value)
    except (ValueError, TypeError):
        return default

# def populate_db():
#     with app.app_context():
#         db.create_all()  # Crea tablas si no existen

#         # Verificar si ya hay sectores guardados
#         if Sector.query.count() == 0:
#             for key, data_sector in sectores.items():
#                 new_sector = Sector(
#                     name=data_sector['nombre'],
#                     image_path=data_sector['imagen_sector']
#                 )
#                 db.session.add(new_sector)
#                 db.session.commit()  # Para obtener new_sector.id

#                 for anuncio in data_sector['anuncios']:
#                     def _parse_price(price_str):
#                         if not price_str:
#                             return None
#                         clean = price_str.replace("€", "").replace(",", "").replace(" ", "")
#                         try:
#                             return float(clean)
#                         except:
#                             return None

#                     new_announcement = Announcement(
#                         sector_id=new_sector.id,
#                         title=anuncio['titulo'],
#                         description=anuncio['descripcion'],
#                         price=_parse_price(anuncio['precio']),
#                         image=anuncio['imagen']
#                     )
#                     db.session.add(new_announcement)
#                     db.session.flush()  # Para asignar new_announcement.id sin hacer commit completo

#                     # NUEVO: Si el anuncio tiene imágenes adicionales, se crean registros en AnnouncementImage
#                     if 'imagenes' in anuncio:
#                         for i, img_url in enumerate(anuncio['imagenes']):
#                             new_image = AnnouncementImage(
#                                 announcement_id=new_announcement.id,
#                                 image_url=img_url,
#                                 order=i
#                             )
#                             db.session.add(new_image)

#         # NUEVO: Poblar la tabla de categorías para Inmobiliaria si está vacía
#         if RealEstateCategory.query.count() == 0:
#             for cat_data in REAL_ESTATE_CATEGORIES_DATA:
#                 cat = RealEstateCategory(
#                     name=cat_data["name"],
#                     description=cat_data["description"]
#                 )
#                 db.session.add(cat)

#         # NUEVO: POBLAR TABLAS DE COMUNIDADES, PROVINCIAS Y MUNICIPIOS
#         if Community.query.count() == 0:
#             c1 = Community(name="Cataluña")
#             db.session.add(c1)
#             db.session.commit()

#             p1 = Province(name="Barcelona", community_id=c1.id)
#             p2 = Province(name="Girona", community_id=c1.id)
#             db.session.add_all([p1, p2])
#             db.session.commit()

#             m1 = Municipality(name="Badalona", province_id=p1.id)
#             m2 = Municipality(name="Mataró", province_id=p1.id)
#             m3 = Municipality(name="Girona (ciudad)", province_id=p2.id)
#             db.session.add_all([m1, m2, m3])
#             db.session.commit()

#         db.session.commit()

# # Llamamos a populate_db cuando se inicie la app
# populate_db()


# ------------------------------
# NUEVO: Ejecutar el archivo SQL externo para crear 'provincia' y 'municipio'
# ------------------------------
def run_sql_file():
    """
    Esta función carga y ejecuta el contenido del archivo
    sql/CreateTableProvinciasMunicipios.sql (si existe) contra la BD.
    Crea las tablas 'provincia' y 'municipio' y las rellena.

    ¡Ahora dividiendo el script en sentencias para evitar "You can only execute one statement at a time"!
    """
    sql_path = os.path.join('sql', 'CreateTableProvinciasMunicipios.sql')
    if not os.path.exists(sql_path):
        print(f"[ADVERTENCIA] No se encuentra el archivo: {sql_path}")
        return

    print(f"Ejecutando el archivo SQL externo: {sql_path}")
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    from sqlalchemy import text

    # 1) Partimos el contenido en sentencias separadas por ';'
    statements = sql_script.split(';')

    # 2) Ejecutamos cada sentencia por separado
    for stmt in statements:
        stmt = stmt.strip()
        # Ignoramos líneas vacías
        if not stmt:
            continue

        # Ejecutar
        db.session.execute(text(stmt))

    # 3) Commit final
    db.session.commit()
    # print("Archivo SQL ejecutado con éxito. Tablas 'provincia' y 'municipio' creadas/pobladas.")


# --------------------------------------------
# NUEVO: Asignar autoload a ProvinciaAuto / MunicipioAuto dentro de app_context
# --------------------------------------------
with app.app_context():
    # Asegura que existan las tablas 'provincia' y 'municipio' antes de reflejarlas
    from sqlalchemy import Table, inspect

    inspector = inspect(db.engine)
    needs_setup = not (inspector.has_table('provincia') and inspector.has_table('municipio'))
    if needs_setup:
        try:
            run_sql_file()
        except Exception as e:
            print(f"[ADVERTENCIA] No se pudo crear/probar tablas provincia/municipio: {e}")

    # Refleja las tablas externas si ya existen (o tras crearlas)
    if inspector.has_table('provincia'):
        ProvinciaAuto.__table__ = Table(
            'provincia',
            db.metadata,
            autoload=True,
            autoload_with=db.engine,
            extend_existing=True
        )
    else:
        print("[ADVERTENCIA] La tabla 'provincia' no existe todavía.")

    if inspector.has_table('municipio'):
        MunicipioAuto.__table__ = Table(
            'municipio',
            db.metadata,
            autoload=True,
            autoload_with=db.engine,
            extend_existing=True
        )
    else:
        print("[ADVERTENCIA] La tabla 'municipio' no existe todavía.")

# Asegura la tabla de usuarios
with app.app_context():
    try:
        User.__table__.create(bind=db.engine, checkfirst=True)
    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo crear la tabla 'users': {e}")

# Sesión y helpers de autenticación
def get_current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    try:
        return User.query.get(uid)
    except Exception:
        return None

@app.context_processor
def inject_user():
    user = get_current_user()
    context_data = dict(current_user=user, is_authenticated=bool(user))
    
    # Add user-specific data if logged in
    if user:
        try:
            # Get saved ads count for bottom navigation badge
            saved_ads_count = SavedAd.query.filter_by(user_id=user.id).count()
            context_data['saved_ads_count'] = saved_ads_count
            
            # Get saved searches count
            saved_searches_count = SavedSearch.query.filter_by(user_id=user.id).count()
            context_data['saved_searches_count'] = saved_searches_count
            
            # Get email alerts status
            context_data['email_alerts_enabled'] = user.email_alerts_enabled
        except Exception as e:
            # Handle any database errors gracefully
            app.logger.error(f"Error getting user data in context processor: {e}")
            context_data.update({
                'saved_ads_count': 0,
                'saved_searches_count': 0,
                'email_alerts_enabled': False
            })
    
    return context_data

@app.before_request
def auth_redirects():
    # Redirige a home si ya está autenticado y entra a login/register
    if request.endpoint in {'login', 'register'} and session.get('user_id'):
        return redirect(url_for('home'))

# Rutas de autenticación
def _wants_json_response():
    if request.is_json:
        return True
    accept = request.headers.get('Accept', '')
    if 'application/json' in accept:
        return True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    return False
@app.route('/auth/register', methods=['POST'])
def auth_register():
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password')
        is_company = data.get('is_company', False)
        cif = (data.get('cif') or '').strip().upper() if is_company else None
        company_logo_file = None
    else:
        data = request.form
        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip().lower()
        password = data.get('password')
        is_company = data.get('is_company') == 'true' or data.get('is_company') == True
        cif = (data.get('cif') or '').strip().upper() if is_company else None
        company_logo_file = request.files.get('company_logo')

    if not email or not password:
        if _wants_json_response():
            return jsonify(message='Email y contraseña son obligatorios.'), 400
        return render_template('auth_message.html', message='Email y contraseña son obligatorios.'), 400
    
    # Validate CIF for company users
    if is_company and not cif:
        if _wants_json_response():
            return jsonify(message='El CIF es obligatorio para empresas.'), 400
        return render_template('auth_message.html', message='El CIF es obligatorio para empresas.'), 400
    
    # Basic CIF format validation
    if is_company and cif:
        if len(cif) < 8 or len(cif) > 20:
            if _wants_json_response():
                return jsonify(message='El CIF debe tener entre 8 y 20 caracteres.'), 400
            return render_template('auth_message.html', message='El CIF debe tener entre 8 y 20 caracteres.'), 400
    
    # Check if CIF already exists for company users
    if is_company and cif:
        existing_cif = User.query.filter_by(cif=cif).first()
        if existing_cif:
            if _wants_json_response():
                return jsonify(message='Este CIF ya está registrado.'), 409
            return render_template('auth_message.html', message='Este CIF ya está registrado.'), 409

    existing = User.query.filter_by(email=email).first()
    if existing:
        if _wants_json_response():
            return jsonify(message='Este email ya está registrado.'), 409
        return render_template('auth_message.html', message='Este email ya está registrado.'), 409

    import secrets, threading
    token = secrets.token_urlsafe(32)
    
    # Check for invitation
    invitation_code = data.get('invitation_code') or session.get('invitation_code')
    invitation = None
    inviter = None
    
    if invitation_code:
        invitation = Invitation.query.filter_by(invitation_code=invitation_code).first()
        if invitation and invitation.status == 'pending' and datetime.utcnow() <= invitation.expires_at:
            inviter = User.query.get(invitation.inviter_id)
    
    # Generate user invitation code for future invitations
    user_invitation_code = secrets.token_urlsafe(16)
    
    # Handle company logo upload
    company_logo_path = None
    if is_company and company_logo_file and company_logo_file.filename:
        import os
        from werkzeug.utils import secure_filename
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(app.static_folder, 'uploads', 'company_logos')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        filename = secure_filename(company_logo_file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{secrets.token_hex(8)}{ext}"
        logo_path = os.path.join(upload_dir, unique_filename)
        
        # Save the file
        company_logo_file.save(logo_path)
        company_logo_path = f"uploads/company_logos/{unique_filename}"
    
    user = User(
        name=name, 
        email=email, 
        verification_token=token,
        invitation_code=user_invitation_code,
        invited_by_id=inviter.id if inviter else None,
        is_company=is_company,
        cif=cif,
        company_logo=company_logo_path
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    # Handle invitation acceptance
    if invitation and inviter:
        invitation.status = 'accepted'
        invitation.accepted_at = datetime.utcnow()
        
        # Award points to inviter
        INVITATION_REWARD_POINTS = 50
        inviter.glopy_points += INVITATION_REWARD_POINTS
        
        # Create points transaction record
        transaction = PointsTransaction(
            user_id=inviter.id,
            points=INVITATION_REWARD_POINTS,
            transaction_type='invitation_reward',
            description=f'Recompensa por invitar a {email}',
            related_invitation_id=invitation.id
        )
        db.session.add(transaction)
        db.session.commit()
        
        # Clear invitation from session
        if 'invitation_code' in session:
            del session['invitation_code']
        if 'invited_email' in session:
            del session['invited_email']

    verify_url = url_for('auth_verify', token=token, _external=True)
    html = render_template('email/verify.html', verify_url=verify_url, user_name=name or email, **_brand_ctx())
    text = f"Hola,\n\nGracias por registrarte en {APP_NAME}. Verifica tu cuenta haciendo clic en el siguiente enlace:\n{verify_url}\n\nSi tú no iniciaste este registro, ignora este correo."

    def _send_email_async():
        try:
            # Flask-Mail necesita el contexto de la aplicación, especialmente en hilos
            with app.app_context():
                msg = Message(
                    subject=f"Verifica tu cuenta en {APP_NAME}",
                    recipients=[email],
                    body=text,
                    html=html,
                )
                mail.send(msg)
                # Logs visibles en producción
                try:
                    app.logger.info(f"[EMAIL] Correo de verificacion enviado a {email}")
                except Exception:
                    pass
                try:
                    print(f"Correo de verificacion enviado a {email}")
                except Exception:
                    pass
        except Exception as e:
            # Este es el error que queremos ver en los logs
            try:
                app.logger.error(
                    f"[ERROR EMAIL] No se pudo enviar email de verificacion a {email}: {e}",
                    exc_info=True,
                )
            except Exception:
                pass
            try:
                print(f"[ADVERTENCIA] No se pudo enviar email de verificacion: {e}")
                print(f"[EMAIL DE VERIFICACION - DEBUG] {email}: {verify_url}")
            except Exception:
                pass

    # --- Enviar de forma sincrona para depuracion ---
    try:
        app.logger.info("Enviando correo de forma sincrona para depuracion...")
    except Exception:
        pass
    _send_email_async()

    if _wants_json_response():
        return jsonify(message='Registro correcto. Revisa tu correo para verificar tu cuenta.'), 200
    return render_template('auth_message.html', message='Registro correcto. Revisa tu correo para verificar tu cuenta.')


@app.route('/auth/verify/<token>')
def auth_verify(token):
    user = User.query.filter_by(verification_token=token).first()
    if not user:
        return render_template('auth_message.html', message='Enlace de verificación inválido o expirado.'), 400

    user.is_verified = True
    user.verification_token = None
    db.session.commit()
    return render_template('auth_message.html', message='¡Cuenta verificada! Ya puedes iniciar sesión.')


@app.route('/auth/login', methods=['POST'])
def auth_login():
    data = request.form if request.form else request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password')

    if not email or not password:
        if _wants_json_response():
            return jsonify(message='Email y contraseña son obligatorios.'), 400
        return render_template('auth_message.html', message='Email y contraseña son obligatorios.'), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        if _wants_json_response():
            return jsonify(message='Credenciales inválidas.'), 401
        return render_template('auth_message.html', message='Credenciales inválidas.'), 401

    if not user.is_verified:
        if _wants_json_response():
            return jsonify(message='Debes verificar tu correo antes de iniciar sesión.'), 403
        return render_template('auth_message.html', message='Debes verificar tu correo antes de iniciar sesión.'), 403

    session['user_id'] = user.id
    session['user_email'] = user.email
    session['user_name'] = user.name
    session['is_admin'] = user.is_admin  # Store admin status in session
    
    # Redirect admins to admin dashboard, regular users to home
    redirect_url = url_for('admin_dashboard') if user.is_admin else url_for('home')
    
    if _wants_json_response():
        return jsonify(message='Login correcto', next=redirect_url), 200
    return redirect(redirect_url)


@app.route('/auth/logout', methods=['POST', 'GET'])
def auth_logout():
    session.clear()
    return redirect(url_for('login'))


# ---------------------------------
# INVITATION SYSTEM
# ---------------------------------

def _require_login(fn):
    """Decorator to require user login"""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            # For API endpoints, always return JSON
            if fn.__name__.startswith('get_') or fn.__name__.startswith('send_') or '/api/' in request.path:
                return jsonify(message='Debes iniciar sesión para acceder a esta función.'), 401
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper


def _require_admin(fn):
    """Decorator to require admin privileges"""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            if '/api/' in request.path:
                return jsonify(message='Debes iniciar sesión para acceder a esta función.'), 401
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            if '/api/' in request.path:
                return jsonify(message='No tienes permisos de administrador.'), 403
            return render_template('auth_message.html', message='No tienes permisos de administrador.'), 403
        
        return fn(*args, **kwargs)
    return wrapper


@app.route('/api/invite/send', methods=['POST'])
@_require_login
def send_invitation():
    """Send an invitation to a user by email"""
    data = request.get_json()
    if not data:
        return jsonify(message='Datos JSON requeridos.'), 400
    
    invited_email = data.get('email', '').strip().lower()
    if not invited_email:
        return jsonify(message='Email es requerido.'), 400
    
    # Check if user is already registered
    existing_user = User.query.filter_by(email=invited_email).first()
    if existing_user:
        return jsonify(message='Este email ya está registrado en Glopy.'), 409
    
    # Check if there's already a pending invitation for this email
    existing_invitation = Invitation.query.filter_by(
        invited_email=invited_email, 
        status='pending'
    ).first()
    if existing_invitation:
        return jsonify(message='Ya existe una invitación pendiente para este email.'), 409
    
    # Get current user
    current_user = User.query.get(session['user_id'])
    if not current_user:
        return jsonify(message='Usuario no encontrado.'), 404
    
    # Generate invitation code
    import secrets
    invitation_code = secrets.token_urlsafe(32)
    
    # Create invitation (expires in 7 days)
    from datetime import timedelta
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    invitation = Invitation(
        inviter_id=current_user.id,
        invited_email=invited_email,
        invitation_code=invitation_code,
        expires_at=expires_at
    )
    
    db.session.add(invitation)
    db.session.commit()
    
    # Send invitation email
    invitation_url = url_for('accept_invitation', code=invitation_code, _external=True)
    
    html = render_template('email/invitation.html', 
                         invitation_url=invitation_url,
                         inviter_name=current_user.name or current_user.email,
                         invited_email=invited_email,
                         **_brand_ctx())
    
    text = f"""Hola,

{current_user.name or current_user.email} te ha invitado a unirte a {APP_NAME}!

Glopy es una plataforma donde puedes encontrar y publicar anuncios de inmuebles, coches, electrónica y más.

Haz clic en el siguiente enlace para aceptar la invitación:
{invitation_url}

Esta invitación expira en 7 días.

¡Esperamos verte pronto en {APP_NAME}!

El equipo de {APP_NAME}
"""
    
    def _send_invitation_email():
        try:
            with app.app_context():
                msg = Message(
                    subject=f"¡{current_user.name or current_user.email} te invita a {APP_NAME}!",
                    recipients=[invited_email],
                    body=text,
                    html=html,
                )
                mail.send(msg)
                app.logger.info(f"[EMAIL] Invitación enviada a {invited_email}")
        except Exception as e:
            app.logger.error(f"[ERROR EMAIL] No se pudo enviar invitación a {invited_email}: {e}")
    
    # Send email asynchronously
    threading.Thread(target=_send_invitation_email, daemon=True).start()
    
    return jsonify({
        'message': 'Invitación enviada exitosamente.',
        'invitation_code': invitation_code,
        'expires_at': expires_at.isoformat()
    }), 200


@app.route('/invite/accept/<code>')
def accept_invitation(code):
    """Accept an invitation and redirect to registration with invitation code"""
    invitation = Invitation.query.filter_by(invitation_code=code).first()
    
    if not invitation:
        return render_template('auth_message.html', 
                             message='Código de invitación inválido.'), 404
    
    if invitation.status != 'pending':
        return render_template('auth_message.html', 
                             message='Esta invitación ya ha sido utilizada.'), 400
    
    if datetime.utcnow() > invitation.expires_at:
        return render_template('auth_message.html', 
                             message='Esta invitación ha expirado.'), 400
    
    # Store invitation code in session for registration
    session['invitation_code'] = code
    session['invited_email'] = invitation.invited_email
    
    return redirect(url_for('register'))


@app.route('/api/invite/accept', methods=['POST'])
def accept_invitation_api():
    """API endpoint to accept invitation during registration"""
    data = request.get_json()
    if not data:
        return jsonify(message='Datos JSON requeridos.'), 400
    
    invitation_code = data.get('invitation_code')
    if not invitation_code:
        return jsonify(message='Código de invitación requerido.'), 400
    
    invitation = Invitation.query.filter_by(invitation_code=invitation_code).first()
    
    if not invitation:
        return jsonify(message='Código de invitación inválido.'), 404
    
    if invitation.status != 'pending':
        return jsonify(message='Esta invitación ya ha sido utilizada.'), 400
    
    if datetime.utcnow() > invitation.expires_at:
        return jsonify(message='Esta invitación ha expirado.'), 400
    
    # Mark invitation as accepted
    invitation.status = 'accepted'
    invitation.accepted_at = datetime.utcnow()
    
    # Award points to inviter
    INVITATION_REWARD_POINTS = 50  # Points for successful invitation
    inviter = User.query.get(invitation.inviter_id)
    if inviter:
        inviter.glopy_points += INVITATION_REWARD_POINTS
        
        # Create points transaction record
        transaction = PointsTransaction(
            user_id=inviter.id,
            points=INVITATION_REWARD_POINTS,
            transaction_type='invitation_reward',
            description=f'Recompensa por invitar a {invitation.invited_email}',
            related_invitation_id=invitation.id
        )
        db.session.add(transaction)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Invitación aceptada exitosamente.',
        'inviter_name': inviter.name if inviter else 'Usuario',
        'points_awarded': INVITATION_REWARD_POINTS
    }), 200


@app.route('/api/points/balance')
@_require_login
def get_points_balance():
    """Get current user's Glopy points balance"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify(message='Usuario no encontrado.'), 404
    
    return jsonify({
        'success': True,
        'glopy_points': user.glopy_points,
        'user_name': user.name or user.email
    }), 200


@app.route('/api/points/transactions')
@_require_login
def get_points_transactions():
    """Get user's points transaction history"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify(message='Usuario no encontrado.'), 404
    
    transactions = PointsTransaction.query.filter_by(user_id=user.id)\
        .order_by(PointsTransaction.created_at.desc())\
        .limit(50).all()
    
    transaction_list = []
    for t in transactions:
        transaction_list.append({
            'id': t.id,
            'points': t.points,
            'transaction_type': t.transaction_type,
            'description': t.description,
            'created_at': t.created_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'transactions': transaction_list,
        'total_points': user.glopy_points
    }), 200


# ---------------------------------
# ADMIN SYSTEM
# ---------------------------------

def _log_admin_action(action, target_type=None, target_id=None, details=None):
    """Log admin actions for audit trail"""
    if 'user_id' in session:
        admin_log = AdminLog(
            admin_id=session['user_id'],
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=request.remote_addr
        )
        db.session.add(admin_log)
        db.session.commit()


@app.route('/admin')
@_require_admin
def admin_dashboard():
    """Admin dashboard main page"""
    # Get statistics
    total_users = User.query.count()
    total_ads = Announcement.query.count()
    total_categories = RealEstateCategory.query.count()
    total_payments = Payment.query.filter_by(status='succeeded').count()
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='succeeded').scalar() or 0
    
    # Recent activity
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_ads = Announcement.query.order_by(Announcement.published_date.desc()).limit(5).all()
    recent_payments = Payment.query.filter_by(status='succeeded').order_by(Payment.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_ads=total_ads,
                         total_categories=total_categories,
                         total_payments=total_payments,
                         total_revenue=total_revenue,
                         recent_users=recent_users,
                         recent_ads=recent_ads,
                         recent_payments=recent_payments,
                         **_brand_ctx())


@app.route('/admin/users')
@_require_admin
def admin_users():
    """Admin users management page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    query = User.query
    if search:
        query = query.filter(
            db.or_(
                User.name.contains(search),
                User.email.contains(search)
            )
        )
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html', users=users, search=search, **_brand_ctx())


@app.route('/admin/ads')
@_require_admin
def admin_ads():
    """Admin ads management page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status = request.args.get('status', '', type=str)
    
    query = Announcement.query
    if search:
        query = query.filter(Announcement.title.contains(search))
    if status:
        # Add status filtering logic here if needed
        pass
    
    ads = query.order_by(Announcement.published_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/ads.html', ads=ads, search=search, status=status, **_brand_ctx())


@app.route('/admin/categories')
@_require_admin
def admin_categories():
    """Admin categories management page"""
    categories = RealEstateCategory.query.all()
    return render_template('admin/categories.html', categories=categories, **_brand_ctx())


@app.route('/admin/pricing')
@_require_admin
def admin_pricing():
    """Admin pricing configuration page"""
    pricing_plan = PricingPlan.query.filter_by(is_active=True).first()
    if not pricing_plan:
        # Create default pricing plan
        pricing_plan = PricingPlan(
            name='Default Plan',
            description='Default pricing for premium ads',
            price_per_ad=5.0,
            max_free_ads=100000  # High limit for app launch period
        )
        db.session.add(pricing_plan)
        db.session.commit()
    
    return render_template('admin/pricing.html', pricing_plan=pricing_plan, **_brand_ctx())


@app.route('/admin/payments')
@_require_admin
def admin_payments():
    """Admin payments overview page"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    
    query = Payment.query
    if status:
        query = query.filter_by(status=status)
    
    payments = query.order_by(Payment.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/payments.html', payments=payments, status=status, **_brand_ctx())


@app.route('/admin/commercial-ads')
@_require_admin
def admin_commercial_ads():
    """Admin commercial ads management page"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    
    query = CommercialAd.query
    if status:
        query = query.filter_by(status=status)
    
    ads = query.order_by(CommercialAd.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get stats
    total_active = CommercialAd.query.filter_by(status='active').count()
    total_views = db.session.query(db.func.sum(CommercialAd.views_count)).scalar() or 0
    total_clicks = db.session.query(db.func.sum(CommercialAd.clicks_count)).scalar() or 0
    
    return render_template('admin/commercial_ads.html', 
                          ads=ads, 
                          status=status,
                          total_active=total_active,
                          total_views=total_views,
                          total_clicks=total_clicks,
                          **_brand_ctx())


@app.route('/admin/commercial-ads/create', methods=['GET', 'POST'])
@_require_admin
def admin_create_commercial_ad():
    """Create a new commercial ad"""
    if request.method == 'POST':
        try:
            data = request.form
            
            # Handle image upload
            image_url = None
            if 'image' in request.files:
                image_file = request.files['image']
                if image_file and image_file.filename:
                    filename = f"commercial_{datetime.utcnow().timestamp()}_{image_file.filename}"
                    image_path = os.path.join('static', 'uploads', 'commercial_ads', filename)
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    image_file.save(image_path)
                    image_url = f'/static/uploads/commercial_ads/{filename}'
            
            # Handle company logo upload
            company_logo = None
            if 'company_logo' in request.files:
                logo_file = request.files['company_logo']
                if logo_file and logo_file.filename:
                    filename = f"logo_{datetime.utcnow().timestamp()}_{logo_file.filename}"
                    logo_path = os.path.join('static', 'uploads', 'commercial_ads', filename)
                    logo_file.save(logo_path)
                    company_logo = f'/static/uploads/commercial_ads/{filename}'
            
            # Parse dates
            from dateutil import parser as date_parser
            start_date = date_parser.parse(data.get('start_date'))
            end_date = date_parser.parse(data.get('end_date'))
            
            new_ad = CommercialAd(
                title=data.get('title'),
                description=data.get('description'),
                image_url=image_url,
                target_url=data.get('target_url'),
                call_to_action=data.get('call_to_action', 'Ver más'),
                company_name=data.get('company_name'),
                company_logo=company_logo,
                contact_email=data.get('contact_email'),
                contact_phone=data.get('contact_phone'),
                placement_frequency=int(data.get('placement_frequency', 4)),
                priority=int(data.get('priority', 1)),
                category_id=int(data.get('category_id')) if data.get('category_id') else None,
                status=data.get('status', 'active'),
                start_date=start_date,
                end_date=end_date,
                price_paid=float(data.get('price_paid')) if data.get('price_paid') else None,
                payment_reference=data.get('payment_reference'),
                notes=data.get('notes'),
                created_by_id=session['user_id']
            )
            
            db.session.add(new_ad)
            db.session.commit()
            
            _log_admin_action('create_commercial_ad', 'commercial_ad', new_ad.id, f'Created ad: {new_ad.title}')
            
            flash('Anuncio comercial creado exitosamente', 'success')
            return redirect(url_for('admin_commercial_ads'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el anuncio: {str(e)}', 'danger')
    
    categories = RealEstateCategory.query.all()
    return render_template('admin/commercial_ad_form.html', 
                          ad=None, 
                          categories=categories,
                          **_brand_ctx())


@app.route('/admin/commercial-ads/<int:ad_id>/edit', methods=['GET', 'POST'])
@_require_admin
def admin_edit_commercial_ad(ad_id):
    """Edit an existing commercial ad"""
    ad = CommercialAd.query.get_or_404(ad_id)
    
    if request.method == 'POST':
        try:
            data = request.form
            
            # Handle image upload
            if 'image' in request.files:
                image_file = request.files['image']
                if image_file and image_file.filename:
                    filename = f"commercial_{datetime.utcnow().timestamp()}_{image_file.filename}"
                    image_path = os.path.join('static', 'uploads', 'commercial_ads', filename)
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    image_file.save(image_path)
                    ad.image_url = f'/static/uploads/commercial_ads/{filename}'
            
            # Handle company logo upload
            if 'company_logo' in request.files:
                logo_file = request.files['company_logo']
                if logo_file and logo_file.filename:
                    filename = f"logo_{datetime.utcnow().timestamp()}_{logo_file.filename}"
                    logo_path = os.path.join('static', 'uploads', 'commercial_ads', filename)
                    logo_file.save(logo_path)
                    ad.company_logo = f'/static/uploads/commercial_ads/{filename}'
            
            # Parse dates
            from dateutil import parser as date_parser
            start_date = date_parser.parse(data.get('start_date'))
            end_date = date_parser.parse(data.get('end_date'))
            
            # Update fields
            ad.title = data.get('title')
            ad.description = data.get('description')
            ad.target_url = data.get('target_url')
            ad.call_to_action = data.get('call_to_action', 'Ver más')
            ad.company_name = data.get('company_name')
            ad.contact_email = data.get('contact_email')
            ad.contact_phone = data.get('contact_phone')
            ad.placement_frequency = int(data.get('placement_frequency', 4))
            ad.priority = int(data.get('priority', 1))
            ad.category_id = int(data.get('category_id')) if data.get('category_id') else None
            ad.status = data.get('status', 'active')
            ad.start_date = start_date
            ad.end_date = end_date
            ad.price_paid = float(data.get('price_paid')) if data.get('price_paid') else None
            ad.payment_reference = data.get('payment_reference')
            ad.notes = data.get('notes')
            
            db.session.commit()
            
            _log_admin_action('update_commercial_ad', 'commercial_ad', ad.id, f'Updated ad: {ad.title}')
            
            flash('Anuncio comercial actualizado exitosamente', 'success')
            return redirect(url_for('admin_commercial_ads'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el anuncio: {str(e)}', 'danger')
    
    categories = RealEstateCategory.query.all()
    return render_template('admin/commercial_ad_form.html', 
                          ad=ad, 
                          categories=categories,
                          **_brand_ctx())


@app.route('/admin/commercial-ads/<int:ad_id>/delete', methods=['POST'])
@_require_admin
def admin_delete_commercial_ad(ad_id):
    """Delete a commercial ad"""
    ad = CommercialAd.query.get_or_404(ad_id)
    
    try:
        title = ad.title
        db.session.delete(ad)
        db.session.commit()
        
        _log_admin_action('delete_commercial_ad', 'commercial_ad', ad_id, f'Deleted ad: {title}')
        
        return jsonify({
            'success': True,
            'message': 'Anuncio comercial eliminado exitosamente'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error al eliminar el anuncio: {str(e)}'
        }), 500


@app.route('/admin/commercial-ads/<int:ad_id>/toggle-status', methods=['POST'])
@_require_admin
def admin_toggle_commercial_ad_status(ad_id):
    """Toggle commercial ad status between active and paused"""
    ad = CommercialAd.query.get_or_404(ad_id)
    
    try:
        ad.status = 'paused' if ad.status == 'active' else 'active'
        db.session.commit()
        
        _log_admin_action('toggle_commercial_ad_status', 'commercial_ad', ad.id, f'Status: {ad.status}')
        
        return jsonify({
            'success': True,
            'message': f'Estado actualizado a: {ad.status}',
            'status': ad.status
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error al cambiar el estado: {str(e)}'
        }), 500


@app.route('/admin/commercial-ads/<int:ad_id>/stats')
@_require_admin
def admin_commercial_ad_stats(ad_id):
    """Get detailed statistics for a commercial ad"""
    ad = CommercialAd.query.get_or_404(ad_id)
    
    # Get views by date
    views_by_date = db.session.query(
        db.func.date(CommercialAdView.viewed_at).label('date'),
        db.func.count(CommercialAdView.id).label('count')
    ).filter(
        CommercialAdView.ad_id == ad_id
    ).group_by(
        db.func.date(CommercialAdView.viewed_at)
    ).order_by(
        db.func.date(CommercialAdView.viewed_at).desc()
    ).limit(30).all()
    
    # Get clicks by date
    clicks_by_date = db.session.query(
        db.func.date(CommercialAdClick.clicked_at).label('date'),
        db.func.count(CommercialAdClick.id).label('count')
    ).filter(
        CommercialAdClick.ad_id == ad_id
    ).group_by(
        db.func.date(CommercialAdClick.clicked_at)
    ).order_by(
        db.func.date(CommercialAdClick.clicked_at).desc()
    ).limit(30).all()
    
    return render_template('admin/commercial_ad_stats.html',
                          ad=ad,
                          views_by_date=views_by_date,
                          clicks_by_date=clicks_by_date,
                          **_brand_ctx())


# Public Commercial Ad Tracking Endpoints
@app.route('/api/commercial-ads/<int:ad_id>/click', methods=['POST'])
def track_commercial_ad_click(ad_id):
    """Track a click on a commercial ad"""
    ad = CommercialAd.query.get_or_404(ad_id)
    
    try:
        # Increment counter on ad
        ad.increment_clicks()
        
        # Log detailed click
        click = CommercialAdClick(
            ad_id=ad_id,
            user_id=session.get('user_id'),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(click)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'redirect_url': ad.target_url
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/commercial-ads/<int:ad_id>/view', methods=['POST'])
def track_commercial_ad_view(ad_id):
    """Track a view of a commercial ad"""
    ad = CommercialAd.query.get_or_404(ad_id)
    
    try:
        # Increment counter on ad
        ad.increment_views()
        
        # Log detailed view
        view = CommercialAdView(
            ad_id=ad_id,
            user_id=session.get('user_id'),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(view)
        db.session.commit()
        
        return jsonify({
            'success': True
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# Admin API endpoints
@app.route('/api/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@_require_admin
def toggle_user_admin(user_id):
    """Toggle admin status for a user"""
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    
    _log_admin_action('toggle_admin', 'user', user_id, f'Admin status: {user.is_admin}')
    
    return jsonify({
        'success': True,
        'message': f'Admin status updated for {user.email}',
        'is_admin': user.is_admin
    }), 200


@app.route('/api/admin/users/<int:user_id>/toggle-premium', methods=['POST'])
@_require_admin
def toggle_user_premium(user_id):
    """Toggle premium status for a user"""
    user = User.query.get_or_404(user_id)
    user.is_premium = not user.is_premium
    if user.is_premium:
        from datetime import timedelta
        user.premium_expires_at = datetime.utcnow() + timedelta(days=30)
    else:
        user.premium_expires_at = None
    db.session.commit()
    
    _log_admin_action('toggle_premium', 'user', user_id, f'Premium status: {user.is_premium}')
    
    return jsonify({
        'success': True,
        'message': f'Premium status updated for {user.email}',
        'is_premium': user.is_premium
    }), 200


@app.route('/api/admin/ads/<int:ad_id>/delete', methods=['POST'])
@_require_admin
def delete_ad(ad_id):
    """Delete an ad (admin only)"""
    ad = Announcement.query.get_or_404(ad_id)
    ad_title = ad.title
    db.session.delete(ad)
    db.session.commit()
    
    _log_admin_action('delete_ad', 'ad', ad_id, f'Deleted ad: {ad_title}')
    
    return jsonify({
        'success': True,
        'message': f'Ad "{ad_title}" deleted successfully'
    }), 200


@app.route('/api/admin/pricing/update', methods=['POST'])
@_require_admin
def update_pricing():
    """Update pricing configuration"""
    data = request.get_json()
    if not data:
        return jsonify(message='Datos JSON requeridos.'), 400
    
    pricing_plan = PricingPlan.query.filter_by(is_active=True).first()
    if not pricing_plan:
        pricing_plan = PricingPlan()
        db.session.add(pricing_plan)
    
    pricing_plan.name = data.get('name', pricing_plan.name)
    pricing_plan.description = data.get('description', pricing_plan.description)
    pricing_plan.price_per_ad = float(data.get('price_per_ad', pricing_plan.price_per_ad))
    pricing_plan.max_free_ads = int(data.get('max_free_ads', pricing_plan.max_free_ads))
    
    db.session.commit()
    
    _log_admin_action('update_pricing', 'pricing', pricing_plan.id, 
                     f'Updated pricing: €{pricing_plan.price_per_ad}/ad, {pricing_plan.max_free_ads} free ads')
    
    return jsonify({
        'success': True,
        'message': 'Pricing configuration updated successfully',
        'pricing_plan': {
            'id': pricing_plan.id,
            'name': pricing_plan.name,
            'price_per_ad': pricing_plan.price_per_ad,
            'max_free_ads': pricing_plan.max_free_ads
        }
    }), 200


# ---------------------------------
# STRIPE PAYMENT SYSTEM
# ---------------------------------

@app.route('/api/create-payment-intent', methods=['POST'])
@_require_login
def create_payment_intent():
    """Create Stripe payment intent for premium ad posting"""
    if not STRIPE_SECRET_KEY:
        return jsonify(message='Stripe no está configurado.'), 500
    
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    
    data = request.get_json()
    if not data:
        return jsonify(message='Datos JSON requeridos.'), 400
    
    # Get current pricing
    pricing_plan = PricingPlan.query.filter_by(is_active=True).first()
    if not pricing_plan:
        return jsonify(message='No hay configuración de precios disponible.'), 400
    
    amount = int(pricing_plan.price_per_ad * 100)  # Convert to cents
    
    try:
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='eur',
            metadata={
                'user_id': session['user_id'],
                'pricing_plan_id': pricing_plan.id
            }
        )
        
        # Create payment record
        payment = Payment(
            user_id=session['user_id'],
            stripe_payment_intent_id=intent.id,
            amount=pricing_plan.price_per_ad,
            currency='EUR',
            status='pending',
            description=f'Premium ad posting - {pricing_plan.name}'
        )
        db.session.add(payment)
        db.session.commit()
        
        return jsonify({
            'client_secret': intent.client_secret,
            'payment_id': payment.id
        }), 200
        
    except stripe.error.StripeError as e:
        return jsonify(message=f'Error de Stripe: {str(e)}'), 400


@app.route('/api/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    if not STRIPE_WEBHOOK_SECRET:
        return jsonify(message='Webhook secret not configured'), 400
    
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return jsonify(message='Invalid payload'), 400
    except stripe.error.SignatureVerificationError:
        return jsonify(message='Invalid signature'), 400
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        
        # Find the payment record
        payment = Payment.query.filter_by(
            stripe_payment_intent_id=payment_intent['id']
        ).first()
        
        if payment:
            # Update payment status
            payment.status = 'succeeded'
            payment.payment_method = payment_intent.get('charges', {}).get('data', [{}])[0].get('payment_method_details', {}).get('type', 'card')
            db.session.commit()
            
            # Grant premium ad posting (reset free ads counter)
            user = User.query.get(payment.user_id)
            if user:
                user.free_ads_used = 0  # Reset free ads counter
                db.session.commit()
    
    return jsonify(status='success'), 200

@app.route('/api/confirm-payment', methods=['POST'])
@_require_login
def confirm_payment():
    """Confirm payment and grant premium ad posting"""
    data = request.get_json()
    if not data:
        return jsonify(message='Datos JSON requeridos.'), 400
    
    payment_id = data.get('payment_id')
    if not payment_id:
        return jsonify(message='ID de pago requerido.'), 400
    
    payment = Payment.query.get(payment_id)
    if not payment or payment.user_id != session['user_id']:
        return jsonify(message='Pago no encontrado.'), 404
    
    if not STRIPE_SECRET_KEY:
        return jsonify(message='Stripe no está configurado.'), 500
    
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    
    try:
        # Check if payment is already confirmed
        if payment.status == 'succeeded':
            return jsonify({
                'success': True,
                'message': 'Pago ya confirmado. Ya puedes publicar anuncios premium.',
                'payment_status': 'succeeded'
            }), 200
        
        # Retrieve payment intent from Stripe
        intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
        
        if intent.status == 'succeeded':
            # Update payment status
            payment.status = 'succeeded'
            payment.payment_method = intent.charges.data[0].payment_method_details.type if intent.charges.data else 'card'
            db.session.commit()
            
            # Grant premium ad posting (reset free ads counter)
            user = User.query.get(session['user_id'])
            user.free_ads_used = 0  # Reset free ads counter
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Pago confirmado. Ya puedes publicar anuncios premium.',
                'payment_status': 'succeeded'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'El pago no se ha completado correctamente.',
                'payment_status': intent.status
            }), 400
            
    except stripe.error.StripeError as e:
        return jsonify(message=f'Error de Stripe: {str(e)}'), 400


@app.route('/api/check-ad-limit', methods=['GET'])
@_require_login
def check_ad_limit():
    """Check if user can post more ads"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify(message='Usuario no encontrado.'), 404
    
    pricing_plan = PricingPlan.query.filter_by(is_active=True).first()
    if not pricing_plan:
        # Create default pricing plan if none exists
        pricing_plan = PricingPlan(
            name='Plan Estándar',
            description='Plan de precios estándar para anuncios premium',
            price_per_ad=5.0,
            max_free_ads=100000,  # High limit for app launch period
            is_active=True
        )
        db.session.add(pricing_plan)
        db.session.commit()
    else:
        # Update existing pricing plan to ensure max_free_ads is set to 100000 for launch
        if pricing_plan.max_free_ads < 100000:
            pricing_plan.max_free_ads = 100000
            db.session.commit()
    
    # Handle None values for free_ads_used
    free_ads_used = user.free_ads_used or 0
    can_post_free = free_ads_used < pricing_plan.max_free_ads
    remaining_free = max(0, pricing_plan.max_free_ads - free_ads_used)
    
    return jsonify({
        'can_post_free': can_post_free,
        'remaining_free_ads': remaining_free,
        'total_free_ads': pricing_plan.max_free_ads,
        'used_free_ads': free_ads_used,
        'premium_price': pricing_plan.price_per_ad,
        'is_premium': user.is_premium
    }), 200


# ---------------------------------
# RUTAS
# ---------------------------------

# @app.route('/')
# def index():
#     """
#     Ruta para la página principal.
#     Intenta obtener los sectores desde la base de datos;
#     si no encuentra nada, se utiliza el diccionario original como fallback.
#     """
#     sectors_db = Sector.query.all()

#     if not sectors_db:
#         sector_list = []
#         for clave, valor in sectores.items():
#             sector_list.append({
#                 "nombre": valor["nombre"],
#                 "imagen_sector": valor["imagen_sector"],
#                 "route": clave
#             })
#         return render_template('index.html', sectores=sector_list)
#     else:
#         ROUTE_MAPPING = {
#             "Inmobiliaria": "inmobiliaria",
#             "Coches": "coches",
#             "Electrónica": "electronica",
#         }
#         sector_list = []
#         for s in sectors_db:
#             route = ROUTE_MAPPING.get(s.name, "#")
#             sector_list.append({
#                 "nombre": s.name,
#                 "imagen_sector": s.image_path,
#                 "route": route
#             })
#         return render_template('index.html', sectores=sector_list)

@app.route("/")
def index():
    # La ruta raíz ahora muestra el buscador con categorías
    return render_template("buscador.html")

@app.route("/login")
def login():
    # La ruta de login ahora está en /login
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/home")
@db_retry(max_retries=3, delay=2)
def home():
    # Creamos una lista específica con 6 elementos para "Búsquedas recientes",
    # usando los nombres EXACTOS de los archivos de tu carpeta de imágenes.
    busquedas_recientes = [
        {'imagen': 'inmobiliaria.jpg', 'route': 'inmobiliaria', 'title': 'Inmobiliaria', 'coming_soon': False},
        {'imagen': 'coches.jpg', 'route': 'autos', 'title': 'Vehículos', 'coming_soon': False},
        {'imagen': 'tecnologia.jpg', 'route': 'electronica', 'title': 'Tecnología', 'coming_soon': True},
        {'imagen': 'image_moto1.jpg', 'route': '#', 'title': 'Motos', 'coming_soon': True},
        {'imagen': 'image_home2.jpeg', 'route': 'inmobiliaria', 'title': 'Casas', 'coming_soon': False},
        {'imagen': 'imagen_carro1.jpg', 'route': 'autos', 'title': 'Autos', 'coming_soon': False},
        {'imagen': 'inmobiliaria.jpg', 'route': '#', 'title': 'Empleos', 'coming_soon': True},
        {'imagen': 'tecnologia.jpg', 'route': '#', 'title': 'Servicios', 'coming_soon': True},
        {'imagen': 'coches.jpg', 'route': '#', 'title': 'Moda', 'coming_soon': True},
        {'imagen': 'image_moto1.jpg', 'route': '#', 'title': 'Deportes', 'coming_soon': True},
        {'imagen': 'image_home2.jpeg', 'route': '#', 'title': 'Hogar & Jardín', 'coming_soon': True},
        {'imagen': 'imagen_carro1.jpg', 'route': '#', 'title': 'Mascotas', 'coming_soon': True},
    ]

    # Datos para las tarjetas de valoraciones
    valoraciones_data = [
        {
            'nombre': 'Olivia Méndez',
            'imagen': 'images.png', # Asegúrate de tener esta imagen
            'testimonio': 'Utilizo mucho la aplicación, ya que siempre encuentro lo que busco y al mejor precio.',
            'rating': '4.9 (37 Comentarios)'
        },
        {
            'nombre': 'Fernando Cruz',
            'imagen': 'images.png', # Y esta también
            'testimonio': 'Encontré la casa de mis sueños, gracias a esta increíble aplicación.',
            'rating': None
        }
    ]

    # Get real user data if logged in
    user_data = {}
    if session.get('user_id'):
        user = User.query.get(session['user_id'])
        if user:
            # Count saved ads
            saved_ads_count = SavedAd.query.filter_by(user_id=user.id).count()
            
            # Count saved searches
            saved_searches_count = SavedSearch.query.filter_by(user_id=user.id).count()
            
            # Get email alerts status
            email_alerts_enabled = user.email_alerts_enabled
            
            user_data = {
                'saved_ads_count': saved_ads_count,
                'saved_searches_count': saved_searches_count,
                'email_alerts_enabled': email_alerts_enabled,
                'is_admin': user.is_admin
            }

    # Pasamos ambas listas a la plantilla junto con los datos del usuario
    return render_template(
        "home.html", 
        busquedas=busquedas_recientes, 
        valoraciones=valoraciones_data,
        **user_data
    )

from sqlalchemy.orm import joinedload

@app.route('/anuncio/<int:announcement_id>')
@db_retry(max_retries=3, delay=2)
def announcement_detail(announcement_id):
    """
    Muestra la página de detalle (HTML) para un anuncio específico.
    """
    # 1. Usamos get_or_404 para buscar el anuncio por su ID.
    #    Si no lo encuentra, automáticamente mostrará tu página 404.html.
    #    'joinedload' es para cargar eficientemente los datos relacionados (imágenes, ubicación)
    #    y evitar consultas extra a la BD. Asumo que tus relaciones se llaman 'images' y 'location'.
    anuncio = Announcement.query.options(
        joinedload(Announcement.images), 
        joinedload(Announcement.location)
    ).get_or_404(announcement_id)

    # 2. Pasamos el objeto 'anuncio' completo a una nueva plantilla que crearemos.
    return render_template('announcement_detail.html', anuncio=anuncio)


from sqlalchemy.orm import joinedload
from models import Domain


def _inject_commercial_ads(regular_ads, category_id=None):
    """
    Inject commercial ads into the list of regular ads.
    Commercial ads are placed every 3-4 posts.
    
    Args:
        regular_ads: List of regular Announcement objects
        category_id: Optional category ID to filter commercial ads
    
    Returns:
        List with commercial ads injected at regular intervals
    """
    # Get active commercial ads
    query = CommercialAd.query.filter_by(status='active')
    
    # Filter by category if specified
    if category_id:
        query = query.filter(
            db.or_(
                CommercialAd.category_id == category_id,
                CommercialAd.category_id.is_(None)  # Also include ads with no specific category
            )
        )
    
    # Filter by date range
    now = datetime.utcnow()
    query = query.filter(
        CommercialAd.start_date <= now,
        CommercialAd.end_date >= now
    )
    
    # Order by priority (higher first) and last shown date (least recently shown first)
    # MySQL doesn't support NULLS FIRST, so we use COALESCE to put NULLs first
    commercial_ads = query.order_by(
        CommercialAd.priority.desc(),
        db.func.coalesce(CommercialAd.last_shown_at, datetime(1970, 1, 1)).asc()
    ).all()
    
    # If no commercial ads, return regular ads as is
    if not commercial_ads:
        return regular_ads
    
    # Inject commercial ads every 3-4 posts
    result = []
    commercial_index = 0
    next_commercial_at = 3  # Show first commercial ad after 3 regular ads
    
    for i, regular_ad in enumerate(regular_ads):
        result.append(regular_ad)
        
        # Check if we should inject a commercial ad
        if (i + 1) == next_commercial_at and commercial_index < len(commercial_ads):
            commercial_ad = commercial_ads[commercial_index]
            
            # Mark the commercial ad so the template can identify it
            commercial_ad.is_commercial = True
            result.append(commercial_ad)
            
            commercial_index += 1
            
            # Alternate between 3 and 4 posts for variety
            # Use the placement_frequency from the ad, defaulting to 4
            frequency = commercial_ad.placement_frequency or 4
            next_commercial_at += frequency
    
    return result


@app.route('/inmobiliaria')
@db_retry(max_retries=3, delay=2)
def inmobiliaria():
    """
    Muestra la seccion Inmobiliaria consultando la tabla 'announcements3'
    a traves del modelo 'Announcement'. Aplica los filtros del formulario y genera píldoras dinámicas.
    """
    categories = RealEstateCategory.query.all()

    # Optimizamos la consulta para cargar relaciones eficientemente.
    # ¡Asegúrate de que estas relaciones ('images', 'location') existan en tu models.py!
    query = Announcement.query.options(
        joinedload(Announcement.images),
        joinedload(Announcement.location) # Esto ya no dará error
    )

    location_id = request.args.get('location_id', type=int)
    location_name = None 

    if location_id:
        # Filtramos por la columna correcta 'sector_id'
        query = query.filter(Announcement.sector_id == location_id)
        # La búsqueda del nombre sigue funcionando con Geoname
        selected_location = Geoname.query.get(location_id)
        if selected_location:
            location_name = selected_location.name

    # --- INICIO DEL NUEVO BLOQUE: LÓGICA DE PÍLDORAS ---

    active_filters = []
    # Usamos request.args.copy() para poder modificarlo sin afectar al original
    filter_args = request.args.copy()

    # Mapeo de claves técnicas a etiquetas amigables para mostrar en las píldoras
    filter_labels = {
        'search_text': 'Texto: "{}"',
        'min_price': 'Desde {} €', 'max_price': 'Hasta {} €',
        'min_m2': 'Desde {} m²', 'max_m2': 'Hasta {} m²',
        'rooms': '{} o más hab.', 'bathrooms': '{} o más baños',
        'listing_type': 'Tipo: {}', 'property_type': 'Inmueble: {}',
        'housing_type': 'Vivienda: {}', 'property_state': 'Estado: {}',
        'advertiser_type': 'Anunciante: {}',
        # Checkboxes (estos no necesitan .format())
        'has_pool': 'Piscina', 'has_parking': 'Parking', 'has_air_conditioning': 'A/A',
        'has_heating': 'Calefacción', 'has_fitted_wardrobes': 'Armarios E.', 'has_elevator': 'Ascensor',
        'has_terrace': 'Terraza', 'is_exterior': 'Exterior', 'has_garden': 'Jardín',
        'has_storage_room': 'Trastero', 'is_accessible': 'Accesible',
        'pets_allowed': 'Mascotas'
    }

    # Iteramos sobre una copia de las claves para poder eliminar del diccionario original
    for key in list(filter_args.keys()):
        value = filter_args.get(key)
        
        # Ignoramos valores vacíos y claves que no queramos mostrar como píldoras (ej. cat_id)
        if value and key in filter_labels:
            if key == 'location_id': # Manejamos la píldora de ubicación de forma especial
                # Solo si realmente pudimos obtener el nombre de la ubicación
                if location_name:
                    active_filters.append({'key': key, 'label': location_name})
            else:
                label = filter_labels[key]
                if '{}' in label:
                    label = label.format(value)
                elif key == 'pets_allowed':
                    label = "Mascotas Sí" if value == '1' else "Mascotas No"
                active_filters.append({'key': key, 'label': label})

    # 3. Recogemos TODOS los parametros de filtro del formulario
    cat_id = request.args.get('cat_id', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    min_m2 = request.args.get('min_m2', type=float)
    max_m2 = request.args.get('max_m2', type=float)
    rooms = request.args.get('rooms', type=int)
    bathrooms = request.args.get('bathrooms', type=int)
    
    # La busqueda por 'city' ya no es posible porque quitamos esa columna
    # city = request.args.get('city', type=str) 

    listing_type = request.args.get('listing_type', type=str)
    property_type = request.args.get('property_type', type=str)
    housing_subtype = request.args.get('housing_type', type=str)
    property_state = request.args.get('property_state', type=str)
    rental_duration = request.args.get('rental_duration', type=str)
    furnished = request.args.get('furnished', type=str)
    pets_allowed_str = request.args.get('pets_allowed', type=str)
    capacity = to_numeric(request.args.get('capacity'), num_type=int)
    advertiser_type = request.args.get('advertiser_type', type=str) # Mapea a 'entity_type'
    published_from = request.args.get('published_from')
    published_to = request.args.get('published_to')
    
    # Checkboxes booleanos (vienen como "1" si estan marcados)
    has_pool = request.args.get('has_pool') == '1'
    has_parking = request.args.get('has_parking') == '1'
    # ... y asi para todos los demas...
    has_air_conditioning = request.args.get('has_air_conditioning') == '1'
    has_heating = request.args.get('has_heating') == '1'
    has_fitted_wardrobes = request.args.get('has_fitted_wardrobes') == '1'
    has_elevator = request.args.get('has_elevator') == '1'
    has_terrace = request.args.get('has_terrace') == '1'
    is_exterior = request.args.get('is_exterior') == '1'
    has_garden = request.args.get('has_garden') == '1'
    has_storage_room = request.args.get('has_storage_room') == '1'
    is_accessible = request.args.get('is_accessible') == '1'

    # 4. Aplicamos los filtros a la consulta UNO POR UNO
    if cat_id:
        query = query.filter(Announcement.category_id == cat_id)
    
    # Search text filter
    search_text = request.args.get('search_text', type=str)
    if search_text:
        # Search in title and description
        search_filter = db.or_(
            Announcement.title.ilike(f'%{search_text}%'),
            Announcement.description.ilike(f'%{search_text}%')
        )
        query = query.filter(search_filter)
    
    if min_price is not None:
        query = query.filter(Announcement.price >= min_price)
    if max_price is not None:
        query = query.filter(Announcement.price <= max_price)
    if min_m2 is not None:
        query = query.filter(Announcement.square_meters >= min_m2)
    if max_m2 is not None:
        query = query.filter(Announcement.square_meters <= max_m2)
    if rooms is not None:
        query = query.filter(Announcement.rooms >= rooms)
    if bathrooms is not None:
        query = query.filter(Announcement.number_of_bathrooms >= bathrooms)
    if property_type:
        query = query.filter(Announcement.property_type == property_type)
    if housing_subtype:
        query = query.filter(Announcement.housing_subtype == housing_subtype)
    if property_state:
        query = query.filter(Announcement.property_state == property_state)
    if listing_type:
        query = query.filter(Announcement.listing_type == listing_type)
    if rental_duration:
        query = query.filter(Announcement.rental_duration == rental_duration)
    if furnished: # Filtra por "Sí" o "No"
        query = query.filter(Announcement.furnished == furnished)
    if capacity is not None:
        query = query.filter(Announcement.capacity >= capacity)
    if advertiser_type:
        query = query.filter(Announcement.entity_type == advertiser_type)

    # Filtros para los checkboxes
    if has_pool: query = query.filter(Announcement.has_pool.is_(True))
    if has_parking: query = query.filter(Announcement.has_parking.is_(True))
    if has_air_conditioning: query = query.filter(Announcement.has_air_conditioning.is_(True))
    if has_heating: query = query.filter(Announcement.has_heating.is_(True))
    if has_fitted_wardrobes: query = query.filter(Announcement.has_fitted_wardrobes.is_(True))
    if has_elevator: query = query.filter(Announcement.has_elevator.is_(True))
    if has_terrace: query = query.filter(Announcement.has_terrace.is_(True))
    if is_exterior: query = query.filter(Announcement.is_exterior.is_(True))
    if has_garden: query = query.filter(Announcement.has_garden.is_(True))
    if has_storage_room: query = query.filter(Announcement.has_storage_room.is_(True))
    if is_accessible: query = query.filter(Announcement.is_accessible.is_(True))
        
    if pets_allowed_str == '1':
        query = query.filter(Announcement.pets_allowed.is_(True))
    elif pets_allowed_str == '0':
        query = query.filter(Announcement.pets_allowed.is_(False))

    # Filtro de fechas
    from datetime import datetime
    if published_from:
        try:
            date_from = datetime.strptime(published_from, '%Y-%m-%d').date()
            query = query.filter(Announcement.published_date >= date_from)
        except ValueError: pass # Ignora fechas invalidas
    if published_to:
        try:
            date_to = datetime.strptime(published_to, '%Y-%m-%d').date()
            query = query.filter(Announcement.published_date <= date_to)
        except ValueError: pass # Ignora fechas invalidas

    # 5. Aplicamos ordenamiento por fecha de publicación (más recientes primero)
    # Si tienen la misma fecha, ordenamos por ID descendente (más recientes primero)
    query = query.order_by(Announcement.published_date.desc(), Announcement.id.desc())
    
    # 6. Ejecutamos la consulta final para obtener los anuncios filtrados
    anuncios_filtrados = query.all()
    for anuncio in anuncios_filtrados:
        # Creamos un nuevo atributo en el objeto 'anuncio' para guardar la URL
        anuncio.domain_logo_url = None
        
        # 'anuncio.image' contiene el ID del dominio como un string. Lo usamos para buscar.
        if anuncio.image:
            try:
                # Convertimos el ID (que está como string en la columna 'image') a entero
                domain_id = int(anuncio.image)
                
                # Buscamos el dominio en la tabla Domain usando ese ID
                domain_obj = Domain.query.get(domain_id)
                
                # Si encontramos el dominio, guardamos la URL de su logo en nuestro nuevo atributo
                if domain_obj and domain_obj.image:
                    anuncio.domain_logo_url = domain_obj.image

            except (ValueError, TypeError):
                # Esto previene errores si 'anuncio.image' no es un número válido
                # Simplemente lo ignoramos y continuamos
                pass

    # 7. Inject commercial ads into the results
    anuncios_with_commercial = _inject_commercial_ads(anuncios_filtrados, cat_id)
    
    # 8. Preparamos los datos para la plantilla
    # La plantilla espera un objeto 'sector' con un atributo 'anuncios'.
    # Como ya no tenemos un sector, creamos un diccionario que lo simule.
    sector_data = {
        'nombre': 'Inmobiliaria',
        'anuncios': anuncios_with_commercial
    }

    return render_template(
        'inmobiliaria.html',
        sector=sector_data,
        categories=categories,
        selected_cat_id=cat_id,
        active_filters=active_filters,
        current_location_name=location_name 
    )


# ============================================
# AUTOMOBILES / VEHICLES SEARCH ENGINE
# ============================================

@app.route('/autos')
@db_retry(max_retries=3, delay=2)
def autos():
    """
    Automobiles search page - simplified search engine for vehicles
    """
    # Get all vehicle categories
    categories = VehicleCategory.query.order_by(VehicleCategory.display_order).all()
    popular_categories = VehicleCategory.query.filter_by(is_popular=True).order_by(VehicleCategory.display_order).limit(5).all()
    
    # Get all makes for autocomplete
    makes = VehicleMake.query.order_by(VehicleMake.display_order, VehicleMake.name).all()
    
    # Build query
    query = Vehicle.query.options(
        joinedload(Vehicle.images),
        joinedload(Vehicle.make),
        joinedload(Vehicle.model),
        joinedload(Vehicle.category),
        joinedload(Vehicle.location)
    )
    
    # Apply filters
    category_slug = request.args.get('category', type=str)
    make_id = request.args.get('make_id', type=int)
    model_id = request.args.get('model_id', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    min_year = request.args.get('min_year', type=int)
    max_year = request.args.get('max_year', type=int)
    fuel_type = request.args.get('fuel_type', type=str)
    location_id = request.args.get('location_id', type=int)
    
    # Advanced filters
    transmission = request.args.get('transmission', type=str)
    max_mileage = request.args.get('max_mileage', type=int)
    seller_type = request.args.get('seller_type', type=str)
    condition = request.args.get('condition', type=str)
    color = request.args.get('color', type=str)
    
    # Apply category filter
    if category_slug:
        category = VehicleCategory.query.filter_by(slug=category_slug).first()
        if category:
            query = query.filter(Vehicle.category_id == category.id)
    
    # Apply essential filters
    if make_id:
        query = query.filter(Vehicle.make_id == make_id)
    if model_id:
        query = query.filter(Vehicle.model_id == model_id)
    if min_price is not None:
        query = query.filter(Vehicle.price >= min_price)
    if max_price is not None:
        query = query.filter(Vehicle.price <= max_price)
    if min_year is not None:
        query = query.filter(Vehicle.year >= min_year)
    if max_year is not None:
        query = query.filter(Vehicle.year <= max_year)
    if fuel_type:
        query = query.filter(Vehicle.fuel_type == fuel_type)
    if location_id:
        query = query.filter(Vehicle.location_id == location_id)
    
    # Apply advanced filters
    if transmission:
        query = query.filter(Vehicle.transmission == transmission)
    if max_mileage is not None:
        query = query.filter(Vehicle.mileage <= max_mileage)
    if seller_type:
        query = query.filter(Vehicle.seller_type == seller_type)
    if condition:
        query = query.filter(Vehicle.condition == condition)
    if color:
        query = query.filter(Vehicle.color == color)
    
    # Order by: Featured first, then newest
    query = query.order_by(
        Vehicle.is_featured.desc(),
        Vehicle.published_date.desc(),
        Vehicle.id.desc()
    )
    
    # Execute query
    vehicles = query.all()
    
    # Inject commercial ads (reuse the same logic)
    vehicles_with_commercial = _inject_commercial_ads(vehicles, None)
    
    # Get selected make and model for display
    selected_make = VehicleMake.query.get(make_id) if make_id else None
    selected_model = VehicleModel.query.get(model_id) if model_id else None
    selected_location = Geoname.query.get(location_id) if location_id else None
    
    return render_template(
        'autos.html',
        vehicles=vehicles_with_commercial,
        categories=categories,
        popular_categories=popular_categories,
        makes=makes,
        selected_category=category_slug,
        selected_make=selected_make,
        selected_model=selected_model,
        selected_location=selected_location,
        filters={
            'min_price': min_price,
            'max_price': max_price,
            'min_year': min_year,
            'max_year': max_year,
            'fuel_type': fuel_type,
            'transmission': transmission,
            'max_mileage': max_mileage,
            'seller_type': seller_type,
            'condition': condition,
            'color': color
        }
    )


# API Endpoints for Vehicles

@app.route('/api/vehicles/makes')
def api_vehicle_makes():
    """Get all vehicle makes for autocomplete"""
    makes = VehicleMake.query.order_by(VehicleMake.display_order, VehicleMake.name).all()
    return jsonify([{
        'id': make.id,
        'name': make.name,
        'slug': make.slug
    } for make in makes])


@app.route('/api/vehicles/models/<int:make_id>')
def api_vehicle_models(make_id):
    """Get all models for a specific make"""
    models = VehicleModel.query.filter_by(make_id=make_id).order_by(VehicleModel.name).all()
    return jsonify([{
        'id': model.id,
        'name': model.name,
        'slug': model.slug
    } for model in models])


@app.route('/api/vehicles/search')
def api_vehicle_search():
    """AJAX search endpoint for vehicles"""
    # Get filters from request
    category_slug = request.args.get('category', type=str)
    make_id = request.args.get('make_id', type=int)
    model_id = request.args.get('model_id', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    min_year = request.args.get('min_year', type=int)
    max_year = request.args.get('max_year', type=int)
    fuel_type = request.args.get('fuel_type', type=str)
    location_id = request.args.get('location_id', type=int)
    
    # Build query
    query = Vehicle.query.options(
        joinedload(Vehicle.make),
        joinedload(Vehicle.model),
        joinedload(Vehicle.category),
        joinedload(Vehicle.location)
    )
    
    # Apply filters (same logic as main route)
    if category_slug:
        category = VehicleCategory.query.filter_by(slug=category_slug).first()
        if category:
            query = query.filter(Vehicle.category_id == category.id)
    
    if make_id:
        query = query.filter(Vehicle.make_id == make_id)
    if model_id:
        query = query.filter(Vehicle.model_id == model_id)
    if min_price is not None:
        query = query.filter(Vehicle.price >= min_price)
    if max_price is not None:
        query = query.filter(Vehicle.price <= max_price)
    if min_year is not None:
        query = query.filter(Vehicle.year >= min_year)
    if max_year is not None:
        query = query.filter(Vehicle.year <= max_year)
    if fuel_type:
        query = query.filter(Vehicle.fuel_type == fuel_type)
    if location_id:
        query = query.filter(Vehicle.location_id == location_id)
    
    # Order by featured and newest
    query = query.order_by(
        Vehicle.is_featured.desc(),
        Vehicle.published_date.desc()
    )
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    results = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Return JSON response
    return jsonify({
        'vehicles': [{
            'id': v.id,
            'title': v.title,
            'price': v.price,
            'year': v.year,
            'make': v.make.name if v.make else None,
            'model': v.model.name if v.model else None,
            'fuel_type': v.fuel_type,
            'mileage': v.mileage,
            'transmission': v.transmission,
            'location': v.location.name if v.location else None,
            'image': v.images[0].image_url if v.images else None,
            'is_featured': v.is_featured,
            'is_urgent': v.is_urgent,
            'is_new': v.is_new
        } for v in results.items],
        'total': results.total,
        'pages': results.pages,
        'current_page': results.page,
        'has_next': results.has_next,
        'has_prev': results.has_prev
    })


@app.route('/autos/<int:vehicle_id>')
def vehicle_detail(vehicle_id):
    """Vehicle detail page"""
    vehicle = Vehicle.query.options(
        joinedload(Vehicle.images),
        joinedload(Vehicle.make),
        joinedload(Vehicle.model),
        joinedload(Vehicle.category),
        joinedload(Vehicle.location),
        joinedload(Vehicle.user)
    ).get_or_404(vehicle_id)
    
    return render_template('vehicle_detail.html', vehicle=vehicle)


@app.route('/coches')
def coches():
    sector_db = Sector.query.filter_by(name='Coches').first()
    if sector_db:
        sector_data = {
            'nombre': sector_db.name,
            'anuncios': sector_db.announcements
        }
        return render_template('coches.html', sector=sector_data)
    else:
        sector = sectores.get('coches')
        return render_template('coches.html', sector=sector)


@app.route('/electronica')
def electronica():
    sector_db = Sector.query.filter_by(name='Electrónica').first()
    if sector_db:
        sector_data = {
            'nombre': sector_db.name,
            'anuncios': sector_db.announcements
        }
        return render_template('electronica.html', sector=sector_data)
    else:
        sector = sectores.get('electronica')
        return render_template('electronica.html', sector=sector)

@app.route('/buscador')
def buscador():
    return render_template('buscador.html')

@app.route('/cargando')
def cargando():
    """Display user's saved ads page"""
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Get saved ads with announcement details
    saved_ads = SavedAd.query.filter_by(user_id=user.id).order_by(SavedAd.saved_date.desc()).all()
    
    return render_template('cargando.html', user=user, saved_ads=saved_ads)

@app.route('/create-ad')
def create_ad():
    """Display the ad creation form"""
    # Check if user is authenticated
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('create_ad.html', 
                         STRIPE_PUBLISHABLE_KEY=STRIPE_PUBLISHABLE_KEY,
                         **_brand_ctx())

@app.route('/my-ads')
def my_ads():
    """Display user's created advertisements"""
    # Check if user is authenticated
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Get user's announcements with related data
    user_announcements = Announcement.query.filter_by(user_id=user.id)\
        .order_by(Announcement.published_at.desc()).all()
    
    # Calculate statistics
    total_ads = len(user_announcements)
    active_ads = len([ad for ad in user_announcements if getattr(ad, 'is_active', True)])
    total_views = sum([getattr(ad, 'views', 0) for ad in user_announcements])
    
    return render_template('my_ads.html', 
                         user=user,
                         announcements=user_announcements,
                         total_ads=total_ads,
                         active_ads=active_ads,
                         total_views=total_views)

@app.route('/api/create-ad', methods=['POST'])
def api_create_ad():
    """API endpoint to create a new advertisement"""
    try:
        from datetime import datetime
        import uuid
        import os
        
        # Check if user is authenticated
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Usuario no autenticado'})
        
        # Check ad limits
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'})
        
        pricing_plan = PricingPlan.query.filter_by(is_active=True).first()
        if not pricing_plan:
            # Create default pricing plan if none exists
            pricing_plan = PricingPlan(
                name='Plan Estándar',
                description='Plan de precios estándar para anuncios premium',
                price_per_ad=5.0,
                max_free_ads=100000,  # High limit for app launch period
                is_active=True
            )
            db.session.add(pricing_plan)
            db.session.commit()
        else:
            # Update existing pricing plan to ensure max_free_ads is set to 100000 for launch
            if pricing_plan.max_free_ads < 100000:
                pricing_plan.max_free_ads = 100000
                db.session.commit()
        
        # Check if user can post free ads (handle None values)
        free_ads_used = user.free_ads_used or 0
        can_post_free = free_ads_used < pricing_plan.max_free_ads
        is_premium = user.is_premium
        
        if not can_post_free and not is_premium:
            return jsonify({
                'success': False, 
                'message': f'Has alcanzado el límite de {pricing_plan.max_free_ads} anuncios gratuitos. Necesitas pagar €{pricing_plan.price_per_ad} para publicar más anuncios.',
                'requires_payment': True,
                'price': pricing_plan.price_per_ad
            })
        
        # Get form data
        title = request.form.get('title')
        price = float(request.form.get('price', 0))
        description = request.form.get('description')
        rooms = int(request.form.get('rooms', 0)) if request.form.get('rooms') else None
        bathrooms = int(request.form.get('bathrooms', 0)) if request.form.get('bathrooms') else None
        square_meters = float(request.form.get('square_meters', 0)) if request.form.get('square_meters') else None
        property_type = request.form.get('property_type')
        whatsapp_number = request.form.get('whatsapp_number')
        contact_name = request.form.get('contact_name')
        
        # Validate required fields
        if not title or not price or not description:
            return jsonify({'success': False, 'message': 'Título, precio y descripción son obligatorios'})
        
        # Get photos
        photos = request.files.getlist('photos')
        if len(photos) < 3:
            return jsonify({'success': False, 'message': 'Se requieren al menos 3 fotos'})
        
        # Get or create Valencia location
        location = Geoname.query.filter_by(name='Valencia').first()
        if not location:
            location = Geoname(
                name='Valencia',
                city='Valencia',
                state='Valencia',
                country='España',
                countryCode='ES',
                latitude=39.4699,
                longitude=-0.3763
            )
            db.session.add(location)
            db.session.commit()
        
        # Update user's free ads counter if not premium
        if not is_premium:
            user.free_ads_used = (user.free_ads_used or 0) + 1
        
        # Create announcement
        announcement = Announcement(
            title=title,
            price=price,
            description=description,
            rooms=rooms,
            number_of_bathrooms=bathrooms,
            square_meters=square_meters,
            property_type=property_type,
            published_date=datetime.utcnow(),
            sector_id=location.id,  # sector_id is actually location_id in this model
            user_id=user_id,  # Associate with the logged-in user
            has_parking=bool(request.form.get('has_parking')),
            has_elevator=bool(request.form.get('has_elevator')),
            has_terrace=bool(request.form.get('has_terrace')),
            has_garden=bool(request.form.get('has_garden')),
            has_pool=bool(request.form.get('has_pool')),
            has_storage_room=bool(request.form.get('has_storage_room')),
            is_exterior=bool(request.form.get('is_exterior')),
            is_accessible=bool(request.form.get('is_accessible'))
        )
        
        db.session.add(announcement)
        db.session.flush()  # Get the ID
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(app.static_folder, 'uploads', 'announcements')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save photos
        for i, photo in enumerate(photos):
            if photo and photo.filename:
                # Generate unique filename
                filename = f"{announcement.id}_{i}_{uuid.uuid4().hex[:8]}.jpg"
                filepath = os.path.join(upload_dir, filename)
                photo.save(filepath)
                
                # Create database record
                image = AnnouncementImage(
                    announcement_id=announcement.id,
                    image_url=f"uploads/announcements/{filename}",
                    order=i
                )
                db.session.add(image)
        
        # Add WhatsApp contact info to description if provided
        if whatsapp_number or contact_name:
            contact_info = []
            if contact_name:
                contact_info.append(f"Contacto: {contact_name}")
            if whatsapp_number:
                whatsapp_link = f"https://wa.me/{whatsapp_number.replace('+', '').replace(' ', '')}"
                contact_info.append(f"WhatsApp: {whatsapp_number}")
            
            if contact_info:
                announcement.description += f"\n\n{' | '.join(contact_info)}"
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Anuncio creado exitosamente',
            'announcement_id': announcement.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating ad: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'})

# Save Ads API Endpoints
@app.route('/api/save-ad', methods=['POST'])
def save_ad():
    """Save an ad to user's favorites"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión para guardar anuncios'}), 401
        
        data = request.get_json()
        announcement_id = data.get('announcement_id')
        notes = data.get('notes', '')
        
        if not announcement_id:
            return jsonify({'success': False, 'message': 'ID de anuncio requerido'}), 400
        
        # Check if ad exists
        announcement = Announcement.query.get(announcement_id)
        if not announcement:
            return jsonify({'success': False, 'message': 'Anuncio no encontrado'}), 404
        
        # Check if already saved
        existing_save = SavedAd.query.filter_by(
            user_id=session['user_id'], 
            announcement_id=announcement_id
        ).first()
        
        if existing_save:
            return jsonify({'success': False, 'message': 'Este anuncio ya está guardado'}), 400
        
        # Create new saved ad
        saved_ad = SavedAd(
            user_id=session['user_id'],
            announcement_id=announcement_id,
            notes=notes
        )
        
        db.session.add(saved_ad)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Anuncio guardado exitosamente',
            'saved_ad_id': saved_ad.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving ad: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/api/unsave-ad', methods=['POST'])
def unsave_ad():
    """Remove an ad from user's favorites"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión'}), 401
        
        data = request.get_json()
        announcement_id = data.get('announcement_id')
        
        if not announcement_id:
            return jsonify({'success': False, 'message': 'ID de anuncio requerido'}), 400
        
        # Find and delete saved ad
        saved_ad = SavedAd.query.filter_by(
            user_id=session['user_id'], 
            announcement_id=announcement_id
        ).first()
        
        if not saved_ad:
            return jsonify({'success': False, 'message': 'Anuncio no encontrado en guardados'}), 404
        
        db.session.delete(saved_ad)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Anuncio eliminado de guardados'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error unsaving ad: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/api/check-saved-ads', methods=['POST'])
def check_saved_ads():
    """Check which ads are saved by the current user"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': True, 'saved_ads': []})
        
        data = request.get_json()
        announcement_ids = data.get('announcement_ids', [])
        
        if not announcement_ids:
            return jsonify({'success': True, 'saved_ads': []})
        
        saved_ads = SavedAd.query.filter(
            SavedAd.user_id == session['user_id'],
            SavedAd.announcement_id.in_(announcement_ids)
        ).all()
        
        saved_ids = [saved.announcement_id for saved in saved_ads]
        
        return jsonify({
            'success': True, 
            'saved_ads': saved_ids
        })
        
    except Exception as e:
        print(f"Error checking saved ads: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

# Save Searches API Endpoints
@app.route('/api/save-search', methods=['POST'])
def save_search():
    """Save a search with its criteria"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión para guardar búsquedas'}), 401
        
        data = request.get_json()
        search_name = data.get('search_name')
        search_criteria = data.get('search_criteria', {})
        
        if not search_name:
            return jsonify({'success': False, 'message': 'Nombre de búsqueda requerido'}), 400
        
        # Check if search name already exists for this user
        existing_search = SavedSearch.query.filter_by(
            user_id=session['user_id'],
            search_name=search_name
        ).first()
        
        if existing_search:
            # Update the existing search instead of creating a new one
            existing_search.search_text = search_criteria.get('search_text')
            existing_search.location = search_criteria.get('location')
            # Store location_id in features if provided
            features = search_criteria.get('features', {})
            if search_criteria.get('location_id'):
                features['location_id'] = search_criteria.get('location_id')
            
            # Store vehicle-specific filters in features if present
            if search_criteria.get('category'):
                features['category'] = search_criteria.get('category')
            if search_criteria.get('make_id'):
                features['make_id'] = int(search_criteria.get('make_id')) if search_criteria.get('make_id') else None
            if search_criteria.get('model_id'):
                features['model_id'] = int(search_criteria.get('model_id')) if search_criteria.get('model_id') else None
            if search_criteria.get('min_year'):
                features['min_year'] = int(search_criteria.get('min_year')) if search_criteria.get('min_year') else None
            if search_criteria.get('max_year'):
                features['max_year'] = int(search_criteria.get('max_year')) if search_criteria.get('max_year') else None
            if search_criteria.get('fuel_type'):
                features['fuel_type'] = search_criteria.get('fuel_type')
            if search_criteria.get('transmission'):
                features['transmission'] = search_criteria.get('transmission')
            if search_criteria.get('max_mileage'):
                features['max_mileage'] = int(search_criteria.get('max_mileage')) if search_criteria.get('max_mileage') else None
            if search_criteria.get('seller_type'):
                features['seller_type'] = search_criteria.get('seller_type')
            if search_criteria.get('condition'):
                features['condition'] = search_criteria.get('condition')
            if search_criteria.get('color'):
                features['color'] = search_criteria.get('color')
            
            existing_search.min_price = float(search_criteria.get('min_price')) if search_criteria.get('min_price') else None
            existing_search.max_price = float(search_criteria.get('max_price')) if search_criteria.get('max_price') else None
            existing_search.property_type = search_criteria.get('property_type')
            existing_search.min_rooms = int(search_criteria.get('min_rooms')) if search_criteria.get('min_rooms') else None
            existing_search.min_bathrooms = int(search_criteria.get('min_bathrooms')) if search_criteria.get('min_bathrooms') else None
            existing_search.features = features
            existing_search.last_used_date = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Búsqueda actualizada exitosamente',
                'saved_search_id': existing_search.id
            })
        
        # Store location_id in features if provided
        features = search_criteria.get('features', {})
        if search_criteria.get('location_id'):
            features['location_id'] = search_criteria.get('location_id')
        
        # Store vehicle-specific filters in features if present
        if search_criteria.get('category'):
            features['category'] = search_criteria.get('category')
        if search_criteria.get('make_id'):
            features['make_id'] = int(search_criteria.get('make_id')) if search_criteria.get('make_id') else None
        if search_criteria.get('model_id'):
            features['model_id'] = int(search_criteria.get('model_id')) if search_criteria.get('model_id') else None
        if search_criteria.get('min_year'):
            features['min_year'] = int(search_criteria.get('min_year')) if search_criteria.get('min_year') else None
        if search_criteria.get('max_year'):
            features['max_year'] = int(search_criteria.get('max_year')) if search_criteria.get('max_year') else None
        if search_criteria.get('fuel_type'):
            features['fuel_type'] = search_criteria.get('fuel_type')
        if search_criteria.get('transmission'):
            features['transmission'] = search_criteria.get('transmission')
        if search_criteria.get('max_mileage'):
            features['max_mileage'] = int(search_criteria.get('max_mileage')) if search_criteria.get('max_mileage') else None
        if search_criteria.get('seller_type'):
            features['seller_type'] = search_criteria.get('seller_type')
        if search_criteria.get('condition'):
            features['condition'] = search_criteria.get('condition')
        if search_criteria.get('color'):
            features['color'] = search_criteria.get('color')
        
        # Create new saved search
        saved_search = SavedSearch(
            user_id=session['user_id'],
            search_name=search_name,
            search_text=search_criteria.get('search_text'),
            location=search_criteria.get('location'),
            min_price=float(search_criteria.get('min_price')) if search_criteria.get('min_price') else None,
            max_price=float(search_criteria.get('max_price')) if search_criteria.get('max_price') else None,
            property_type=search_criteria.get('property_type'),
            min_rooms=int(search_criteria.get('min_rooms')) if search_criteria.get('min_rooms') else None,
            min_bathrooms=int(search_criteria.get('min_bathrooms')) if search_criteria.get('min_bathrooms') else None,
            features=features
        )
        
        db.session.add(saved_search)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Búsqueda guardada exitosamente',
            'saved_search_id': saved_search.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving search: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/api/get-saved-searches', methods=['GET'])
def get_saved_searches():
    """Get all saved searches for the current user"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión'}), 401
        
        saved_searches = SavedSearch.query.filter_by(
            user_id=session['user_id']
        ).order_by(SavedSearch.created_date.desc()).all()
        
        searches_data = []
        for search in saved_searches:
            searches_data.append({
                'id': search.id,
                'search_name': search.search_name,
                'search_text': search.search_text,
                'location': search.location,
                'min_price': search.min_price,
                'max_price': search.max_price,
                'property_type': search.property_type,
                'min_rooms': search.min_rooms,
                'min_bathrooms': search.min_bathrooms,
                'features': search.features,
                'created_date': search.created_date.isoformat(),
                'last_used_date': search.last_used_date.isoformat() if search.last_used_date else None
            })
        
        return jsonify({
            'success': True, 
            'saved_searches': searches_data
        })
        
    except Exception as e:
        print(f"Error getting saved searches: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/api/get-saved-search/<int:search_id>', methods=['GET'])
def get_saved_search(search_id):
    """Get a single saved search by ID"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión'}), 401
        
        saved_search = SavedSearch.query.filter_by(
            id=search_id,
            user_id=session['user_id']
        ).first()
        
        if not saved_search:
            return jsonify({'success': False, 'message': 'Búsqueda no encontrada'}), 404
        
        # Update last_used_date
        saved_search.last_used_date = datetime.utcnow()
        db.session.commit()
        
        search_data = {
            'id': saved_search.id,
            'search_name': saved_search.search_name,
            'search_text': saved_search.search_text,
            'location': saved_search.location,
            'min_price': saved_search.min_price,
            'max_price': saved_search.max_price,
            'property_type': saved_search.property_type,
            'min_rooms': saved_search.min_rooms,
            'min_bathrooms': saved_search.min_bathrooms,
            'features': saved_search.features or {}
        }
        
        return jsonify({
            'success': True, 
            'search': search_data
        })
        
    except Exception as e:
        print(f"Error getting saved search: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/api/delete-saved-search', methods=['POST'])
def delete_saved_search():
    """Delete a saved search"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión'}), 401
        
        data = request.get_json()
        search_id = data.get('search_id')
        
        if not search_id:
            return jsonify({'success': False, 'message': 'ID de búsqueda requerido'}), 400
        
        saved_search = SavedSearch.query.filter_by(
            id=search_id,
            user_id=session['user_id']
        ).first()
        
        if not saved_search:
            return jsonify({'success': False, 'message': 'Búsqueda no encontrada'}), 404
        
        db.session.delete(saved_search)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Búsqueda eliminada exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting saved search: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

# Email Alert System
def check_and_send_email_alerts():
    """Check for new properties matching saved searches and send email alerts"""
    with app.app_context():
        try:
            print("Checking for email alerts...")
            
            # Get all users with email alerts enabled
            users_with_alerts = User.query.filter_by(email_alerts_enabled=True).all()
            
            for user in users_with_alerts:
                # Check if it's time to send alerts for this user
                if should_send_alert(user):
                    send_email_alerts_for_user(user)
                    
        except Exception as e:
            print(f"Error in email alert check: {e}")

def should_send_alert(user):
    """Check if it's time to send alerts for this user based on their frequency preference"""
    if not user.last_alert_sent:
        return True
    
    now = datetime.utcnow()
    time_since_last = now - user.last_alert_sent
    
    if user.email_frequency == 'immediate':
        return True  # For immediate alerts, we'll check every time
    elif user.email_frequency == 'daily':
        return time_since_last >= timedelta(days=1)
    elif user.email_frequency == 'weekly':
        return time_since_last >= timedelta(weeks=1)
    
    return False

def send_email_alerts_for_user(user):
    """Send email alerts for a specific user's saved searches (both real estate and vehicles)"""
    try:
        # Get user's saved searches
        saved_searches = SavedSearch.query.filter_by(user_id=user.id).all()
        
        if not saved_searches:
            return
        
        new_properties = []
        new_vehicles = []
        
        for search in saved_searches:
            # Check if this is a vehicle search or real estate search
            features = search.features or {}
            search_type = features.get('search_type', 'real_estate')
            
            if search_type == 'vehicle':
                # Find matching vehicles
                matching_vehicles = find_matching_vehicles(search, user.last_alert_sent)
                new_vehicles.extend(matching_vehicles)
            else:
                # Find matching properties (real estate)
                matching_properties = find_matching_properties(search, user.last_alert_sent)
                new_properties.extend(matching_properties)
        
        # Send separate emails for properties and vehicles
        if new_properties:
            send_property_alert_email(user, new_properties)
            print(f"Sent property alert email to {user.email} with {len(new_properties)} new properties")
        
        if new_vehicles:
            send_vehicle_alert_email(user, new_vehicles)
            print(f"Sent vehicle alert email to {user.email} with {len(new_vehicles)} new vehicles")
        
        if new_properties or new_vehicles:
            # Update last alert sent time
            user.last_alert_sent = datetime.utcnow()
            db.session.commit()
        
    except Exception as e:
        print(f"Error sending email alerts for user {user.id}: {e}")

def find_matching_vehicles(saved_search, since_date=None):
    """Find vehicles that match a saved search criteria"""
    try:
        from models import Vehicle, VehicleMake, VehicleModel, VehicleCategory
        
        # Start with base query
        query = Vehicle.query.options(
            joinedload(Vehicle.images),
            joinedload(Vehicle.make),
            joinedload(Vehicle.model),
            joinedload(Vehicle.location)
        )
        
        # Filter by date if provided
        if since_date:
            since_date_only = since_date.date() if hasattr(since_date, 'date') else since_date
            query = query.filter(Vehicle.published_date > since_date_only)
        
        # Get criteria from features (vehicle-specific filters are stored there)
        features = saved_search.features or {}
        
        # Apply location filter
        if features.get('location_id'):
            query = query.filter(Vehicle.location_id == features['location_id'])
        
        # Apply price filters
        if saved_search.min_price:
            query = query.filter(Vehicle.price >= saved_search.min_price)
        if saved_search.max_price:
            query = query.filter(Vehicle.price <= saved_search.max_price)
        
        # Apply vehicle-specific filters from features
        if features.get('category'):
            category = VehicleCategory.query.filter_by(slug=features['category']).first()
            if category:
                query = query.filter(Vehicle.category_id == category.id)
        
        if features.get('make_id'):
            query = query.filter(Vehicle.make_id == features['make_id'])
        if features.get('model_id'):
            query = query.filter(Vehicle.model_id == features['model_id'])
        if features.get('min_year'):
            query = query.filter(Vehicle.year >= features['min_year'])
        if features.get('max_year'):
            query = query.filter(Vehicle.year <= features['max_year'])
        if features.get('fuel_type'):
            query = query.filter(Vehicle.fuel_type == features['fuel_type'])
        if features.get('transmission'):
            query = query.filter(Vehicle.transmission == features['transmission'])
        if features.get('max_mileage'):
            query = query.filter(Vehicle.mileage <= features['max_mileage'])
        if features.get('seller_type'):
            query = query.filter(Vehicle.seller_type == features['seller_type'])
        if features.get('condition'):
            query = query.filter(Vehicle.condition == features['condition'])
        if features.get('color'):
            query = query.filter(Vehicle.color == features['color'])
        
        return query.limit(10).all()  # Limit to 10 vehicles per search
        
    except Exception as e:
        print(f"Error finding matching vehicles: {e}")
        return []

def find_matching_properties(saved_search, since_date=None):
    """Find properties that match a saved search criteria"""
    try:
        # Start with base query
        query = Announcement.query.options(
            joinedload(Announcement.images),
            joinedload(Announcement.location)
        )
        
        # Filter by date if provided
        if since_date:
            # Convert since_date to date for comparison
            since_date_only = since_date.date() if hasattr(since_date, 'date') else since_date
            query = query.filter(Announcement.published_date > since_date_only)
        
        # Apply search criteria
        criteria = {
            'search_text': saved_search.search_text,
            'location': saved_search.location,
            'min_price': saved_search.min_price,
            'max_price': saved_search.max_price,
            'property_type': saved_search.property_type,
            'min_rooms': saved_search.min_rooms,
            'min_bathrooms': saved_search.min_bathrooms,
            'features': saved_search.features or {}
        }
        
        # Apply location filter (by location_id if available, otherwise by location name)
        if criteria['features'].get('location_id'):
            location_id = criteria['features']['location_id']
            query = query.filter(Announcement.sector_id == location_id)
        elif criteria['location']:
            # Search by location name - join Geoname table
            query = query.join(Geoname, Announcement.sector_id == Geoname.id).filter(Geoname.name.ilike(f'%{criteria["location"]}%'))
        
        # Apply text search
        if criteria['search_text']:
            search_filter = db.or_(
                Announcement.title.ilike(f'%{criteria["search_text"]}%'),
                Announcement.description.ilike(f'%{criteria["search_text"]}%')
            )
            query = query.filter(search_filter)
        
        # Apply price filters
        if criteria['min_price']:
            query = query.filter(Announcement.price >= criteria['min_price'])
        if criteria['max_price']:
            query = query.filter(Announcement.price <= criteria['max_price'])
        
        # Apply property type filter
        if criteria['property_type']:
            query = query.filter(Announcement.property_type == criteria['property_type'])
        
        # Apply room filters
        if criteria['min_rooms']:
            query = query.filter(Announcement.rooms >= criteria['min_rooms'])
        if criteria['min_bathrooms']:
            query = query.filter(Announcement.number_of_bathrooms >= criteria['min_bathrooms'])
        
        # Apply feature filters (excluding location_id and search_type which are handled separately)
        if criteria['features']:
            for feature, value in criteria['features'].items():
                if feature not in ['location_id', 'search_type'] and value and hasattr(Announcement, feature):
                    query = query.filter(getattr(Announcement, feature) == True)
        
        return query.limit(10).all()  # Limit to 10 properties per search
        
    except Exception as e:
        print(f"Error finding matching properties: {e}")
        return []

def send_property_alert_email(user, properties):
    """Send email with new property alerts"""
    try:
        # Check if email is properly configured
        if not app.config.get('MAIL_USERNAME') or app.config.get('MAIL_USERNAME') == 'glopy.alerts@gmail.com':
            print(f"Email not configured - would send to {user.email}: {len(properties)} properties")
            return
        
        # Create email content
        subject = f"🔔 Nuevas propiedades que coinciden con tus búsquedas - {len(properties)} encontradas"
        
        # Create HTML email content
        html_content = create_property_alert_html(user, properties)
        
        # Send email using Flask-Mail
        msg = Message(
            subject=subject,
            recipients=[user.email],
            html=html_content,
            sender=app.config['MAIL_USERNAME']
        )
        
        # Ensure mail connection is established
        with mail.connect() as conn:
            conn.send(msg)
        print(f"Email sent to {user.email}")
        
    except Exception as e:
        print(f"Error sending email to {user.email}: {e}")

def create_property_alert_html(user, properties):
    """Create HTML content for property alert email"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Nuevas Propiedades - Glopy</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #4fc3f7; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .property {{ border: 1px solid #ddd; margin: 15px 0; border-radius: 8px; overflow: hidden; }}
            .property-image {{ width: 100%; height: 200px; object-fit: cover; }}
            .property-content {{ padding: 15px; }}
            .property-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
            .property-price {{ color: #28a745; font-size: 20px; font-weight: bold; margin-bottom: 10px; }}
            .property-details {{ color: #666; margin-bottom: 10px; }}
            .property-features {{ margin-top: 10px; }}
            .feature-tag {{ background: #e9ecef; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px; }}
            .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
            .btn {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔔 Nuevas Propiedades Encontradas</h1>
                <p>Hola {user.name or 'Usuario'}, hemos encontrado {len(properties)} propiedades que coinciden con tus búsquedas guardadas.</p>
            </div>
    """
    
    for prop in properties:
        # Get first image
        first_image = prop.images[0] if prop.images else None
        image_url = first_image.image_url if first_image else None
        
        # Build features list
        features = []
        if prop.has_parking: features.append("Parking")
        if prop.has_elevator: features.append("Ascensor")
        if prop.has_terrace: features.append("Terraza")
        if prop.has_garden: features.append("Jardín")
        if prop.has_pool: features.append("Piscina")
        
        html += f"""
            <div class="property">
                <img src="{image_url or 'https://via.placeholder.com/400x200?text=Sin+Imagen'}" alt="{prop.title}" class="property-image">
                <div class="property-content">
                    <div class="property-title">{prop.title}</div>
                    <div class="property-price">{'{:,.0f}'.format(prop.price).replace(',', '.')} €</div>
                    <div class="property-details">
                        {prop.location.name if prop.location else 'Ubicación no especificada'}<br>
                        {f"{prop.rooms} hab." if prop.rooms else ""} 
                        {f"• {prop.number_of_bathrooms} baños" if prop.number_of_bathrooms else ""} 
                        {f"• {prop.square_meters} m²" if prop.square_meters else ""}
                    </div>
                    <div class="property-features">
                        {''.join([f'<span class="feature-tag">{feature}</span>' for feature in features])}
                    </div>
                </div>
            </div>
        """
    
    html += f"""
            <div class="footer">
                <p>¿Te interesa alguna de estas propiedades?</p>
                <a href="http://127.0.0.1:5001/inmobiliaria" class="btn">Ver Todas las Propiedades</a>
                <p style="margin-top: 20px; font-size: 12px; color: #666;">
                    Puedes gestionar tus alertas de email en tu <a href="http://127.0.0.1:5001/profile">perfil</a>.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def send_vehicle_alert_email(user, vehicles):
    """Send email with new vehicle alerts"""
    try:
        # Check if email is properly configured
        if not app.config.get('MAIL_USERNAME') or app.config.get('MAIL_USERNAME') == 'glopy.alerts@gmail.com':
            print(f"Email not configured - would send to {user.email}: {len(vehicles)} vehicles")
            return
        
        # Create email content
        subject = f"🚗 Nuevos vehículos que coinciden con tus búsquedas - {len(vehicles)} encontrados"
        
        # Create HTML email content
        html_content = create_vehicle_alert_html(user, vehicles)
        
        # Send email using Flask-Mail
        msg = Message(
            subject=subject,
            recipients=[user.email],
            html=html_content,
            sender=app.config['MAIL_USERNAME']
        )
        
        # Ensure mail connection is established
        with mail.connect() as conn:
            conn.send(msg)
        print(f"Vehicle alert email sent to {user.email}")
        
    except Exception as e:
        print(f"Error sending vehicle alert email to {user.email}: {e}")

def create_vehicle_alert_html(user, vehicles):
    """Create HTML content for vehicle alert email"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Nuevos Vehículos - Glopy</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #0071c2; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .vehicle {{ border: 1px solid #ddd; margin: 15px 0; border-radius: 8px; overflow: hidden; }}
            .vehicle-image {{ width: 100%; height: 200px; object-fit: cover; }}
            .vehicle-content {{ padding: 15px; }}
            .vehicle-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
            .vehicle-price {{ color: #28a745; font-size: 20px; font-weight: bold; margin-bottom: 10px; }}
            .vehicle-details {{ color: #666; margin-bottom: 10px; }}
            .vehicle-specs {{ margin-top: 10px; }}
            .spec-tag {{ background: #e9ecef; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px; }}
            .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
            .btn {{ background: #0071c2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚗 Nuevos Vehículos Encontrados</h1>
                <p>Hola {user.name or 'Usuario'}, hemos encontrado {len(vehicles)} vehículos que coinciden con tus búsquedas guardadas.</p>
            </div>
    """
    
    for vehicle in vehicles:
        # Get first image
        first_image = vehicle.images[0] if vehicle.images else None
        image_url = first_image.image_url if first_image else None
        
        # Build specs list
        specs = []
        if vehicle.year: specs.append(f"{vehicle.year}")
        if vehicle.mileage: specs.append(f"{vehicle.mileage:,.0f} km".replace(',', '.'))
        if vehicle.fuel_type: specs.append(vehicle.fuel_type)
        if vehicle.transmission: specs.append(vehicle.transmission)
        
        make_name = vehicle.make.name if vehicle.make else ''
        model_name = vehicle.model.name if vehicle.model else ''
        full_title = f"{make_name} {model_name}".strip() if make_name or model_name else vehicle.title
        
        html += f"""
            <div class="vehicle">
                <img src="{image_url or 'https://via.placeholder.com/400x200?text=Sin+Imagen'}" alt="{full_title}" class="vehicle-image">
                <div class="vehicle-content">
                    <div class="vehicle-title">{full_title}</div>
                    <div class="vehicle-price">{'{:,.0f}'.format(vehicle.price).replace(',', '.')} €</div>
                    <div class="vehicle-details">
                        {vehicle.location.name if vehicle.location else 'Ubicación no especificada'}
                    </div>
                    <div class="vehicle-specs">
                        {''.join([f'<span class="spec-tag">{spec}</span>' for spec in specs])}
                    </div>
                </div>
            </div>
        """
    
    html += f"""
            <div class="footer">
                <p>¿Te interesa alguno de estos vehículos?</p>
                <a href="http://127.0.0.1:5001/autos" class="btn">Ver Todos los Vehículos</a>
                <p style="margin-top: 20px; font-size: 12px; color: #666;">
                    Puedes gestionar tus alertas de email en tu <a href="http://127.0.0.1:5001/profile">perfil</a>.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def start_email_alert_scheduler():
    """Start the background email alert scheduler"""
    def run_scheduler():
        while True:
            try:
                check_and_send_email_alerts()
                time.sleep(3600)  # Check every hour
            except Exception as e:
                print(f"Error in email alert scheduler: {e}")
                time.sleep(3600)
    
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Email alert scheduler started")

# User Profile Routes
@app.route('/profile')
def profile():
    """User profile page with saved ads and searches"""
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Get saved ads
    saved_ads = SavedAd.query.filter_by(user_id=user.id).order_by(SavedAd.saved_date.desc()).all()
    
    # Get saved searches
    saved_searches = SavedSearch.query.filter_by(user_id=user.id).order_by(SavedSearch.created_date.desc()).all()
    
    return render_template('profile.html', 
                         user=user, 
                         saved_ads=saved_ads, 
                         saved_searches=saved_searches)

# Email Alert API Endpoints
@app.route('/api/email-alert-settings', methods=['GET'])
def get_email_alert_settings():
    """Get user's email alert settings"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        return jsonify({
            'success': True,
            'settings': {
                'email_alerts_enabled': user.email_alerts_enabled,
                'email_frequency': user.email_frequency,
                'last_alert_sent': user.last_alert_sent.isoformat() if user.last_alert_sent else None
            }
        })
        
    except Exception as e:
        print(f"Error getting email alert settings: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/api/email-alert-settings', methods=['POST'])
def update_email_alert_settings():
    """Update user's email alert settings"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        data = request.get_json()
        email_alerts_enabled = data.get('email_alerts_enabled')
        email_frequency = data.get('email_frequency')
        
        if email_alerts_enabled is not None:
            user.email_alerts_enabled = email_alerts_enabled
        
        if email_frequency and email_frequency in ['immediate', 'daily', 'weekly']:
            user.email_frequency = email_frequency
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Configuración de alertas actualizada exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating email alert settings: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/api/test-email-alert', methods=['POST'])
def test_email_alert():
    """Send a test email alert to the current user"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        # Get some recent properties for testing
        recent_properties = Announcement.query.options(
            joinedload(Announcement.images),
            joinedload(Announcement.location)
        ).order_by(Announcement.published_date.desc()).limit(3).all()
        
        if recent_properties:
            try:
                send_property_alert_email(user, recent_properties)
                return jsonify({
                    'success': True,
                    'message': 'Email de prueba enviado exitosamente'
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error al enviar email: {str(e)}'
                })
        else:
            return jsonify({
                'success': False,
                'message': 'No hay propiedades disponibles para enviar'
            })
        
    except Exception as e:
        print(f"Error sending test email alert: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

# Map API Endpoints
@app.route('/api/property/<int:property_id>/coordinates', methods=['GET'])
def get_property_coordinates(property_id):
    """Get coordinates for a specific property"""
    try:
        property = Announcement.query.get(property_id)
        if not property:
            return jsonify({'success': False, 'message': 'Propiedad no encontrada'}), 404
        
        if not property.latitude or not property.longitude:
            return jsonify({'success': False, 'message': 'Coordenadas no disponibles'}), 404
        
        return jsonify({
            'success': True,
            'coordinates': {
                'latitude': property.latitude,
                'longitude': property.longitude,
                'title': property.title,
                'price': property.price,
                'address': property.location.name if property.location else 'Ubicación no especificada'
            }
        })
        
    except Exception as e:
        print(f"Error getting property coordinates: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/api/properties/coordinates', methods=['GET'])
def get_all_properties_coordinates():
    """Get coordinates for properties with valid coordinates, applying the same filters as the main search"""
    try:
        # Apply same filtering logic as inmobiliaria route
        # We'll filter by coordinates availability in Python after loading
        query = Announcement.query.options(
            joinedload(Announcement.location),
            joinedload(Announcement.images)
        )
        
        # Apply filters from request parameters (same as inmobiliaria route)
        location_id = request.args.get('location_id', type=int)
        if location_id:
            query = query.filter(Announcement.sector_id == location_id)
        
        cat_id = request.args.get('cat_id', type=int)
        if cat_id:
            query = query.filter(Announcement.category_id == cat_id)
        
        search_text = request.args.get('search_text', type=str)
        if search_text:
            search_filter = db.or_(
                Announcement.title.ilike(f'%{search_text}%'),
                Announcement.description.ilike(f'%{search_text}%')
            )
            query = query.filter(search_filter)
        
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        if min_price is not None:
            query = query.filter(Announcement.price >= min_price)
        if max_price is not None:
            query = query.filter(Announcement.price <= max_price)
        
        min_m2 = request.args.get('min_m2', type=float)
        max_m2 = request.args.get('max_m2', type=float)
        if min_m2 is not None:
            query = query.filter(Announcement.square_meters >= min_m2)
        if max_m2 is not None:
            query = query.filter(Announcement.square_meters <= max_m2)
        
        rooms = request.args.get('rooms', type=int)
        bathrooms = request.args.get('bathrooms', type=int)
        if rooms is not None:
            query = query.filter(Announcement.rooms >= rooms)
        if bathrooms is not None:
            query = query.filter(Announcement.number_of_bathrooms >= bathrooms)
        
        property_type = request.args.get('property_type', type=str)
        if property_type:
            query = query.filter(Announcement.property_type == property_type)
        
        # Apply checkbox filters
        if request.args.get('has_pool') == '1':
            query = query.filter(Announcement.has_pool.is_(True))
        if request.args.get('has_parking') == '1':
            query = query.filter(Announcement.has_parking.is_(True))
        if request.args.get('has_air_conditioning') == '1':
            query = query.filter(Announcement.has_air_conditioning.is_(True))
        if request.args.get('has_heating') == '1':
            query = query.filter(Announcement.has_heating.is_(True))
        if request.args.get('has_elevator') == '1':
            query = query.filter(Announcement.has_elevator.is_(True))
        if request.args.get('has_terrace') == '1':
            query = query.filter(Announcement.has_terrace.is_(True))
        if request.args.get('has_garden') == '1':
            query = query.filter(Announcement.has_garden.is_(True))
        
        properties = query.all()
        
        coordinates = []
        for prop in properties:
            # Get first image if available
            first_image = None
            if prop.images and len(prop.images) > 0:
                first_image = prop.images[0].image_url
                # Handle relative paths
                if first_image and not first_image.startswith('http'):
                    first_image = url_for('static', filename=first_image)
            
            # Use property coordinates, or fall back to location coordinates
            lat = prop.latitude
            lon = prop.longitude
            if not lat or not lon:
                # Fall back to location coordinates if property doesn't have them
                if prop.location:
                    lat = prop.location.latitude
                    lon = prop.location.longitude
            
            # Only include if we have valid coordinates
            if lat and lon:
                coordinates.append({
                    'id': prop.id,
                    'title': prop.title,
                    'price': prop.price,
                    'latitude': lat,
                    'longitude': lon,
                    'address': prop.location.name if prop.location else 'Ubicación no especificada',
                    'property_type': prop.property_type,
                    'rooms': prop.rooms,
                    'bathrooms': prop.number_of_bathrooms,
                    'square_meters': prop.square_meters,
                    'image_url': first_image
                })
        
        return jsonify({
            'success': True,
            'properties': coordinates,
            'count': len(coordinates)
        })
        
    except Exception as e:
        print(f"Error getting all properties coordinates: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

# Company Logo Upload API
@app.route('/api/upload-company-logo', methods=['POST'])
def upload_company_logo():
    """Upload company logo for existing users"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        if not user.is_company:
            return jsonify({'success': False, 'message': 'Solo las empresas pueden subir logos'}), 403
        
        if 'company_logo' not in request.files:
            return jsonify({'success': False, 'message': 'No se encontró el archivo'}), 400
        
        logo_file = request.files['company_logo']
        if logo_file.filename == '':
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'}), 400
        
        if logo_file:
            import os
            import secrets
            from werkzeug.utils import secure_filename
            
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join(app.static_folder, 'uploads', 'company_logos')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            filename = secure_filename(logo_file.filename)
            name, ext = os.path.splitext(filename)
            unique_filename = f"{name}_{secrets.token_hex(8)}{ext}"
            logo_path = os.path.join(upload_dir, unique_filename)
            
            # Save the file
            logo_file.save(logo_path)
            company_logo_path = f"uploads/company_logos/{unique_filename}"
            
            # Update user's company logo
            user.company_logo = company_logo_path
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Logo actualizado exitosamente',
                'logo_url': url_for('static', filename=company_logo_path)
            })
        
    except Exception as e:
        print(f"Error uploading company logo: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

# Glopy Assistant API Endpoints
@app.route('/api/glopy-assistant/chat', methods=['POST'])
def glopy_assistant_chat():
    """Chat with Glopy Assistant for property search"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión'}), 401
        
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'message': 'Mensaje requerido'}), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'success': False, 'message': 'Mensaje no puede estar vacío'}), 400
        
        # Get conversation history from request
        conversation_history = data.get('conversation_history', [])
        
        # Import and initialize Glopy Assistant
        from services.glopy_assistant import GlopyAssistant
        assistant = GlopyAssistant()
        
        # Process the message
        result = assistant.process_message(user_message, session['user_id'], conversation_history)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in Glopy Assistant chat: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/api/glopy-assistant/suggestions', methods=['GET'])
def glopy_assistant_suggestions():
    """Get suggested questions for Glopy Assistant"""
    try:
        from services.glopy_assistant import GlopyAssistant
        assistant = GlopyAssistant()
        
        suggestions = assistant.get_suggested_questions()
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        print(f"Error getting Glopy Assistant suggestions: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/api/glopy-assistant/properties/<int:property_id>', methods=['GET'])
def glopy_assistant_property_details(property_id):
    """Get detailed information about a specific property from Glopy Assistant"""
    try:
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión'}), 401
        
        # Get property details
        property_obj = Announcement.query.options(
            joinedload(Announcement.location),
            joinedload(Announcement.images)
        ).get(property_id)
        
        if not property_obj:
            return jsonify({'success': False, 'message': 'Propiedad no encontrada'}), 404
        
        # Format property data
        property_data = {
            'id': property_obj.id,
            'title': property_obj.title,
            'description': property_obj.description,
            'price': property_obj.price,
            'rooms': property_obj.rooms,
            'bathrooms': property_obj.number_of_bathrooms,
            'bedrooms': property_obj.number_of_bedrooms,
            'square_meters': property_obj.square_meters,
            'property_type': property_obj.property_type,
            'housing_subtype': property_obj.housing_subtype,
            'listing_type': property_obj.listing_type,
            'location': {
                'name': property_obj.location.name if property_obj.location else 'Ubicación no especificada',
                'latitude': property_obj.latitude,
                'longitude': property_obj.longitude
            },
            'features': {
                'has_parking': property_obj.has_parking,
                'has_pool': property_obj.has_pool,
                'has_garden': property_obj.has_garden,
                'has_terrace': property_obj.has_terrace,
                'has_elevator': property_obj.has_elevator,
                'has_air_conditioning': property_obj.has_air_conditioning,
                'has_heating': property_obj.has_heating,
                'is_exterior': property_obj.is_exterior,
                'pets_allowed': property_obj.pets_allowed,
                'is_accessible': property_obj.is_accessible
            },
            'images': [
                {
                    'url': img.image_url,
                    'order': img.order
                } for img in property_obj.images
            ] if property_obj.images else [],
            'extras': property_obj.extras,
            'luxury_features': property_obj.luxury_features,
            'published_date': property_obj.published_date.isoformat() if property_obj.published_date else None
        }
        
        return jsonify({
            'success': True,
            'property': property_data
        })
        
    except Exception as e:
        print(f"Error getting property details: {e}")
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

# Glopy Assistant Page
@app.route('/glopy-assistant')
def glopy_assistant():
    """Glopy Assistant chat interface"""
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    return render_template('glopy_assistant.html')

# Puedes añadir más rutas para otros sectores aquí

@app.errorhandler(500)
def internal_server_error(e):
    """Handle database connection errors and other server errors"""
    error_msg = str(e).lower()
    if 'mysql server has gone away' in error_msg or 'broken pipe' in error_msg or 'connection' in error_msg:
        # Try to reconnect the database
        try:
            db.engine.dispose()
            print("Database connection disposed, will reconnect on next request")
        except:
            pass
        return render_template('500.html', error="Database connection issue. Please try again."), 500
    return render_template('500.html', error=str(e)), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    # Start email alert scheduler
    start_email_alert_scheduler()
    app.run(debug=True, port=5001)
