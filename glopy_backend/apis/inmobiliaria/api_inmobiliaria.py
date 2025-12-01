# api_inmobiliaria.py

from flask import Blueprint, jsonify, request
from models import db, Announcement, Sector, RealEstateCategory, AnnouncementImage, Domain, Geoname2, Geoname
from datetime import datetime, date
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
api_inmobiliaria_bp = Blueprint('api_inmobiliaria_bp', __name__)
from sqlalchemy import or_
# Helper: obtener ID del sector 'Inmobiliaria'
def get_inmobiliaria_sector_id():
    sector_inmo = Sector.query.filter_by(name='Inmobiliaria').first()
    return sector_inmo.id if sector_inmo else None

# ------------------------------------------------------------------
# Funciones auxiliares para parsear datos con seguridad
# ------------------------------------------------------------------
def parse_bool(value):
    """
    Convierte un string a bool. Acepta "1", "true", "True", "yes", "si" => True
    Acepta "0", "false", "False", "no" => False
    Devuelve None si no es reconocible.
    """
    if value is None:
        return None
    value_lower = value.strip().lower()
    if value_lower in ["1", "true", "yes", "sí", "si"]:
        return True
    elif value_lower in ["0", "false", "no"]:
        return False
    return None

def parse_date(value):
    """
    Intenta parsear la fecha en formato 'YYYY-MM-DD'.
    Devuelve objeto date o None si falla.
    """
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None

# ==================================================================
#                  FUNCIONES AUXILIARES DE LOGICA
# ==================================================================

# def find_geoname_id(location_text):
#     """
#     Busca un texto de ubicacion en la tabla 'geoname2' de forma iterativa y devuelve el ID
#     del primer resultado probable que encuentre.
#     Devuelve None si no encuentra nada tras probar todas las partes.
#     """
#     if not location_text:
#         return None

#     # 1. Dividimos la dirección en partes limpias.
#     # Ej: "9911 Whitehurst Dr, Dallas, TX 75243" -> ["9911 Whitehurst Dr", "Dallas", "TX 75243"]
#     parts = [p.strip() for p in location_text.split(',') if p.strip()]

#     if not parts:
#         return None

#     # 2. Iteramos sobre cada parte de la dirección para buscar una coincidencia.
#     for search_term in parts:
#         print(f"Buscando en geoname2 el termino: '{search_term}'")

#         # Intentamos la búsqueda con el término actual
#         try:
#             # La consulta inteligente, ordenada por poblacion para obtener el mejor resultado
#             location = Geoname2.query.filter(
#                 Geoname2.name.ilike(f'{search_term}%')
#             ).order_by(
#                 Geoname2.population.desc()
#             ).first()

#             # 3. Si encontramos una coincidencia, ¡hemos terminado!
#             if location:
#                 print(f"Coincidencia encontrada para '{search_term}': {location.name} (ID: {location.id})")
#                 return location.id # Devolvemos el ID y salimos de la función.
#             else:
#                 # Si no encontramos nada, informamos y el bucle continuará con la siguiente parte.
#                 print(f"No se encontro coincidencia para '{search_term}'. Intentando con la siguiente parte...")
        
#         except Exception as e:
#             # Capturamos cualquier error inesperado en la consulta
#             print(f"Error durante la busqueda del termino '{search_term}': {e}")
#             # Continuamos con la siguiente parte por si el error fue puntual
#             continue
            
#     # 4. Si el bucle termina y no hemos encontrado nada, lo informamos.
#     print(f"Busqueda agotada. No se encontro ninguna coincidencia para la ubicacion: '{location_text}'")
#     return None

# ==================================================================
#                  FUNCIÓN DE LÓGICA (EL CEREBRO)
# ==================================================================
def get_or_create_domain_id(domain_name, image_url=None):
    """
    Busca un dominio por nombre. Si no existe, lo crea. Siempre devuelve el ID.
    Si existe y no tiene imagen, intenta actualizarla.
    Devuelve el ID del dominio encontrado o creado.
    """
    if not domain_name:
        return None

    normalized_domain = domain_name.strip().lower()
    
    # Buscamos el dominio
    domain = Domain.query.filter_by(domain=normalized_domain).first()

    if domain:
        # Si existe y podemos actualizar la imagen, lo hacemos.
        if image_url and not domain.image:
            print(f"Dominio '{normalized_domain}' encontrado. Actualizando imagen.")
            domain.image = image_url
            # El commit se hará en la transacción principal que llame a esta función.
        return domain.id
    else:
        # Si no existe, creamos una nueva instancia.
        print(f"Dominio '{normalized_domain}' no encontrado. Creando nueva instancia.")
        new_domain = Domain(domain=normalized_domain, image=image_url)
        db.session.add(new_domain)
        # Hacemos flush para obtener un ID provisional.
        db.session.flush()
        return new_domain.id

# ==================================================================
#                  ENDPOINT DE LA API (EL MENSAJERO)
# ==================================================================
@api_inmobiliaria_bp.route('/api/domains/get-or-create', methods=['POST'])
def get_or_create_domain_endpoint():
    """
    Endpoint para buscar o crear un dominio.
    Llama a la función de lógica y devuelve el resultado.
    """
    data = request.get_json()
    if not data or 'domain' not in data:
        return jsonify({"error": "Falta el campo 'domain'."}), 400

    try:
        # 1. Llama a la función de lógica
        domain_id = get_or_create_domain_id(data.get('domain'), data.get('image'))

        if domain_id:
            # 2. Como este endpoint es una operación única, hacemos commit aquí.
            db.session.commit()
            return jsonify({"id": domain_id}), 200
        else:
            # Si la función devolvió None (porque domain_name estaba vacío)
            return jsonify({"error": "El nombre del dominio no puede estar vacio."}), 400

    except IntegrityError:
        # Captura el error si dos peticiones crean lo mismo a la vez
        db.session.rollback()
        return jsonify({"error": "Error de concurrencia, el dominio acaba de ser creado."}), 409
    except Exception as e:
        db.session.rollback()
        print(f"Error en el endpoint get_or_create_domain: {e}")
        return jsonify({"error": "Error interno del servidor."}), 500

