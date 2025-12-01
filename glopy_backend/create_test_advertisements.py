#!/usr/bin/env python3
"""
Script to create test advertisements for testing the UI
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Announcement, AnnouncementImage, Geoname, Sector

def create_test_advertisements():
    """Create test advertisements with various dates and features"""
    
    with app.app_context():
        # Get or create a location
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
        
        # Get or create a sector
        sector = Sector.query.filter_by(name='Inmobiliaria').first()
        if not sector:
            sector = Sector(
                name='Inmobiliaria',
                image_path='/static/images/inmobiliaria.jpg'
            )
            db.session.add(sector)
            db.session.commit()
        
        # Sample property data
        properties_data = [
            {
                'title': 'Piso moderno en el centro de Valencia',
                'price': 250000,
                'rooms': 3,
                'number_of_bathrooms': 2,
                'square_meters': 85,
                # 'location_text': 'Centro, Valencia',  # This field is commented out in the model
                'description': 'Hermoso piso reformado en el corazón de Valencia, cerca de todos los servicios.',
                'has_parking': True,
                'has_elevator': True,
                'has_terrace': False,
                'has_garden': False,
                'has_pool': False,
                'is_exterior': True,
                'has_fitted_wardrobes': True,
                'has_storage_room': False,
                'is_accessible': True,
                'published_date': datetime.utcnow() - timedelta(days=1)
            },
            {
                'title': 'Casa con jardín en zona residencial',
                'price': 450000,
                'rooms': 4,
                'number_of_bathrooms': 3,
                'square_meters': 150,
                # 'location_text': 'Zona residencial, Valencia',
                'description': 'Casa independiente con jardín privado, ideal para familias.',
                'has_parking': True,
                'has_elevator': False,
                'has_terrace': True,
                'has_garden': True,
                'has_pool': True,
                'is_exterior': True,
                'has_fitted_wardrobes': True,
                'has_storage_room': True,
                'is_accessible': False,
                'published_date': datetime.utcnow() - timedelta(days=3)
            },
            {
                'title': 'Ático con terraza panorámica',
                'price': 380000,
                'rooms': 3,
                'number_of_bathrooms': 2,
                'square_meters': 120,
                # 'location_text': 'Eixample, Valencia',
                'description': 'Ático con terraza privada y vistas espectaculares de la ciudad.',
                'has_parking': False,
                'has_elevator': True,
                'has_terrace': True,
                'has_garden': False,
                'has_pool': False,
                'is_exterior': True,
                'has_fitted_wardrobes': True,
                'has_storage_room': True,
                'is_accessible': True,
                'published_date': datetime.utcnow() - timedelta(days=5)
            },
            {
                'title': 'Estudio moderno para jóvenes profesionales',
                'price': 180000,
                'rooms': 1,
                'number_of_bathrooms': 1,
                'square_meters': 45,
                # 'location_text': 'Ruzafa, Valencia',
                'description': 'Estudio completamente equipado en el barrio de moda de Valencia.',
                'has_parking': False,
                'has_elevator': True,
                'has_terrace': False,
                'has_garden': False,
                'has_pool': False,
                'is_exterior': False,
                'has_fitted_wardrobes': True,
                'has_storage_room': False,
                'is_accessible': True,
                'published_date': datetime.utcnow() - timedelta(days=7)
            },
            {
                'title': 'Chalet adosado con piscina comunitaria',
                'price': 320000,
                'rooms': 3,
                'number_of_bathrooms': 2,
                'square_meters': 110,
                # 'location_text': 'Campanar, Valencia',
                'description': 'Chalet adosado en urbanización con piscina comunitaria y zonas verdes.',
                'has_parking': True,
                'has_elevator': False,
                'has_terrace': True,
                'has_garden': True,
                'has_pool': True,
                'is_exterior': True,
                'has_fitted_wardrobes': True,
                'has_storage_room': True,
                'is_accessible': False,
                'published_date': datetime.utcnow() - timedelta(days=10)
            },
            {
                'title': 'Piso de lujo con vistas al mar',
                'price': 650000,
                'rooms': 4,
                'number_of_bathrooms': 3,
                'square_meters': 180,
                # 'location_text': 'Malvarrosa, Valencia',
                'description': 'Piso de lujo con vistas al mar Mediterráneo, acabados de alta calidad.',
                'has_parking': True,
                'has_elevator': True,
                'has_terrace': True,
                'has_garden': False,
                'has_pool': True,
                'is_exterior': True,
                'has_fitted_wardrobes': True,
                'has_storage_room': True,
                'is_accessible': True,
                'published_date': datetime.utcnow() - timedelta(days=2)
            },
            {
                'title': 'Casa rural reformada con encanto',
                'price': 280000,
                'rooms': 3,
                'number_of_bathrooms': 2,
                'square_meters': 95,
                # 'location_text': 'Paterna, Valencia',
                'description': 'Casa rural reformada manteniendo el encanto original, ideal para descanso.',
                'has_parking': True,
                'has_elevator': False,
                'has_terrace': True,
                'has_garden': True,
                'has_pool': False,
                'is_exterior': True,
                'has_fitted_wardrobes': False,
                'has_storage_room': True,
                'is_accessible': False,
                'published_date': datetime.utcnow() - timedelta(days=15)
            },
            {
                'title': 'Loft industrial en nave reconvertida',
                'price': 220000,
                'rooms': 2,
                'number_of_bathrooms': 1,
                'square_meters': 75,
                # 'location_text': 'Benimaclet, Valencia',
                'description': 'Loft con estilo industrial en nave reconvertida, muy luminoso.',
                'has_parking': False,
                'has_elevator': False,
                'has_terrace': False,
                'has_garden': False,
                'has_pool': False,
                'is_exterior': True,
                'has_fitted_wardrobes': False,
                'has_storage_room': False,
                'is_accessible': True,
                'published_date': datetime.utcnow() - timedelta(days=4)
            },
            {
                'title': 'Piso familiar con trastero incluido',
                'price': 295000,
                'rooms': 4,
                'number_of_bathrooms': 2,
                'square_meters': 105,
                # 'location_text': 'Quatre Carreres, Valencia',
                'description': 'Piso familiar con trastero incluido, perfecto para familias numerosas.',
                'has_parking': True,
                'has_elevator': True,
                'has_terrace': False,
                'has_garden': False,
                'has_pool': False,
                'is_exterior': True,
                'has_fitted_wardrobes': True,
                'has_storage_room': True,
                'is_accessible': True,
                'published_date': datetime.utcnow() - timedelta(days=6)
            },
            {
                'title': 'Casa unifamiliar con garaje doble',
                'price': 420000,
                'rooms': 5,
                'number_of_bathrooms': 3,
                'square_meters': 160,
                # 'location_text': 'Burjassot, Valencia',
                'description': 'Casa unifamiliar con garaje doble y jardín, en zona tranquila.',
                'has_parking': True,
                'has_elevator': False,
                'has_terrace': True,
                'has_garden': True,
                'has_pool': False,
                'is_exterior': True,
                'has_fitted_wardrobes': True,
                'has_storage_room': True,
                'is_accessible': False,
                'published_date': datetime.utcnow() - timedelta(days=12)
            }
        ]
        
        # Create announcements
        created_count = 0
        for prop_data in properties_data:
            # Check if announcement already exists
            existing = Announcement.query.filter_by(title=prop_data['title']).first()
            if existing:
                print(f"⚠️  Announcement '{prop_data['title']}' already exists, skipping...")
                continue
            
            announcement = Announcement(
                title=prop_data['title'],
                price=prop_data['price'],
                rooms=prop_data['rooms'],
                number_of_bathrooms=prop_data['number_of_bathrooms'],
                square_meters=prop_data['square_meters'],
                # location_text=prop_data['location_text'],  # This field is commented out in the model
                description=prop_data['description'],
                has_parking=prop_data['has_parking'],
                has_elevator=prop_data['has_elevator'],
                has_terrace=prop_data['has_terrace'],
                has_garden=prop_data['has_garden'],
                has_pool=prop_data['has_pool'],
                is_exterior=prop_data['is_exterior'],
                has_fitted_wardrobes=prop_data['has_fitted_wardrobes'],
                has_storage_room=prop_data['has_storage_room'],
                is_accessible=prop_data['is_accessible'],
                published_date=prop_data['published_date'],
                sector_id=location.id  # sector_id is actually the location_id in this model
                # domain_logo_url='https://via.placeholder.com/100x30/4CAF50/white?text=Test+Site'  # This field doesn't exist in the model
            )
            
            db.session.add(announcement)
            db.session.flush()  # Get the ID
            
            # Add some sample images
            sample_images = [
                'https://via.placeholder.com/400x300/87CEEB/white?text=Exterior',
                'https://via.placeholder.com/400x300/98FB98/white?text=Interior',
                'https://via.placeholder.com/400x300/F0E68C/white?text=Cocina'
            ]
            
            for i, img_url in enumerate(sample_images):
                if i < 2:  # Add 2 images per property
                    image = AnnouncementImage(
                        announcement_id=announcement.id,
                        image_url=img_url,
                        order=i
                    )
                    db.session.add(image)
            
            created_count += 1
            print(f"✅ Created: {prop_data['title']} - {prop_data['price']:,}€")
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n🎉 Successfully created {created_count} test advertisements!")
        print(f"📅 Date range: {min(prop['published_date'] for prop in properties_data).strftime('%Y-%m-%d')} to {max(prop['published_date'] for prop in properties_data).strftime('%Y-%m-%d')}")
        print(f"💰 Price range: {min(prop['price'] for prop in properties_data):,}€ to {max(prop['price'] for prop in properties_data):,}€")
        print(f"🏠 Total rooms: {sum(prop['rooms'] for prop in properties_data)}")
        print(f"📐 Total square meters: {sum(prop['square_meters'] for prop in properties_data)}")
        
        return created_count

if __name__ == '__main__':
    print("🏠 Creating test advertisements...")
    print("=" * 50)
    
    try:
        count = create_test_advertisements()
        print(f"\n✅ Process completed successfully!")
        print(f"🌐 You can now visit http://127.0.0.1:5001/inmobiliaria to see the advertisements")
    except Exception as e:
        print(f"❌ Error creating test advertisements: {e}")
        sys.exit(1)
