#!/usr/bin/env python3
"""
Script to update announcement_images.image_url column length from 200 to 1000.
This fixes the "Data too long for column 'image_url'" error.

Usage:
    python update_image_url_column.py
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def update_image_url_column():
    """Update the image_url column length in announcement_images table"""
    with app.app_context():
        try:
            print("🔄 Updating announcement_images.image_url column length...")
            
            # Check current column size
            result = db.session.execute(text("""
                SELECT CHARACTER_MAXIMUM_LENGTH 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'announcement_images' 
                AND COLUMN_NAME = 'image_url'
            """))
            
            current_size = result.fetchone()
            if current_size:
                print(f"   Current column size: {current_size[0]} characters")
            
            # Update the column
            db.session.execute(text("""
                ALTER TABLE announcement_images 
                MODIFY COLUMN image_url VARCHAR(1000) NOT NULL
            """))
            
            db.session.commit()
            print("✅ Successfully updated image_url column to 1000 characters!")
            
            # Verify the change
            result = db.session.execute(text("""
                SELECT CHARACTER_MAXIMUM_LENGTH 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'announcement_images' 
                AND COLUMN_NAME = 'image_url'
            """))
            
            new_size = result.fetchone()
            if new_size:
                print(f"   New column size: {new_size[0]} characters")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating column: {e}")
            print("\n💡 Alternative: Run this SQL command manually:")
            print("   ALTER TABLE announcement_images MODIFY COLUMN image_url VARCHAR(1000) NOT NULL;")
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("Update announcement_images.image_url Column Length")
    print("=" * 60)
    print()
    
    success = update_image_url_column()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("   The API will now accept image URLs up to 1000 characters.")
        print("   Tracking URLs will be automatically filtered out.")
    else:
        print("\n❌ Migration failed. Please run the SQL command manually.")
        sys.exit(1)