# ------------------------------------------------------------------
# 1) GET /api/inmuebles : Listar inmuebles (con TODOS los filtros)
# ------------------------------------------------------------------
@api_inmobiliaria_bp.route('/api/inmuebles', methods=['GET'])
def get_all_inmuebles():
    """
    Devuelve un JSON con todos los inmuebles del sector 'Inmobiliaria',
    permitiendo filtrar por *cualquier* campo definido en models.py (Announcement).

    Para filtrar, pasa parámetros en la query string, por ejemplo:
      /api/inmuebles?city=Madrid&has_pool=true&price_min=100000&price_max=300000
    """
    sector_id_inmo = get_inmobiliaria_sector_id()
    if not sector_id_inmo:
        return jsonify({"error": "No existe el sector 'Inmobiliaria' en la BD."}), 404

    # Empezamos filtrando sólo los del sector Inmobiliaria
    query = Announcement.query.filter_by(sector_id=sector_id_inmo)

    # -----------------------------
    # Filtros por rangos numéricos
    # -----------------------------
    price_min = request.args.get('price_min', type=float)
    price_max = request.args.get('price_max', type=float)
    if price_min is not None:
        query = query.filter(Announcement.price >= price_min)
    if price_max is not None:
        query = query.filter(Announcement.price <= price_max)

    sqm_min = request.args.get('square_meters_min', type=float)
    sqm_max = request.args.get('square_meters_max', type=float)
    if sqm_min is not None:
        query = query.filter(Announcement.square_meters >= sqm_min)
    if sqm_max is not None:
        query = query.filter(Announcement.square_meters <= sqm_max)

    rooms_min = request.args.get('rooms_min', type=int)
    rooms_max = request.args.get('rooms_max', type=int)
    if rooms_min is not None:
        query = query.filter(Announcement.rooms >= rooms_min)
    if rooms_max is not None:
        query = query.filter(Announcement.rooms <= rooms_max)

    # number_of_bedrooms
    bedrooms_min = request.args.get('bedrooms_min', type=int)
    bedrooms_max = request.args.get('bedrooms_max', type=int)
    if bedrooms_min is not None:
        query = query.filter(Announcement.number_of_bedrooms >= bedrooms_min)
    if bedrooms_max is not None:
        query = query.filter(Announcement.number_of_bedrooms <= bedrooms_max)

    # number_of_bathrooms
    bathrooms_min = request.args.get('bathrooms_min', type=int)
    bathrooms_max = request.args.get('bathrooms_max', type=int)
    if bathrooms_min is not None:
        query = query.filter(Announcement.number_of_bathrooms >= bathrooms_min)
    if bathrooms_max is not None:
        query = query.filter(Announcement.number_of_bathrooms <= bathrooms_max)

    # search_radius_km (si quisieras filtrar un rango)
    radius_min = request.args.get('search_radius_km_min', type=float)
    radius_max = request.args.get('search_radius_km_max', type=float)
    if radius_min is not None:
        query = query.filter(Announcement.search_radius_km >= radius_min)
    if radius_max is not None:
        query = query.filter(Announcement.search_radius_km <= radius_max)

    # capacity
    capacity_min = request.args.get('capacity_min', type=int)
    capacity_max = request.args.get('capacity_max', type=int)
    if capacity_min is not None:
        query = query.filter(Announcement.capacity >= capacity_min)
    if capacity_max is not None:
        query = query.filter(Announcement.capacity <= capacity_max)

    # relevancy
    relevancy_min = request.args.get('relevancy_min', type=int)
    relevancy_max = request.args.get('relevancy_max', type=int)
    if relevancy_min is not None:
        query = query.filter(Announcement.relevancy >= relevancy_min)
    if relevancy_max is not None:
        query = query.filter(Announcement.relevancy <= relevancy_max)

    # ----------------------------------------------------------------
    # Filtros por igualdad/substring en campos de tipo string (opcional)
    # ----------------------------------------------------------------
    def filter_eq_string(arg_name, column):
        val = request.args.get(arg_name)
        if val:
            nonlocal query
            query = query.filter(column == val)

    filter_eq_string('property_type', Announcement.property_type)
    filter_eq_string('province', Announcement.province)
    filter_eq_string('city', Announcement.city)
    filter_eq_string('postal_code', Announcement.postal_code)
    filter_eq_string('extras', Announcement.extras)
    filter_eq_string('property_state', Announcement.property_state)
    filter_eq_string('special_tags', Announcement.special_tags)
    filter_eq_string('published_at', Announcement.published_at)  # Ojo: string, no confundir con published_date
    filter_eq_string('rental_duration', Announcement.rental_duration)
    filter_eq_string('furnished', Announcement.furnished)
    filter_eq_string('luxury_features', Announcement.luxury_features)
    filter_eq_string('entity_type', Announcement.entity_type)
    filter_eq_string('auction_end_date', Announcement.auction_end_date)
    filter_eq_string('official_link', Announcement.official_link)
    filter_eq_string('land_use', Announcement.land_use)
    filter_eq_string('commercial_type', Announcement.commercial_type)
    filter_eq_string('vacation_duration', Announcement.vacation_duration)
    filter_eq_string('industrial_use', Announcement.industrial_use)
    filter_eq_string('property_main_type', Announcement.property_main_type)
    filter_eq_string('housing_subtype', Announcement.housing_subtype)
    filter_eq_string('listing_type', Announcement.listing_type)

    # ----------------------------------------------------------------
    # Filtros por booleans
    # ----------------------------------------------------------------
    def filter_bool(arg_name, column):
        raw_val = request.args.get(arg_name)
        if raw_val is not None:
            val_parsed = parse_bool(raw_val)
            if val_parsed is not None:
                nonlocal query
                query = query.filter(column == val_parsed)

    filter_bool('pets_allowed', Announcement.pets_allowed)
    filter_bool('has_balcony', Announcement.has_balcony)
    filter_bool('community_included', Announcement.community_included)
    filter_bool('has_street_access', Announcement.has_street_access)
    filter_bool('has_licence', Announcement.has_licence)
    filter_bool('is_conditioned', Announcement.is_conditioned)
    filter_bool('near_beach', Announcement.near_beach)
    filter_bool('has_air_conditioning', Announcement.has_air_conditioning)
    filter_bool('has_heating', Announcement.has_heating)
    filter_bool('has_fitted_wardrobes', Announcement.has_fitted_wardrobes)
    filter_bool('has_elevator', Announcement.has_elevator)
    filter_bool('has_terrace', Announcement.has_terrace)
    filter_bool('is_exterior', Announcement.is_exterior)
    filter_bool('has_parking', Announcement.has_parking)
    filter_bool('has_garden', Announcement.has_garden)
    filter_bool('has_pool', Announcement.has_pool)
    filter_bool('has_storage_room', Announcement.has_storage_room)
    filter_bool('is_accessible', Announcement.is_accessible)

    # ----------------------------------------------------------------
    # Filtro por rango de fechas en published_date (tipo Date)
    # ----------------------------------------------------------------
    published_date_from = request.args.get('published_date_from')
    published_date_to = request.args.get('published_date_to')

    date_from_obj = parse_date(published_date_from)
    date_to_obj = parse_date(published_date_to)

    if date_from_obj:
        query = query.filter(Announcement.published_date >= date_from_obj)
    if date_to_obj:
        query = query.filter(Announcement.published_date <= date_to_obj)

    # ----------------------------------------------------------------
    # Filtros por community_id, province_id, municipality_id (FKs)
    # ----------------------------------------------------------------
    community_id = request.args.get('community_id', type=int)
    if community_id is not None:
        query = query.filter(Announcement.community_id == community_id)

    province_id = request.args.get('province_id', type=int)
    if province_id is not None:
        query = query.filter(Announcement.province_id == province_id)

    municipality_id = request.args.get('municipality_id', type=int)
    if municipality_id is not None:
        query = query.filter(Announcement.municipality_id == municipality_id)

    # Finalmente, aplicamos ordenamiento por fecha de publicación (más recientes primero)
    # Si tienen la misma fecha, ordenamos por ID descendente (más recientes primero)
    query = query.order_by(Announcement.published_date.desc(), Announcement.id.desc())
    
    # Obtenemos resultados
    anuncios = query.all()

    # Convertimos a diccionarios
    results = []
    for a in anuncios:
        results.append({
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "price": a.price,
            "province": a.province,
            "city": a.city,
            "postal_code": a.postal_code,
            "search_radius_km": a.search_radius_km,
            "square_meters": a.square_meters,
            "rooms": a.rooms,
            "number_of_bedrooms": a.number_of_bedrooms,
            "number_of_bathrooms": a.number_of_bathrooms,
            "extras": a.extras,
            "property_state": a.property_state,
            "special_tags": a.special_tags,
            "published_at": a.published_at,
            "relevancy": a.relevancy,
            "rental_duration": a.rental_duration,
            "furnished": a.furnished,
            "pets_allowed": a.pets_allowed,
            "has_balcony": a.has_balcony,
            "community_included": a.community_included,
            "luxury_features": a.luxury_features,
            "entity_type": a.entity_type,
            "auction_end_date": a.auction_end_date,
            "official_link": a.official_link,
            "land_use": a.land_use,
            "commercial_type": a.commercial_type,
            "has_street_access": a.has_street_access,
            "has_licence": a.has_licence,
            "is_conditioned": a.is_conditioned,
            "vacation_duration": a.vacation_duration,
            "capacity": a.capacity,
            "near_beach": a.near_beach,
            "industrial_use": a.industrial_use,
            "property_type": a.property_type,
            "property_main_type": a.property_main_type,
            "housing_subtype": a.housing_subtype,
            "has_air_conditioning": a.has_air_conditioning,
            "has_heating": a.has_heating,
            "has_fitted_wardrobes": a.has_fitted_wardrobes,
            "has_elevator": a.has_elevator,
            "has_terrace": a.has_terrace,
            "is_exterior": a.is_exterior,
            "has_parking": a.has_parking,
            "has_garden": a.has_garden,
            "has_pool": a.has_pool,
            "has_storage_room": a.has_storage_room,
            "is_accessible": a.is_accessible,
            "listing_type": a.listing_type,
            "published_date": a.published_date.isoformat() if a.published_date else None,
            "sector_id": a.sector_id,
            "category_id": a.category_id,
            "community_id": a.community_id,
            "province_id": a.province_id,
            "municipality_id": a.municipality_id
        })

    return jsonify(results), 200

