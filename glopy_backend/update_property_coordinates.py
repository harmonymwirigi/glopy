#!/usr/bin/env python3
"""
Script to update property coordinates from their location if missing.
This helps existing properties appear on the map.

Usage:
    python update_property_coordinates.py
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Announcement, Geoname

def update_property_coordinates():
    """Update property coordinates from location if missing"""
    with app.app_context():
        try:
            print("🔄 Updating property coordinates...")
            
            # Find properties without coordinates but with locations that have coordinates
            properties_to_update = Announcement.query.filter(
                db.or_(
                    Announcement.latitude.is_(None),
                    Announcement.longitude.is_(None)
                )
            ).options(
                db.joinedload(Announcement.location)
            ).all()
            
            updated_count = 0
            skipped_count = 0
            
            for prop in properties_to_update:
                if prop.location and prop.location.latitude and prop.location.longitude:
                    # Update property coordinates from location
                    prop.latitude = prop.location.latitude
                    prop.longitude = prop.location.longitude
                    updated_count += 1
                    print(f"  ✅ Updated property {prop.id}: {prop.title[:50]}...")
                else:
                    skipped_count += 1
            
            if updated_count > 0:
                db.session.commit()
                print(f"\n✅ Successfully updated {updated_count} properties with coordinates!")
            else:
                print(f"\nℹ️ No properties needed updating.")
            
            if skipped_count > 0:
                print(f"⚠️ {skipped_count} properties skipped (no location coordinates available)")
            
            return updated_count
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating coordinates: {e}")
            import traceback
            traceback.print_exc()
            return 0

if __name__ == "__main__":
    print("=" * 60)
    print("Update Property Coordinates from Locations")
    print("=" * 60)
    print()
    
    updated = update_property_coordinates()
    
    if updated > 0:
        print(f"\n✅ Migration completed! {updated} properties now have coordinates.")
        print("   These properties will now appear on the map.")
    else:
        print("\nℹ️ No updates needed or migration failed.")

