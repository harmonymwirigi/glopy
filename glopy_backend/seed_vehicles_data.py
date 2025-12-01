"""
Seed data for vehicles system - Populates makes, models, and categories
Run this after creating the vehicles tables: python seed_vehicles_data.py
"""
from app import app, db
from models import VehicleCategory, VehicleMake, VehicleModel

def seed_vehicle_data():
    """Populate vehicle categories, makes, and models"""
    
    with app.app_context():
        print("Seeding vehicle data...")
        
        # 1. Create Vehicle Categories
        categories_data = [
            {'name': 'Coche', 'slug': 'car', 'icon': 'bi-car-front-fill', 'is_popular': True, 'display_order': 1},
            {'name': 'SUV / 4x4', 'slug': 'suv-4x4', 'icon': 'bi-truck', 'is_popular': True, 'display_order': 2},
            {'name': 'Furgoneta / Comercial', 'slug': 'van-commercial', 'icon': 'bi-minecart-loaded', 'is_popular': True, 'display_order': 3},
            {'name': 'Motocicleta', 'slug': 'motorcycle', 'icon': 'bi-bicycle', 'is_popular': True, 'display_order': 4},
            {'name': 'Eléctrico / Híbrido', 'slug': 'electric-hybrid', 'icon': 'bi-lightning-charge-fill', 'is_popular': True, 'display_order': 5},
            {'name': 'Camión', 'slug': 'truck', 'icon': 'bi-truck-front', 'is_popular': False, 'display_order': 6},
            {'name': 'Caravana / Autocaravana', 'slug': 'caravan', 'icon': 'bi-house-door', 'is_popular': False, 'display_order': 7},
            {'name': 'Quad / ATV', 'slug': 'quad-atv', 'icon': 'bi-dribbble', 'is_popular': False, 'display_order': 8},
        ]
        
        for cat_data in categories_data:
            existing = VehicleCategory.query.filter_by(slug=cat_data['slug']).first()
            if not existing:
                category = VehicleCategory(**cat_data)
                db.session.add(category)
                print(f"  + Category: {cat_data['name']}")
        
        db.session.commit()
        print(f"[OK] {len(categories_data)} categories created")
        
        # 2. Create Popular Vehicle Makes
        makes_data = [
            # Spanish/European popular brands
            {'name': 'Seat', 'slug': 'seat', 'display_order': 1},
            {'name': 'Renault', 'slug': 'renault', 'display_order': 2},
            {'name': 'Peugeot', 'slug': 'peugeot', 'display_order': 3},
            {'name': 'Citroën', 'slug': 'citroen', 'display_order': 4},
            {'name': 'Volkswagen', 'slug': 'volkswagen', 'display_order': 5},
            {'name': 'Opel', 'slug': 'opel', 'display_order': 6},
            {'name': 'Ford', 'slug': 'ford', 'display_order': 7},
            {'name': 'BMW', 'slug': 'bmw', 'display_order': 8},
            {'name': 'Mercedes-Benz', 'slug': 'mercedes-benz', 'display_order': 9},
            {'name': 'Audi', 'slug': 'audi', 'display_order': 10},
            
            # Japanese brands
            {'name': 'Toyota', 'slug': 'toyota', 'display_order': 11},
            {'name': 'Honda', 'slug': 'honda', 'display_order': 12},
            {'name': 'Nissan', 'slug': 'nissan', 'display_order': 13},
            {'name': 'Mazda', 'slug': 'mazda', 'display_order': 14},
            {'name': 'Suzuki', 'slug': 'suzuki', 'display_order': 15},
            
            # Other popular
            {'name': 'Fiat', 'slug': 'fiat', 'display_order': 16},
            {'name': 'Hyundai', 'slug': 'hyundai', 'display_order': 17},
            {'name': 'Kia', 'slug': 'kia', 'display_order': 18},
            {'name': 'Volvo', 'slug': 'volvo', 'display_order': 19},
            {'name': 'Tesla', 'slug': 'tesla', 'display_order': 20},
        ]
        
        for make_data in makes_data:
            existing = VehicleMake.query.filter_by(slug=make_data['slug']).first()
            if not existing:
                make = VehicleMake(**make_data)
                db.session.add(make)
                print(f"  + Make: {make_data['name']}")
        
        db.session.commit()
        print(f"[OK] {len(makes_data)} makes created")
        
        # 3. Create Popular Models (Sample for a few makes)
        # Get make IDs
        toyota = VehicleMake.query.filter_by(slug='toyota').first()
        bmw = VehicleMake.query.filter_by(slug='bmw').first()
        volkswagen = VehicleMake.query.filter_by(slug='volkswagen').first()
        seat = VehicleMake.query.filter_by(slug='seat').first()
        
        models_data = []
        
        # Toyota models
        if toyota:
            models_data.extend([
                {'make_id': toyota.id, 'name': 'Corolla', 'slug': 'corolla'},
                {'make_id': toyota.id, 'name': 'Camry', 'slug': 'camry'},
                {'make_id': toyota.id, 'name': 'RAV4', 'slug': 'rav4'},
                {'make_id': toyota.id, 'name': 'Yaris', 'slug': 'yaris'},
                {'make_id': toyota.id, 'name': 'Prius', 'slug': 'prius'},
            ])
        
        # BMW models
        if bmw:
            models_data.extend([
                {'make_id': bmw.id, 'name': 'Serie 1', 'slug': 'serie-1'},
                {'make_id': bmw.id, 'name': 'Serie 3', 'slug': 'serie-3'},
                {'make_id': bmw.id, 'name': 'Serie 5', 'slug': 'serie-5'},
                {'make_id': bmw.id, 'name': 'X3', 'slug': 'x3'},
                {'make_id': bmw.id, 'name': 'X5', 'slug': 'x5'},
            ])
        
        # Volkswagen models
        if volkswagen:
            models_data.extend([
                {'make_id': volkswagen.id, 'name': 'Golf', 'slug': 'golf'},
                {'make_id': volkswagen.id, 'name': 'Polo', 'slug': 'polo'},
                {'make_id': volkswagen.id, 'name': 'Passat', 'slug': 'passat'},
                {'make_id': volkswagen.id, 'name': 'Tiguan', 'slug': 'tiguan'},
                {'make_id': volkswagen.id, 'name': 'T-Roc', 'slug': 't-roc'},
            ])
        
        # Seat models
        if seat:
            models_data.extend([
                {'make_id': seat.id, 'name': 'Ibiza', 'slug': 'ibiza'},
                {'make_id': seat.id, 'name': 'León', 'slug': 'leon'},
                {'make_id': seat.id, 'name': 'Arona', 'slug': 'arona'},
                {'make_id': seat.id, 'name': 'Ateca', 'slug': 'ateca'},
            ])
        
        for model_data in models_data:
            existing = VehicleModel.query.filter_by(
                make_id=model_data['make_id'], 
                name=model_data['name']
            ).first()
            if not existing:
                model = VehicleModel(**model_data)
                db.session.add(model)
        
        db.session.commit()
        print(f"[OK] {len(models_data)} models created")
        
        print("\n[SUCCESS] Vehicle data seeded successfully!")
        print(f"   - {len(categories_data)} categories")
        print(f"   - {len(makes_data)} makes")
        print(f"   - {len(models_data)} models")
        print("\nNote: You can add more makes/models through the admin panel or this script")

if __name__ == '__main__':
    seed_vehicle_data()