# ------------------------------------------------------------------
# 2) POST /api/inmuebles : Crear un inmueble (con TODOS los campos)
# ------------------------------------------------------------------
@api_inmobiliaria_bp.route('/api/inmuebles', methods=['POST'])
def create_inmueble():
    """
    Crea un nuevo anuncio.
    1. Recibe el JSON y extrae el objeto 'location_text' y el 'domain'.
    2. Crea un nuevo registro en la tabla 'geoname'.
    3. Busca o crea un registro en la tabla 'domain'.
    4. Crea el anuncio en 'announcements3', usando los IDs de geoname y domain.
    """
    import json
    data = request.get_json()
    if not data:
        return jsonify({"error": "Falta el cuerpo JSON con los datos."}), 400

    print("==========================================================")
    print("== JSON RECIBIDO EN /api/inmuebles ==")
    # print(json.dumps(data, indent=2, ensure_ascii=False))
    print("==========================================================")

    # --- Verificación de campos obligatorios ---
    if not data.get('title'):
        return jsonify({"error": "El campo 'title' es obligatorio."}), 400

    location_data = data.get('location_text')
    if not location_data or not isinstance(location_data, dict):
        return jsonify({"error": "El campo 'location_text' es obligatorio y debe ser un objeto."}), 400

    try:
        # --- 0. DUPLICATE DETECTION ---
        print("\n--- PASO 0: Verificando duplicados ---")
        from services.property_deduplicator import PropertyDeduplicator
        
        # Prepare property data for duplicate checking
        # Note: location_id will be added after location is created/get
        property_data = {
            'title': data.get('title'),
            'description': data.get('description'),
            'price': data.get('price'),
            'square_meters': data.get('square_meters'),
            'rooms': data.get('rooms'),
            'number_of_bathrooms': data.get('number_of_bathrooms'),
            'number_of_bedrooms': data.get('number_of_bedrooms'),
            'property_type': data.get('property_type'),
            'housing_subtype': data.get('housing_subtype'),
            'listing_type': data.get('listing_type'),
            'extras': data.get('extras'),
            'luxury_features': data.get('luxury_features'),
            'has_parking': data.get('has_parking'),
            'has_pool': data.get('has_pool'),
            'has_garden': data.get('has_garden'),
            'has_terrace': data.get('has_terrace'),
            'has_air_conditioning': data.get('has_air_conditioning'),
            'has_heating': data.get('has_heating'),
            'has_elevator': data.get('has_elevator'),
            'is_exterior': data.get('is_exterior'),
            'pets_allowed': data.get('pets_allowed'),
            'is_accessible': data.get('is_accessible'),
            'latitude': location_data.get('lat') if location_data else None,
            'longitude': location_data.get('lon') if location_data else None,
            'location_name': location_data.get('displayName') if location_data else None,
            'official_link': data.get('official_link')
        }
        
        # Try to get location_id early if location exists
        # This helps with candidate selection
        if location_data:
            location_name = location_data.get('displayName') or location_data.get('city')
            if location_name:
                existing_location = Geoname.query.filter_by(name=location_name).first()
                if existing_location:
                    property_data['location_id'] = existing_location.id
        
        # Check for duplicates
        deduplicator = PropertyDeduplicator()
        is_duplicate, duplicate_properties = deduplicator.check_for_duplicates(property_data)
        
        if is_duplicate:
            print(f"DUPLICATE DETECTED: Found {len(duplicate_properties)} similar properties")
            return jsonify({
                "error": "Property appears to be a duplicate",
                "duplicate_count": len(duplicate_properties),
                "similar_properties": [
                    {
                        "id": dup['property']['id'],
                        "title": dup['property']['title'],
                        "similarity_score": dup['similarity_score']
                    } for dup in duplicate_properties
                ]
            }), 409  # Conflict status code
        
        print("No duplicates found, proceeding with creation...")

        # --- 1. Crear la nueva entrada en la tabla Geoname ---
        print("\n--- PASO 1: Creando objeto Geoname ---")
        new_location = Geoname(
            name=location_data.get('displayName'),
            latitude=location_data.get('lat'),
            longitude=location_data.get('lon'),
            city=location_data.get('city'),
            state=location_data.get('state'),
            country=location_data.get('country'),
            countryCode=location_data.get('countryCode')
        )
        db.session.add(new_location)

        # --- 2. Buscar o Crear el Dominio ---
        print("\n--- PASO 2: Obteniendo ID del Dominio ---")
        # Usamos la función que ya tenías: get_or_create_domain_id
        # Esta función ya hace 'flush' si crea un dominio nuevo.
        domain_id = get_or_create_domain_id(data.get('domain'), data.get('image'))
        print(f"ID del Dominio encontrado/creado: {domain_id}")
        
        # Hacemos 'flush' para asignar el ID al nuevo Geoname.
        # Es seguro hacerlo aquí porque get_or_create_domain_id ya lo hace si es necesario,
        # y si no, no pasa nada por hacerlo de nuevo.
        db.session.flush()
        print(f"Flush realizado. ID asignado a Geoname: {new_location.id}")
        
        # --- 3. Validar category_id antes de crear el anuncio ---
        print("\n--- PASO 3: Validando category_id ---")
        category_id = data.get('category_id')
        if category_id is not None:
            # Verificar que el category_id existe en la base de datos
            category_exists = RealEstateCategory.query.filter_by(id=category_id).first()
            if not category_exists:
                print(f"[WARN] category_id {category_id} no existe en la base de datos. Usando None.")
                category_id = None
            else:
                print(f"[INFO] category_id {category_id} valido.")
        else:
            print("ℹ️ category_id es None (correcto, el campo es nullable).")

        # --- 4. Crear el objeto Announcement ---
        print("\n--- PASO 4: Creando objeto Announcement y enlazando IDs ---")
        new_inmueble = Announcement(
            # ¡Aquí está la conexión! Guardamos el ID de la ubicación en 'sector_id'
            sector_id=new_location.id,

            # Y aquí la conexión con el dominio. El campo 'image' ahora guarda el ID del dominio.
            # Nota: Si quieres que la columna 'image' guarde la URL de la imagen en lugar del ID,
            # tendrías que cambiar esto a `image=data.get('image')` y añadir una nueva columna
            # `domain_id` al modelo Announcement. Por ahora, lo mantenemos simple.
            image=str(domain_id) if domain_id is not None else None, # Guardamos el ID del dominio

            # IMPORTANT: Save coordinates directly to Announcement for map display
            latitude=location_data.get('lat') if location_data else None,
            longitude=location_data.get('lon') if location_data else None,

            # El resto de los campos, mapeados desde el JSON
            title=data.get('title'),
            description=data.get('description'),
            price=data.get('price'),
            category_id=category_id,
            auction_end_date=data.get('auction_end_date'),
            capacity=data.get('capacity'),
            commercial_type=data.get('commercial_type'),
            community_included=bool(data.get('community_included')),
            entity_type=data.get('entity_type'),
            extras=data.get('extras'),
            furnished=data.get('furnished'),
            has_air_conditioning=bool(data.get('has_air_conditioning')),
            has_balcony=bool(data.get('has_balcony')),
            has_elevator=bool(data.get('has_elevator')),
            has_fitted_wardrobes=bool(data.get('has_fitted_wardrobes')),
            has_garden=bool(data.get('has_garden')),
            has_heating=bool(data.get('has_heating')),
            has_licence=bool(data.get('has_licence')),
            has_parking=bool(data.get('has_parking')),
            has_pool=bool(data.get('has_pool')),
            has_storage_room=bool(data.get('has_storage_room')),
            has_street_access=bool(data.get('has_street_access')),
            has_terrace=bool(data.get('has_terrace')),
            housing_subtype=data.get('housing_subtype'),
            industrial_use=data.get('industrial_use'),
            is_accessible=bool(data.get('is_accessible')),
            is_conditioned=bool(data.get('is_conditioned')),
            is_exterior=bool(data.get('is_exterior')),
            land_use=data.get('land_use'),
            listing_type=data.get('listing_type'),
            luxury_features=data.get('luxury_features'),
            near_beach=bool(data.get('near_beach')),
            number_of_bathrooms=data.get('number_of_bathrooms'),
            number_of_bedrooms=data.get('number_of_bedrooms'),
            official_link=data.get('official_link'),
            pets_allowed=bool(data.get('pets_allowed')),
            property_main_type=data.get('property_main_type'),
            property_state=data.get('property_state'),
            property_type=data.get('property_type'),
            published_at=data.get('published_at'),
            published_date=parse_date(data.get('published_date')) or date.today(),
            relevancy=data.get('relevancy'),
            rental_duration=data.get('rental_duration'),
            rooms=data.get('rooms'),
            search_radius_km=data.get('search_radius_km'),
            special_tags=data.get('special_tags'),
            square_meters=data.get('square_meters'),
            vacation_duration=data.get('vacation_duration')
        )
        # print(f"Objeto 'Announcement' creado para '{new_inmueble.title}'")

        # --- 5. Procesamiento de Imágenes ---
        print("\n--- PASO 5: Procesando imagenes ---")
        images_list = data.get('images', [])
        if isinstance(images_list, list) and images_list:
            # Tracking URL patterns to filter out
            tracking_patterns = [
                'bat.bing.com',
                'doubleclick.net',
                'google-analytics.com',
                'googletagmanager.com',
                'facebook.com/tr',
                'analytics',
                'tracking',
                'pixel',
                'beacon',
                'gtm',
                'utm_',
                'ref=',
                'campaign=',
                'ad_id=',
                'click_id='
            ]
            
            def is_valid_image_url(url):
                """Validate if URL is a real image URL, not a tracking URL"""
                if not isinstance(url, str) or not url.startswith('http'):
                    return False
                
                url_lower = url.lower()
                
                # Check for obvious tracking URLs first (strict check)
                # These are definitive tracking services
                strict_tracking_domains = [
                    'bat.bing.com',
                    'doubleclick.net',
                    'googletagmanager.com',
                    'google-analytics.com',
                    'facebook.com/tr',
                    'analytics.google.com'
                ]
                
                for domain in strict_tracking_domains:
                    if domain in url_lower:
                        print(f"[WARN] Filtered out tracking URL: {url[:100]}...")
                        return False
                
                # Check for tracking patterns in query parameters (more lenient)
                # Only reject if it's clearly a tracking pixel/beacon
                if any(pattern in url_lower for pattern in ['/pixel', '/beacon', '/tracking', '/tr?id=']):
                    # But allow if it also has image indicators
                    if not any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', 'image', 'photo', 'img']):
                        print(f"[WARN] Filtered out tracking pixel: {url[:100]}...")
                        return False
                
                # Must be reasonable length (max 1000 chars)
                if len(url) > 1000:
                    print(f"[WARN] URL too long ({len(url)} chars), will be truncated")
                    # Don't reject, just truncate later
                
                # Common image extensions
                image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.avif']
                has_image_extension = any(url_lower.endswith(ext) or f'{ext}?' in url_lower or f'{ext}&' in url_lower or f'{ext}%' in url_lower for ext in image_extensions)
                
                # Common image-related keywords in URL path
                image_keywords = ['image', 'photo', 'img', 'picture', 'media', 'cdn', 'static', 'assets']
                has_image_keyword = any(keyword in url_lower for keyword in image_keywords)
                
                # Common real estate domains (trust these even without image extension)
                real_estate_domains = ['redfin.com', 'zillow.com', 'realtor.com', 'trulia.com', 'homes.com', 
                                      'apartments.com', 'rent.com', 'apartments.com', 'streeteasy.com']
                is_real_estate_site = any(domain in url_lower for domain in real_estate_domains)
                
                # Accept if:
                # 1. Has image extension OR
                # 2. Has image keywords AND length < 500 (reasonable URL) OR
                # 3. Is from known real estate site OR
                # 4. URL is short (< 300 chars) - likely valid
                is_valid = (has_image_extension or 
                           (has_image_keyword and len(url) < 500) or 
                           is_real_estate_site or 
                           len(url) < 300)
                
                if not is_valid:
                    print(f"[WARN] URL doesn't appear to be an image: {url[:100]}...")
                
                return is_valid
            
            def truncate_url(url, max_length=1000):
                """Truncate URL if too long"""
                if len(url) > max_length:
                    return url[:max_length]
                return url
            
            valid_images_count = 0
            for i, url in enumerate(images_list):
                if is_valid_image_url(url):
                    truncated_url = truncate_url(url, 1000)
                    new_inmueble.images.append(AnnouncementImage(image_url=truncated_url, order=valid_images_count))
                    valid_images_count += 1
                else:
                    print(f"[WARN] Skipping invalid image URL at index {i}")
            
            print(f"[INFO] Added {valid_images_count} valid images out of {len(images_list)} total URLs.")

        # --- 6. Guardado atómico en la Base de Datos ---
        db.session.add(new_inmueble)
        print("\n--- PASO 6: Ejecutando db.session.commit() ---")
        db.session.commit()
        print("--- COMMIT REALIZADO CON eXITO ---")

        # --- 7. Almacenar vector para futuras comparaciones ---
        print("\n--- PASO 7: Almacenando vector de la propiedad ---")
        try:
            # Add location_id to property_data for vector storage
            property_data['location_id'] = new_location.id
            property_data['id'] = new_inmueble.id
            
            # Store property vector
            deduplicator.store_property_vector(new_inmueble.id, property_data)
            print("Vector almacenado correctamente")
        except Exception as e:
            print(f"Error almacenando vector: {e}")
            # No fallar la creación por error en vector storage

        return jsonify({
            "message": "Anuncio, ubicación, dominio e imágenes creados con éxito.",
            "announcement_id": new_inmueble.id,
            "location_id": new_location.id,
            "domain_id": domain_id
        }), 201

    except Exception as e:
        db.session.rollback()
        import traceback
        print("\n--- !!! OCURRIo UN ERROR !!! ---")
        traceback.print_exc()
        print("--- ROLLBACK REALIZADO ---")
        return jsonify({"error": "Error interno al guardar el anuncio.", "details": str(e)}), 500
    

