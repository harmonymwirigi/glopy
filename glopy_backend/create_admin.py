#!/usr/bin/env python3
"""
Script to create the first admin user for Glopy
Run this script to set up the initial admin account
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, PricingPlan

def create_admin():
    """Create the first admin user"""
    with app.app_context():
        # Check if admin already exists
        existing_admin = User.query.filter_by(is_admin=True).first()
        if existing_admin:
            print(f"Admin user already exists: {existing_admin.email}")
            return
        
        # Get admin details
        print("=== Crear Usuario Administrador ===")
        print("Ingresa los datos para el primer administrador:")
        
        name = input("Nombre completo: ").strip()
        email = input("Email: ").strip()
        password = input("Contraseña: ").strip()
        
        if not name or not email or not password:
            print("Error: Todos los campos son obligatorios")
            return
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"Error: Ya existe un usuario con el email {email}")
            return
        
        # Create admin user
        admin_user = User(
            name=name,
            email=email,
            is_admin=True,
            is_verified=True,
            created_at=datetime.utcnow()
        )
        admin_user.set_password(password)
        
        db.session.add(admin_user)
        
        # Create default pricing plan if it doesn't exist
        existing_plan = PricingPlan.query.filter_by(is_active=True).first()
        if not existing_plan:
            default_plan = PricingPlan(
                name='Plan Estándar',
                description='Plan de precios estándar para anuncios premium',
                price_per_ad=5.0,
                max_free_ads=100000,  # High limit for app launch period
                is_active=True
            )
            db.session.add(default_plan)
            print("Plan de precios por defecto creado: €5.00 por anuncio premium, 100,000 anuncios gratuitos (período de lanzamiento)")
        
        try:
            db.session.commit()
            print(f"\n✅ Usuario administrador creado exitosamente!")
            print(f"   Email: {email}")
            print(f"   Nombre: {name}")
            print(f"   Acceso admin: /admin")
            print(f"\n🔑 Puedes iniciar sesión con estas credenciales")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error al crear el administrador: {e}")

def create_pricing_plan():
    """Create a default pricing plan"""
    with app.app_context():
        existing_plan = PricingPlan.query.filter_by(is_active=True).first()
        if existing_plan:
            print(f"Plan de precios ya existe: {existing_plan.name} - €{existing_plan.price_per_ad}")
            return
        
        plan = PricingPlan(
            name='Plan Estándar',
            description='Plan de precios estándar para anuncios premium',
            price_per_ad=5.0,
            max_free_ads=100000,  # High limit for app launch period
            is_active=True
        )
        
        db.session.add(plan)
        db.session.commit()
        print("✅ Plan de precios creado: €5.00 por anuncio premium, 100,000 anuncios gratuitos (período de lanzamiento)")

if __name__ == "__main__":
    print("Glopy Admin Setup")
    print("================")
    
    while True:
        print("\nOpciones:")
        print("1. Crear usuario administrador")
        print("2. Crear plan de precios por defecto")
        print("3. Salir")
        
        choice = input("\nSelecciona una opción (1-3): ").strip()
        
        if choice == "1":
            create_admin()
        elif choice == "2":
            create_pricing_plan()
        elif choice == "3":
            print("¡Hasta luego!")
            break
        else:
            print("Opción inválida. Por favor selecciona 1, 2 o 3.")
