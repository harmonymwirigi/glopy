#!/usr/bin/env python3
"""
Script to set up default pricing plan
Run this script to ensure there's a default pricing plan in the database
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import PricingPlan

def setup_default_pricing():
    """Create default pricing plan if it doesn't exist"""
    with app.app_context():
        # Check if pricing plan already exists
        existing_plan = PricingPlan.query.filter_by(is_active=True).first()
        if existing_plan:
            print(f"Pricing plan already exists: {existing_plan.name} - €{existing_plan.price_per_ad}")
            return
        
        # Create default pricing plan
        default_plan = PricingPlan(
            name='Plan Estándar',
            description='Plan de precios estándar para anuncios premium',
            price_per_ad=5.0,
            max_free_ads=100000,  # High limit for app launch period
            is_active=True
        )
        
        db.session.add(default_plan)
        db.session.commit()
        print("✅ Default pricing plan created: €5.00 per premium ad, 100,000 free ads (launch period)")

if __name__ == "__main__":
    print("Setting up default pricing plan...")
    setup_default_pricing()
    print("Done!")