# ------------------------------------------------------------------
# 3) GET /api/inmuebles/<int:inmueble_id> : Obtener un inmueble concreto
# ------------------------------------------------------------------
@api_inmobiliaria_bp.route('/api/inmuebles/<int:inmueble_id>', methods=['GET'])
def get_inmueble(inmueble_id):
    anuncio = Announcement.query.get(inmueble_id)
    if not anuncio:
        return jsonify({"error": "Inmueble no encontrado."}), 404

    # Lo convertimos a dict (puedes extraer todos los campos si quieres)
    anuncio_dict = {
        "id": anuncio.id,
        "title": anuncio.title,
        "description": anuncio.description,
        "price": anuncio.price,
        "city": anuncio.city,
        "rooms": anuncio.rooms,
        "number_of_bathrooms": anuncio.number_of_bathrooms,
        "listing_type": anuncio.listing_type,
        "furnished": anuncio.furnished,
        "pets_allowed": anuncio.pets_allowed,
        "has_parking": anuncio.has_parking,
        "published_date": anuncio.published_date.isoformat() if anuncio.published_date else None,
        # ... añade el resto de campos si deseas
    }
    return jsonify(anuncio_dict), 200

# ------------------------------------------------------------------
# 4) GET /api/inmuebles/<int:inmueble_id>/duplicates : Obtener duplicados de un inmueble
# ------------------------------------------------------------------
@api_inmobiliaria_bp.route('/api/inmuebles/<int:inmueble_id>/duplicates', methods=['GET'])
def get_inmueble_duplicates(inmueble_id):
    """Obtiene todas las propiedades que son duplicados de la propiedad especificada."""
    try:
        from services.property_deduplicator import PropertyDeduplicator
        
        deduplicator = PropertyDeduplicator()
        duplicates = deduplicator.get_duplicate_properties(inmueble_id)
        
        return jsonify({
            "property_id": inmueble_id,
            "duplicate_count": len(duplicates),
            "duplicates": duplicates
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Error obteniendo duplicados: {str(e)}"}), 500

# ------------------------------------------------------------------
# 5) POST /api/inmuebles/check-duplicate : Verificar si una propiedad es duplicado
# ------------------------------------------------------------------
@api_inmobiliaria_bp.route('/api/inmuebles/check-duplicate', methods=['POST'])
def check_duplicate():
    """Verifica si una propiedad es duplicado sin almacenarla."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Falta el cuerpo JSON con los datos."}), 400
    
    try:
        from services.property_deduplicator import PropertyDeduplicator
        
        # Prepare property data
        property_data = {
            'title': data.get('title'),
            'description': data.get('description'),
            'price': data.get('price'),
            'square_meters': data.get('square_meters'),
            'rooms': data.get('rooms'),
            'number_of_bathrooms': data.get('number_of_bathrooms'),
            'number_of_bedrooms': data.get('number_of_bedrooms'),
            'property_type': data.get('property_type'),
            'housing_subtype': data.get('housing_subtype'),
            'listing_type': data.get('listing_type'),
            'extras': data.get('extras'),
            'luxury_features': data.get('luxury_features'),
            'has_parking': data.get('has_parking'),
            'has_pool': data.get('has_pool'),
            'has_garden': data.get('has_garden'),
            'has_terrace': data.get('has_terrace'),
            'has_air_conditioning': data.get('has_air_conditioning'),
            'has_heating': data.get('has_heating'),
            'has_elevator': data.get('has_elevator'),
            'is_exterior': data.get('is_exterior'),
            'pets_allowed': data.get('pets_allowed'),
            'is_accessible': data.get('is_accessible'),
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'location_name': data.get('location_name'),
            'official_link': data.get('official_link')
        }
        
        deduplicator = PropertyDeduplicator()
        is_duplicate, duplicates = deduplicator.check_for_duplicates(property_data)
        
        return jsonify({
            "is_duplicate": is_duplicate,
            "duplicate_count": len(duplicates),
            "similar_properties": duplicates
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Error verificando duplicados: {str(e)}"}), 500

# ------------------------------------------------------------------
# 6) PUT /api/inmuebles/<int:inmueble_id> : Actualizar un inmueble (TODOS los campos)
# ------------------------------------------------------------------
@api_inmobiliaria_bp.route('/api/inmuebles/<int:inmueble_id>', methods=['PUT'])
def update_inmueble(inmueble_id):
    anuncio = Announcement.query.get(inmueble_id)
    if not anuncio:
        return jsonify({"error": "Inmueble no encontrado."}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Falta el cuerpo JSON con los datos."}), 400

    # Actualizamos solo si vienen en el JSON
    if 'title' in data: anuncio.title = data['title']
    if 'description' in data: anuncio.description = data['description']
    if 'price' in data: anuncio.price = data['price']
    if 'image' in data: anuncio.image = data['image']
    if 'category_id' in data: anuncio.category_id = data['category_id']

    if 'property_type' in data: anuncio.property_type = data['property_type']
    if 'province' in data: anuncio.province = data['province']
    if 'city' in data: anuncio.city = data['city']
    if 'postal_code' in data: anuncio.postal_code = data['postal_code']
    if 'extras' in data: anuncio.extras = data['extras']
    if 'property_state' in data: anuncio.property_state = data['property_state']
    if 'special_tags' in data: anuncio.special_tags = data['special_tags']
    if 'published_at' in data: anuncio.published_at = data['published_at']
    if 'rental_duration' in data: anuncio.rental_duration = data['rental_duration']
    if 'furnished' in data: anuncio.furnished = data['furnished']
    if 'luxury_features' in data: anuncio.luxury_features = data['luxury_features']
    if 'entity_type' in data: anuncio.entity_type = data['entity_type']
    if 'auction_end_date' in data: anuncio.auction_end_date = data['auction_end_date']
    if 'official_link' in data: anuncio.official_link = data['official_link']
    if 'land_use' in data: anuncio.land_use = data['land_use']
    if 'commercial_type' in data: anuncio.commercial_type = data['commercial_type']
    if 'vacation_duration' in data: anuncio.vacation_duration = data['vacation_duration']
    if 'industrial_use' in data: anuncio.industrial_use = data['industrial_use']
    if 'property_main_type' in data: anuncio.property_main_type = data['property_main_type']
    if 'housing_subtype' in data: anuncio.housing_subtype = data['housing_subtype']
    if 'listing_type' in data: anuncio.listing_type = data['listing_type']

    if 'search_radius_km' in data: anuncio.search_radius_km = data['search_radius_km']
    if 'square_meters' in data: anuncio.square_meters = data['square_meters']
    if 'rooms' in data: anuncio.rooms = data['rooms']
    if 'relevancy' in data: anuncio.relevancy = data['relevancy']
    if 'capacity' in data: anuncio.capacity = data['capacity']
    if 'number_of_bedrooms' in data: anuncio.number_of_bedrooms = data['number_of_bedrooms']
    if 'number_of_bathrooms' in data: anuncio.number_of_bathrooms = data['number_of_bathrooms']

    # Booleans
    def update_bool(field_name):
        if field_name in data and isinstance(data[field_name], bool):
            setattr(anuncio, field_name, data[field_name])

    update_bool('pets_allowed')
    update_bool('has_balcony')
    update_bool('community_included')
    update_bool('has_street_access')
    update_bool('has_licence')
    update_bool('is_conditioned')
    update_bool('near_beach')
    update_bool('has_air_conditioning')
    update_bool('has_heating')
    update_bool('has_fitted_wardrobes')
    update_bool('has_elevator')
    update_bool('has_terrace')
    update_bool('is_exterior')
    update_bool('has_parking')
    update_bool('has_garden')
    update_bool('has_pool')
    update_bool('has_storage_room')
    update_bool('is_accessible')

    # published_date
    if 'published_date' in data:
        pd_str = data['published_date']
        if pd_str:
            try:
                anuncio.published_date = datetime.strptime(pd_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"error": "Formato de fecha inválido en 'published_date' (YYYY-MM-DD)"}), 400
        else:
            anuncio.published_date = None

    # FK IDs
    if 'community_id' in data: anuncio.community_id = data['community_id']
    if 'province_id' in data: anuncio.province_id = data['province_id']
    if 'municipality_id' in data: anuncio.municipality_id = data['municipality_id']

    db.session.commit()

    return jsonify({
        "id": anuncio.id,
        "title": anuncio.title,
        "message": "Inmueble actualizado correctamente."
    }), 200

# ------------------------------------------------------------------
# 5) DELETE /api/inmuebles/<int:inmueble_id> : Borrar un inmueble
# ------------------------------------------------------------------
@api_inmobiliaria_bp.route('/api/inmuebles/<int:inmueble_id>', methods=['DELETE'])
def delete_inmueble(inmueble_id):
    anuncio = Announcement.query.get(inmueble_id)
    if not anuncio:
        return jsonify({"error": "Inmueble no encontrado."}), 404

    db.session.delete(anuncio)
    db.session.commit()

    return jsonify({
        "message": f"Inmueble con id {inmueble_id} eliminado correctamente."
    }), 200

# ------------------------------------------------------------------
# NUEVO: Endpoint para añadir varias imágenes (URLs) a un inmueble
# ------------------------------------------------------------------
@api_inmobiliaria_bp.route('/api/inmuebles/<int:inmueble_id>/images', methods=['POST'])
def add_images_to_inmueble(inmueble_id):
    """
    Permite añadir múltiples URLs de imágenes (AnnouncementImage)
    para un inmueble específico.

    Se espera un JSON con el campo "images", que contenga una lista de URLs.

    Ejemplo de JSON:
    {
      "images": [
        "https://ruta/de/imagen1.jpg",
        "https://ruta/de/imagen2.jpg"
      ]
    }
    """
    anuncio = Announcement.query.get(inmueble_id)
    if not anuncio:
        return jsonify({"error": "Inmueble no encontrado."}), 404

    data = request.get_json()
    if not data or 'images' not in data:
        return jsonify({"error": "Falta el campo 'images' (lista de URLs)."}), 400

    images_list = data['images']
    if not isinstance(images_list, list):
        return jsonify({"error": "El campo 'images' debe ser una lista de URLs."}), 400

    # Insertar cada URL en la tabla 'announcement_images'
    for i, url in enumerate(images_list):
        new_image = AnnouncementImage(
            announcement_id = anuncio.id,
            image_url = url,
            order = i  # Puedes ajustar el orden como prefieras
        )
        db.session.add(new_image)

    db.session.commit()

    return jsonify({
        "message": f"Se han añadido {len(images_list)} imágenes al inmueble {inmueble_id}.",
        "inmueble_id": anuncio.id,
        "images_added": images_list
    }), 201


# ------------------------------------------------------------------
# GET /api/domains : Listar todos los dominios
# ------------------------------------------------------------------
@api_inmobiliaria_bp.route('/api/domains', methods=['GET'])
def get_all_domains():
    """
    Devuelve un JSON con todos los registros de la tabla 'domain'.
    """
    try:
        all_domains = Domain.query.all()
        
        # Convertimos los objetos Domain a una lista de diccionarios
        results = [
            {
                "id": domain.id,
                "domain": domain.domain,
                "image": domain.image
            }
            for domain in all_domains
        ]
        
        return jsonify(results), 200
        
    except Exception as e:
        # Manejo de errores genérico por si la tabla no existe o hay otro problema
        print(f"Error al obtener dominios: {e}")
        return jsonify({"error": "No se pudieron obtener los dominios."}), 500

# ------------------------------------------------------------------
# POST /api/domains : Crear un nuevo dominio
# ------------------------------------------------------------------
@api_inmobiliaria_bp.route('/api/domains', methods=['POST'])
def create_domain():
    """
    Crea un nuevo registro en la tabla 'domain'.
    Se espera un JSON con los campos "domain" (obligatorio) e "image" (opcional).
    
    Ejemplo de JSON:
    {
      "domain": "www.idealista.com",
      "image": "https://url.to/logo.png"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Falta el cuerpo JSON con los datos."}), 400

    # Verificamos que el campo obligatorio 'domain' venga en el JSON
    domain_name = data.get('domain')
    if not domain_name:
        return jsonify({"error": "El campo 'domain' es obligatorio."}), 400
        
    # Creamos la nueva instancia del modelo Domain
    new_domain = Domain(
        domain=domain_name.strip(), # Usamos .strip() para quitar espacios al inicio/final
        image=data.get('image')      # El campo 'image' es opcional
    )
    
    try:
        # Añadimos a la sesión y guardamos en la base de datos
        db.session.add(new_domain)
        db.session.commit()
        
        # Devolvemos una respuesta de éxito con los datos creados
        return jsonify({
            "message": "Dominio creado con éxito.",
            "id": new_domain.id,
            "domain": new_domain.domain,
            "image": new_domain.image
        }), 201 # 201 Created es el código de estado correcto para un POST exitoso

    except IntegrityError:
        # Este error ocurre si intentas insertar un dominio que ya existe (gracias a unique=True)
        db.session.rollback() # Deshacemos la transacción fallida
        return jsonify({"error": f"El dominio '{domain_name}' ya existe en la base de datos."}), 409 # 409 Conflict
        
    except Exception as e:
        # Manejo de otros posibles errores de base de datos
        db.session.rollback()
        print(f"Error al crear el dominio: {e}")
        return jsonify({"error": "Ocurrió un error al guardar en la base de datos."}), 500
    

# ==================================================================
#           NUEVO ENDPOINT: BUSCAR UBICACIÓN EN GEONAME2
# ==================================================================
@api_inmobiliaria_bp.route('/api/geoname2/find', methods=['POST'])
def find_geoname():
    """
    Busca una ubicación por un texto.
    Recibe un JSON con el campo "location_text".
    Devuelve el registro más probable de la tabla 'geoname2'.

    Ejemplo de JSON: {"location_text": "Madrid"}
    """
    data = request.get_json()
    if not data or 'location_text' not in data:
        return jsonify({"error": "Falta el campo 'location_text' en el cuerpo JSON."}), 400

    location_text = data.get('location_text').strip()

    if not location_text:
        return jsonify({"error": "El campo 'location_text' no puede estar vacío."}), 400

    # 1. Limpieza y preparación del término de búsqueda.
    #    Tomamos la parte más significativa antes de la primera coma.
    #    Ej: "Madrid, Comunidad de Madrid, España" -> "Madrid"
    search_term = location_text.split(',')[0].strip()

    # print(f"Buscando en geoname2 el termino: '{search_term}'")

    try:
        # 2. La consulta inteligente a la base de datos.
        #    - `Geoname2.name.ilike(f'{search_term}%')`: Busca coincidencias que EMPIECEN con el término
        #      (insensible a mayúsculas/minúsculas). Esto es más preciso que usar % al principio y al final.
        #    - `order_by(Geoname2.population.desc())`: Ordena por población descendente. Esto es CLAVE.
        #      Si hay varias ciudades con el mismo nombre, la más poblada suele ser la correcta.
        #    - `.first()`: Obtenemos solo el primer resultado, que es el más probable.
        
        location = Geoname2.query.filter(
            Geoname2.name.ilike(f'{search_term}%')
        ).order_by(
            Geoname2.population.desc()
        ).first()

        # 3. Devolvemos el resultado.
        if location:
            print(f"Coincidencia encontrada para '{search_term}': {location.name} (ID: {location.id})")
            # Devolvemos un objeto completo para que puedas usar más datos si lo necesitas.
            return jsonify({
                "status": "found",
                "id": location.id,
                "name": location.name,
                "country_code": location.country_code,
                "latitude": location.latitude,
                "longitude": location.longitude
            }), 200
        else:
            # Si no se encuentra nada, lo informamos.
            print(f"No se encontro coincidencia en geoname2 para '{search_term}'")
            return jsonify({
                "status": "not_found",
                "id": None
            }), 404 # 404 Not Found es el código apropiado aquí.

    except Exception as e:
        print(f"Error inesperado durante la busqueda en geoname2: {e}")
        return jsonify({"error": "Error interno del servidor al buscar la ubicación."}), 500
    

# ==================================================================
#           ENDPOINT GET SIMPLE PARA GEONAME2 (CON LÍMITE)
# ==================================================================
@api_inmobiliaria_bp.route('/api/geoname2', methods=['GET'])
def get_geonames_sample():
    """
    Devuelve una muestra de hasta 100 registros de la tabla 'geoname2'.
    """
    print("--- Entrando a /api/geoname2 ---") # Mensaje de depuración
    try:
        query = db.session.query(Geoname2)
        
        # Aplicamos el límite
        locations_sample = query.limit(100).all()
        
        print(f"Numero de resultados encontrados: {len(locations_sample)}") # ¡Depuración clave!

        if not locations_sample:
            print("La consulta a la BD no devolvio resultados, aunque la tabla existe.")

        # La serialización no cambia
        results = [
            {
                "id": loc.id,
                "name": loc.name,
                "ascii_name": loc.ascii_name,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "feature_class": loc.feature_class,
                "feature_code": loc.feature_code,
                "country_code": loc.country_code,
                "population": loc.population,
                "timezone": loc.timezone,
            }
            for loc in locations_sample
        ]
        
        print(f"Enviando {len(results)} resultados al cliente.")
        return jsonify(results), 200
        
    except Exception as e:
        print(f"ERROR GRAVE al obtener una muestra de geoname2: {e}")
        # Imprimimos el traceback completo para más detalles
        import traceback
        traceback.print_exc()
        return jsonify({"error": "No se pudieron obtener las ubicaciones."}), 500
    
@api_inmobiliaria_bp.route('/test-raw-sql', methods=['GET'])
def test_raw_sql():
    try:
        # 1. Creamos la consulta SQL cruda con un LÍMITE
        query = text("SELECT * FROM geoname2 LIMIT 100")

        # 2. Ejecutamos la consulta
        result_proxy = db.session.execute(query)

        # 3. Obtenemos todas las filas del resultado
        rows = result_proxy.fetchall()

        # 4. Convertimos las filas a una lista de diccionarios
        #    Esto es necesario porque el resultado de la base de datos no es
        #    directamente convertible a JSON.
        
        # Obtenemos los nombres de las columnas del resultado
        column_names = result_proxy.keys()

        # Creamos una lista de diccionarios, donde cada diccionario es una fila
        results_list = [dict(zip(column_names, row)) for row in rows]
        
        print(f"Prueba Raw SQL: Encontradas {len(results_list)} filas.")

        # 5. Devolvemos la lista como JSON
        return jsonify({
            "status": "success",
            "count": len(results_list),
            "data": results_list
        }), 200

    except Exception as e:
        # Imprimimos el error en la consola para depurar
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    

@api_inmobiliaria_bp.route('/api/ubicaciones/buscar', methods=['GET'])
def buscar_ubicaciones():
    query_text = request.args.get('q', '').strip()
    
    # Si no hay texto de búsqueda, devuelve 10 ubicaciones aleatorias
    if not query_text:
        # Para aleatorio en SQLite, se usa db.func.random()
        # Para otras bases de datos como PostgreSQL, sería RANDOM()
        ubicaciones = Geoname.query.order_by(db.func.random()).limit(10).all()
    else:
        # --- ¡AQUÍ ESTÁ LA NUEVA LÓGICA DE BÚSQUEDA! ---
        search_pattern = f'%{query_text}%' # El patrón para la búsqueda 'contiene'
        
        # Construimos una consulta que busca coincidencias en CUALQUIERA de las columnas deseadas
        # La función or_() de SQLAlchemy es perfecta para esto.
        # .ilike() hace la búsqueda insensible a mayúsculas/minúsculas.
        ubicaciones = Geoname.query.filter(
            or_(
                Geoname.name.ilike(search_pattern),
                Geoname.city.ilike(search_pattern),
                Geoname.state.ilike(search_pattern)
                # Puedes añadir más columnas aquí si lo deseas, por ejemplo:
                # Geoname.country.ilike(search_pattern)
            )
        ).limit(10).all()

    # Formatea los resultados para que el frontend los entienda (sin cambios aquí)
    results = [
        {'id': u.id, 'name': u.name} for u in ubicaciones
    ]
    return jsonify(results), 200