# api_vehicles.py

from flask import Blueprint, jsonify, request
from models import db, Vehicle, VehicleCategory, VehicleMake, VehicleModel, VehicleImage, Geoname, Domain
from datetime import datetime, date
from sqlalchemy.exc import IntegrityError
from services.vehicle_deduplicator import VehicleDeduplicator
import sys
import io

# Ensure stdout/stderr can handle UTF-8 characters to avoid UnicodeEncodeError on prints
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

api_vehicles_bp = Blueprint('api_vehicles_bp', __name__)

# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------
def parse_int(value):
    """Safely parse integer values"""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def parse_float(value):
    """Safely parse float values"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def parse_bool(value):
    """Convert string to bool"""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    value_lower = str(value).strip().lower()
    if value_lower in ["1", "true", "yes", "sí", "si"]:
        return True
    elif value_lower in ["0", "false", "no"]:
        return False
    return None

def get_or_create_location(location_data):
    """Create a new Geoname record for the vehicle location"""
    if not location_data or not isinstance(location_data, dict):
        return None
    
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
    db.session.flush()  # Get the ID
    return new_location.id

def get_or_create_domain(domain_name, image_url=None):
    """Get or create domain record"""
    if not domain_name:
        return None
    
    normalized_domain = domain_name.strip().lower()
    domain = Domain.query.filter_by(domain=normalized_domain).first()
    
    if domain:
        if image_url and not domain.image:
            domain.image = image_url
        return domain.id
    else:
        new_domain = Domain(domain=normalized_domain, image=image_url)
        db.session.add(new_domain)
        db.session.flush()
        return new_domain.id

def get_or_create_make(make_name):
    """Get or create vehicle make"""
    if not make_name:
        return None
    
    # Normalize name
    normalized_name = make_name.strip().title()
    make = VehicleMake.query.filter_by(name=normalized_name).first()
    
    if make:
        return make.id
    else:
        # Create slug from name
        slug = normalized_name.lower().replace(' ', '-')
        new_make = VehicleMake(name=normalized_name, slug=slug)
        db.session.add(new_make)
        db.session.flush()
        return new_make.id

def get_or_create_model(model_name, make_id):
    """Get or create vehicle model"""
    if not model_name or not make_id:
        return None
    
    normalized_name = model_name.strip().title()
    model = VehicleModel.query.filter_by(make_id=make_id, name=normalized_name).first()
    
    if model:
        return model.id
    else:
        slug = normalized_name.lower().replace(' ', '-')
        new_model = VehicleModel(make_id=make_id, name=normalized_name, slug=slug)
        db.session.add(new_model)
        db.session.flush()
        return new_model.id

def get_or_create_category(category_name):
    """Get or create vehicle category"""
    if not category_name:
        # Default to "Car" if not specified
        category_name = "Car"
    
    normalized_name = category_name.strip().title()
    category = VehicleCategory.query.filter_by(name=normalized_name).first()
    
    if category:
        return category.id
    else:
        # Check if category with same slug already exists
        slug = normalized_name.lower().replace(' ', '-')
        existing_slug = VehicleCategory.query.filter_by(slug=slug).first()
        
        if existing_slug:
            return existing_slug.id
        else:
            try:
                new_category = VehicleCategory(name=normalized_name, slug=slug)
                db.session.add(new_category)
                db.session.flush()
                return new_category.id
            except IntegrityError:
                # If there's still a constraint error, try to find the existing one
                db.session.rollback()
                existing = VehicleCategory.query.filter_by(slug=slug).first()
                if existing:
                    return existing.id
                else:
                    # Last resort: get the first available category
                    first_category = VehicleCategory.query.first()
                    return first_category.id if first_category else None

# ------------------------------------------------------------------
# 1) POST /api/vehicles : Create a vehicle
# ------------------------------------------------------------------
@api_vehicles_bp.route('/api/vehicles', methods=['POST'])
def create_vehicle():
    """
    Creates a new vehicle listing.
    Receives JSON with vehicle data and creates all necessary related records.
    """
    import json
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body with data."}), 400

    print("==========================================================")
    print("== JSON RECEIVED AT /api/vehicles ==")
    try:
        print(json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8'))
    except Exception as log_error:
        print(f"[WARN] Could not pretty-print incoming JSON: {log_error}")
    print("==========================================================")

    # Validate required fields
    if not data.get('title'):
        return jsonify({"error": "Field 'title' is required."}), 400
    
    if not data.get('price'):
        return jsonify({"error": "Field 'price' is required."}), 400
    
    # Year is optional - we'll try to extract it from title or use a default
    year_value = data.get('year')
    
    # Check if year is a stock number (all digits) and extract from title instead
    if year_value and str(year_value).isdigit() and len(str(year_value)) > 4:
        print(f"[WARN] Year appears to be stock number '{year_value}', extracting from title...")
        year_value = None
    
    if not year_value:
        # Try to extract year from title (e.g., "2018 Toyota Corolla")
        import re
        title = data.get('title', '')
        year_match = re.search(r'\b(19|20)\d{2}\b', title)
        if year_match:
            year_value = int(year_match.group())
            print(f"[INFO] Extracted year from title: {year_value}")
        else:
            year_value = 2020  # Default year if not found
            print(f"[WARN] Could not extract year from title, using default: {year_value}")

    try:
        # --- 0. Check for duplicates (NOW USING FREE SENTENCE-BERT!) ---
        print("\n--- STEP 0: Checking for Duplicates (FREE Vectorization) ---")
        print("   Using FREE Sentence-BERT - Cost: $0 (vs $7K-15K with OpenAI)")
        
        deduplicator = VehicleDeduplicator()
        
        # Prepare vehicle data for duplicate checking
        vehicle_data = {
            'title': data.get('title'),
            'description': data.get('description'),
            'make': data.get('make'),
            'model': data.get('model'),
            'year': year_value,
            'price': data.get('price'),
            'mileage': data.get('mileage'),
            'fuel_type': data.get('fuel_type'),
            'transmission': data.get('transmission'),
            'color': data.get('color'),
            'features': data.get('features'),
            'condition': data.get('condition'),
            'location': data.get('location_text', {}).get('displayName') if data.get('location_text') else None,
            'latitude': data.get('location_text', {}).get('lat') if data.get('location_text') else None,
            'longitude': data.get('location_text', {}).get('lon') if data.get('location_text') else None
        }
        
        # Check for duplicates (FREE - no API cost!)
        is_duplicate, duplicate_vehicles = deduplicator.check_for_duplicates(vehicle_data)
        
        # Filter duplicates that are truly conflicts (same link or very high similarity on same domain)
        official_link = data.get('official_link')
        domain_name = (data.get('domain') or '').strip().lower()
        conflicting_duplicates = []

        if is_duplicate:
            for dup in duplicate_vehicles:
                dup_vehicle = dup.get('vehicle', {})
                dup_link = dup_vehicle.get('official_link')
                dup_domain = (dup_vehicle.get('domain') or '').strip().lower()
                similarity = dup.get('similarity_score', 0)

                same_link = official_link and dup_link and official_link == dup_link
                same_domain_high_similarity = (
                    domain_name
                    and dup_domain
                    and domain_name == dup_domain
                    and similarity >= 0.93
                )

                if same_link or same_domain_high_similarity:
                    conflicting_duplicates.append(dup)

        if conflicting_duplicates:
            print(f"DUPLICATE DETECTED: Found {len(conflicting_duplicates)} conflicts (from {len(duplicate_vehicles)} candidates)")
            top_dup = conflicting_duplicates[0]
            print(f"Top match: {top_dup['vehicle']['title']} (similarity: {top_dup['similarity_score']:.2%})")
            return jsonify({
                "error": "Vehicle appears to be a duplicate",
                "duplicate_count": len(conflicting_duplicates),
                "similar_vehicles": [
                    {
                        "id": dup['vehicle']['id'],
                        "title": dup['vehicle']['title'],
                        "similarity_score": dup['similarity_score']
                    } for dup in conflicting_duplicates[:5]  # Return top 5
                ]
            }), 409  # Conflict status code
        elif is_duplicate:
            print(f"[INFO] Duplicate candidates found ({len(duplicate_vehicles)}), but none met strict conflict rules. Continuing...")
        
        print("No duplicates found, proceeding with creation...")

        # --- 1. Create or get location ---
        print("\n--- STEP 1: Creating/Getting Location ---")
        location_data = data.get('location_text')
        location_id = None
        
        if location_data:
            location_id = get_or_create_location(location_data)
            print(f"Location ID: {location_id}")
        else:
            print("[WARN] No location data provided, location will be null")
            # Location is optional - we'll create the vehicle without it

        # --- 2. Get or create domain ---
        print("\n--- STEP 2: Getting Domain ID ---")
        domain_id = get_or_create_domain(data.get('domain'), data.get('image'))
        print(f"Domain ID: {domain_id}")

        # --- 3. Get or create make ---
        print("\n--- STEP 3: Getting Make ID ---")
        make_name = data.get('make')
        
        # Check if make is a stock number (all digits) and extract from title instead
        if make_name and make_name.isdigit():
            print(f"[WARN] Make appears to be stock number '{make_name}', extracting from title...")
            make_name = None
        
        # If make is missing, try to extract from title (e.g., "2025 Ford Mustang")
        if not make_name:
            title = data.get('title', '')
            import re
            # Common car makes (expanded list)
            known_makes = ['Ford', 'Toyota', 'Honda', 'Chevrolet', 'BMW', 'Mercedes', 'Audi', 
                          'Volkswagen', 'Nissan', 'Mazda', 'Hyundai', 'Kia', 'Lexus', 'Jeep',
                          'Dodge', 'Ram', 'GMC', 'Subaru', 'Volvo', 'Porsche', 'Tesla', 'Land Rover',
                          'Acura', 'Infiniti', 'Lincoln', 'Cadillac', 'Buick', 'Chrysler', 'Jaguar',
                          'Maserati', 'Bentley', 'Rolls Royce', 'Ferrari', 'Lamborghini', 'McLaren',
                          'Aston Martin', 'Alfa Romeo', 'Genesis', 'MINI', 'Smart', 'Fiat', 'Mitsubishi',
                          'Suzuki', 'Isuzu']
            for make in known_makes:
                if make.lower() in title.lower():
                    make_name = make
                    print(f"[INFO] Extracted make from title: {make_name}")
                    break
        
        if not make_name:
            print("[WARN] No make provided and couldn't extract from title, using 'Unknown'")
            make_name = "Unknown"
        
        make_id = get_or_create_make(make_name)
        print(f"Make ID: {make_id}")

        # --- 4. Get or create model ---
        print("\n--- STEP 4: Getting Model ID ---")
        model_name = data.get('model')
        
        # Check if model is a stock number (all digits) and extract from title instead
        if model_name and model_name.isdigit():
            print(f"[WARN] Model appears to be stock number '{model_name}', extracting from title...")
            model_name = None
        
        # If model is missing, try to extract from title
        if not model_name and make_name:
            title = data.get('title', '')
            # Remove the make from title and try to get the model
            title_without_make = title.replace(make_name, '').strip()
            # Extract the first word after year (if present) as model
            words = title_without_make.split()
            if len(words) > 0:
                model_name = words[0]
                print(f"[INFO] Extracted model from title: {model_name}")
        
        model_id = None
        if model_name and make_id:
            model_id = get_or_create_model(model_name, make_id)
            print(f"Model ID: {model_id}")
        else:
            print("[WARN] No model extracted, will be null")

        # --- 5. Get or create category ---
        print("\n--- STEP 5: Getting Category ID ---")
        # Truncate category to prevent database overflow
        raw_category = data.get('category', '')
        if raw_category and len(raw_category) > 50:
            print(f"[WARN] Category too long ({len(raw_category)} chars), truncating to 50...")
            raw_category = raw_category[:50]
        
        # Always ensure we have a category_id (it's required in the database)
        if raw_category:
            category_id = get_or_create_category(raw_category)
        else:
            print("[WARN] No category provided, using default 'Car'")
            category_id = get_or_create_category("Car")  # Default category
        
        print(f"Category ID: {category_id}")

        # --- 6. Create the vehicle record ---
        print("\n--- STEP 6: Creating Vehicle Record ---")
        
        # Truncate fields to prevent database overflow
        def truncate_field(value, max_length, field_name=""):
            if value and len(str(value)) > max_length:
                print(f"[WARN] Truncating {field_name or 'field'} from {len(str(value))} to {max_length} chars: '{str(value)[:30]}...'")
                return str(value)[:max_length]
            return value
        
        # For now, we'll use a default user_id of 1 (admin) for scraped vehicles
        # You may want to create a specific "scraper bot" user
        default_user_id = 1
        
        new_vehicle = Vehicle(
            # Basic Information
            title=truncate_field(data.get('title'), 255, "title"),
            description=data.get('description'),  # TEXT field, no limit
            price=parse_float(data.get('price')),
            
            # Vehicle Specifications
            category_id=category_id,
            make_id=make_id,
            model_id=model_id,
            year=parse_int(year_value),
            
            # Technical Details
            fuel_type=truncate_field(data.get('fuel_type'), 50, "fuel_type"),
            transmission=truncate_field(data.get('transmission'), 50, "transmission"),
            mileage=parse_int(data.get('mileage')),
            engine_size=parse_float(data.get('engine_size')),
            horsepower=parse_int(data.get('horsepower')),
            doors=parse_int(data.get('doors')),
            seats=parse_int(data.get('seats')),
            color=truncate_field(data.get('color'), 50, "color"),
            
            # Condition (max 20 chars in database!)
            condition=truncate_field(data.get('condition'), 20, "condition"),
            seller_type=truncate_field(data.get('seller_type'), 20, "seller_type"),
            
            # Features
            features=data.get('features'),  # TEXT field, no limit
            
            # Location
            location_id=location_id,
            latitude=location_data.get('lat') if location_data else None,
            longitude=location_data.get('lon') if location_data else None,
            
            # Status & Promotion
            is_featured=parse_bool(data.get('is_featured')) or False,
            is_urgent=parse_bool(data.get('is_urgent')) or False,
            is_guaranteed=parse_bool(data.get('is_guaranteed')) or False,
            is_new=parse_bool(data.get('is_new')) or False,
            
            # Ownership
            user_id=default_user_id,
            
            # External reference
            external_id=data.get('external_id'),
            external_url=data.get('official_link'),
            
            # Timestamps
            published_date=date.today()
        )

        # --- 7. Process Images ---
        print("\n--- STEP 7: Processing Images ---")
        images_list = data.get('images', [])
        if isinstance(images_list, list) and images_list:
            for i, url in enumerate(images_list):
                if isinstance(url, str) and url.startswith('http'):
                    is_primary = (i == 0)  # First image is primary
                    new_vehicle.images.append(
                        VehicleImage(
                            image_url=url,
                            order=i,
                            is_primary=is_primary
                        )
                    )
            print(f"Added {len(new_vehicle.images)} valid images.")

        # --- 8. Save to database ---
        db.session.add(new_vehicle)
        print("\n--- STEP 8: Executing db.session.commit() ---")
        db.session.commit()
        print("--- COMMIT SUCCESSFUL ---")

        # --- 9. Store vehicle vector for future duplicate detection (FREE!) ---
        print("\n--- STEP 9: Storing Vehicle Vector (FREE Sentence-BERT) ---")
        try:
            # Store vehicle vector using FREE Sentence-BERT
            deduplicator.store_vehicle_vector(new_vehicle.id, vehicle_data)
            print("Vehicle vector stored successfully (Cost: $0!)")
        except Exception as e:
            print(f"Error storing vehicle vector: {e}")
            # Don't fail the creation for vector storage errors

        return jsonify({
            "message": "Vehicle, location, domain, and images created successfully.",
            "vehicle_id": new_vehicle.id,
            "location_id": location_id,
            "domain_id": domain_id,
            "make_id": make_id,
            "model_id": model_id,
            "category_id": category_id
        }), 201

    except Exception as e:
        db.session.rollback()
        import traceback
        print("\n--- !!! ERROR OCCURRED !!! ---")
        print("ERROR TYPE:", type(e).__name__)
        print("ERROR MESSAGE:", str(e))
        traceback.print_exc()
        
        # Extract specific field name from error if possible
        error_msg = str(e)
        if "Data too long for column" in error_msg:
            import re
            match = re.search(r"column '(\w+)'", error_msg)
            if match:
                field_name = match.group(1)
                print(f"\n[WARN] FIELD CAUSING ERROR: '{field_name}'\n")
        
        print("--- ROLLBACK PERFORMED ---")
        return jsonify({
            "error": "Internal error saving vehicle.",
            "details": str(e)
        }), 500


# ------------------------------------------------------------------
# 2) GET /api/vehicles : List all vehicles (with filters)
# ------------------------------------------------------------------
@api_vehicles_bp.route('/api/vehicles', methods=['GET'])
def get_all_vehicles():
    """
    Returns JSON with all vehicles, allowing filtering.
    """
    query = Vehicle.query

    # Price filters
    price_min = request.args.get('price_min', type=float)
    price_max = request.args.get('price_max', type=float)
    if price_min is not None:
        query = query.filter(Vehicle.price >= price_min)
    if price_max is not None:
        query = query.filter(Vehicle.price <= price_max)

    # Year filters
    year_min = request.args.get('year_min', type=int)
    year_max = request.args.get('year_max', type=int)
    if year_min is not None:
        query = query.filter(Vehicle.year >= year_min)
    if year_max is not None:
        query = query.filter(Vehicle.year <= year_max)

    # Mileage filters
    mileage_max = request.args.get('mileage_max', type=int)
    if mileage_max is not None:
        query = query.filter(Vehicle.mileage <= mileage_max)

    # Make/Model filters
    make_id = request.args.get('make_id', type=int)
    if make_id is not None:
        query = query.filter(Vehicle.make_id == make_id)
    
    model_id = request.args.get('model_id', type=int)
    if model_id is not None:
        query = query.filter(Vehicle.model_id == model_id)

    # Category filter
    category_id = request.args.get('category_id', type=int)
    if category_id is not None:
        query = query.filter(Vehicle.category_id == category_id)

    # Fuel type filter
    fuel_type = request.args.get('fuel_type')
    if fuel_type:
        query = query.filter(Vehicle.fuel_type == fuel_type)

    # Order by newest first
    query = query.order_by(Vehicle.published_date.desc(), Vehicle.id.desc())
    
    vehicles = query.all()

    results = []
    for v in vehicles:
        results.append({
            "id": v.id,
            "title": v.title,
            "description": v.description,
            "price": v.price,
            "year": v.year,
            "make": v.make.name if v.make else None,
            "model": v.model.name if v.model else None,
            "category": v.category.name if v.category else None,
            "fuel_type": v.fuel_type,
            "transmission": v.transmission,
            "mileage": v.mileage,
            "engine_size": v.engine_size,
            "horsepower": v.horsepower,
            "doors": v.doors,
            "seats": v.seats,
            "color": v.color,
            "condition": v.condition,
            "seller_type": v.seller_type,
            "features": v.features,
            "location": v.location.name if v.location else None,
            "is_featured": v.is_featured,
            "is_urgent": v.is_urgent,
            "is_new": v.is_new,
            "published_date": v.published_date.isoformat() if v.published_date else None,
            "external_url": v.external_url
        })

    return jsonify(results), 200


# ------------------------------------------------------------------
# 3) GET /api/vehicles/<int:vehicle_id> : Get single vehicle
# ------------------------------------------------------------------
@api_vehicles_bp.route('/api/vehicles/<int:vehicle_id>', methods=['GET'])
def get_vehicle(vehicle_id):
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return jsonify({"error": "Vehicle not found."}), 404

    vehicle_dict = {
        "id": vehicle.id,
        "title": vehicle.title,
        "description": vehicle.description,
        "price": vehicle.price,
        "year": vehicle.year,
        "make": vehicle.make.name if vehicle.make else None,
        "model": vehicle.model.name if vehicle.model else None,
        "category": vehicle.category.name if vehicle.category else None,
        "fuel_type": vehicle.fuel_type,
        "transmission": vehicle.transmission,
        "mileage": vehicle.mileage,
        "condition": vehicle.condition,
        "images": [img.image_url for img in vehicle.images]
    }
    return jsonify(vehicle_dict), 200


# ------------------------------------------------------------------
# 4) DELETE /api/vehicles/<int:vehicle_id> : Delete vehicle
# ------------------------------------------------------------------
@api_vehicles_bp.route('/api/vehicles/<int:vehicle_id>', methods=['DELETE'])
def delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return jsonify({"error": "Vehicle not found."}), 404

    db.session.delete(vehicle)
    db.session.commit()

    return jsonify({
        "message": f"Vehicle with id {vehicle_id} deleted successfully."
    }), 200


# ------------------------------------------------------------------
# 5) GET /api/vehicles/<int:vehicle_id>/duplicates : Get duplicates of a vehicle
# ------------------------------------------------------------------
@api_vehicles_bp.route('/api/vehicles/<int:vehicle_id>/duplicates', methods=['GET'])
def get_vehicle_duplicates(vehicle_id):
    """Get all vehicles that are duplicates of the specified vehicle."""
    try:
        deduplicator = VehicleDeduplicator()
        duplicates = deduplicator.get_duplicate_vehicles(vehicle_id)
        
        return jsonify({
            "vehicle_id": vehicle_id,
            "duplicate_count": len(duplicates),
            "duplicates": duplicates
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Error getting vehicle duplicates",
            "details": str(e)
        }), 500


# ------------------------------------------------------------------
# 6) POST /api/vehicles/check-duplicate : Check if a vehicle is a duplicate
# ------------------------------------------------------------------
@api_vehicles_bp.route('/api/vehicles/check-duplicate', methods=['POST'])
def check_duplicate():
    """Check if a vehicle is a duplicate without storing it."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body with data."}), 400

    try:
        deduplicator = VehicleDeduplicator()
        
        # Prepare vehicle data for duplicate checking
        vehicle_data = {
            'title': data.get('title'),
            'description': data.get('description'),
            'make': data.get('make'),
            'model': data.get('model'),
            'year': data.get('year'),
            'price': data.get('price'),
            'mileage': data.get('mileage'),
            'fuel_type': data.get('fuel_type'),
            'transmission': data.get('transmission'),
            'color': data.get('color'),
            'location': data.get('location_text', {}).get('displayName') if data.get('location_text') else None,
            'latitude': data.get('location_text', {}).get('lat') if data.get('location_text') else None,
            'longitude': data.get('location_text', {}).get('lon') if data.get('location_text') else None
        }
        
        is_duplicate, duplicates = deduplicator.check_for_duplicates(vehicle_data)
        
        return jsonify({
            "is_duplicate": is_duplicate,
            "duplicate_count": len(duplicates),
            "similar_vehicles": duplicates
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Error checking for duplicates",
            "details": str(e)
        }), 500

