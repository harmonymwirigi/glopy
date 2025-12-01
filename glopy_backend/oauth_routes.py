"""
OAuth Routes for Google, Facebook, and Microsoft authentication
"""
from flask import Blueprint, redirect, url_for, session, request, flash, jsonify
from oauth_config import oauth
from models import db, User
import secrets
import os

# Create OAuth blueprint
oauth_bp = Blueprint('oauth', __name__, url_prefix='/oauth')

def get_or_create_oauth_user(provider, oauth_id, email, name, profile_picture=None):
    """
    Get existing user by OAuth credentials or create a new one
    Returns (user, is_new_user)
    """
    # First, check if user exists with this OAuth provider and ID
    user = User.query.filter_by(oauth_provider=provider, oauth_id=oauth_id).first()
    
    if user:
        # Update profile picture if provided
        if profile_picture and user.profile_picture != profile_picture:
            user.profile_picture = profile_picture
            db.session.commit()
        return user, False
    
    # Check if a user with this email already exists (non-OAuth account)
    existing_user = User.query.filter_by(email=email).first()
    
    if existing_user:
        # Link OAuth to existing account
        existing_user.oauth_provider = provider
        existing_user.oauth_id = oauth_id
        if profile_picture:
            existing_user.profile_picture = profile_picture
        if not existing_user.is_verified:
            existing_user.is_verified = True  # OAuth emails are verified
        db.session.commit()
        return existing_user, False
    
    # Create new user
    new_user = User(
        email=email,
        name=name,
        oauth_provider=provider,
        oauth_id=oauth_id,
        profile_picture=profile_picture,
        is_verified=True,  # OAuth emails are pre-verified
        password_hash=None,  # No password for OAuth users
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return new_user, True


# ============ GOOGLE OAUTH ============
@oauth_bp.route('/login/google')
def login_google():
    """Initiate Google OAuth login"""
    redirect_uri = url_for('oauth.authorize_google', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@oauth_bp.route('/authorize/google')
def authorize_google():
    """Google OAuth callback"""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            flash('Failed to get user information from Google', 'danger')
            return redirect(url_for('login'))
        
        # Extract user information
        oauth_id = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        profile_picture = user_info.get('picture')
        
        # Get or create user
        user, is_new = get_or_create_oauth_user('google', oauth_id, email, name, profile_picture)
        
        # Set session
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.name
        
        if is_new:
            flash(f'¡Bienvenido {user.name}! Tu cuenta ha sido creada exitosamente.', 'success')
        else:
            flash(f'¡Bienvenido de nuevo {user.name}!', 'success')
        
        return redirect(url_for('home'))
        
    except Exception as e:
        print(f"Google OAuth error: {e}")
        flash('Error al iniciar sesión con Google. Por favor, intenta de nuevo.', 'danger')
        return redirect(url_for('login'))


# ============ FACEBOOK OAUTH ============
@oauth_bp.route('/login/facebook')
def login_facebook():
    """Initiate Facebook OAuth login"""
    redirect_uri = url_for('oauth.authorize_facebook', _external=True)
    return oauth.facebook.authorize_redirect(redirect_uri)


@oauth_bp.route('/authorize/facebook')
def authorize_facebook():
    """Facebook OAuth callback"""
    try:
        token = oauth.facebook.authorize_access_token()
        
        # Get user info from Facebook Graph API
        resp = oauth.facebook.get('me?fields=id,name,email,picture{url}')
        user_info = resp.json()
        
        if not user_info or not user_info.get('email'):
            flash('No se pudo obtener tu email de Facebook. Por favor, asegúrate de que tu cuenta de Facebook tenga un email verificado.', 'danger')
            return redirect(url_for('login'))
        
        # Extract user information
        oauth_id = user_info.get('id')
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        profile_picture = user_info.get('picture', {}).get('data', {}).get('url')
        
        # Get or create user
        user, is_new = get_or_create_oauth_user('facebook', oauth_id, email, name, profile_picture)
        
        # Set session
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.name
        
        if is_new:
            flash(f'¡Bienvenido {user.name}! Tu cuenta ha sido creada exitosamente.', 'success')
        else:
            flash(f'¡Bienvenido de nuevo {user.name}!', 'success')
        
        return redirect(url_for('home'))
        
    except Exception as e:
        print(f"Facebook OAuth error: {e}")
        flash('Error al iniciar sesión con Facebook. Por favor, intenta de nuevo.', 'danger')
        return redirect(url_for('login'))


# ============ MICROSOFT OAUTH ============
@oauth_bp.route('/login/microsoft')
def login_microsoft():
    """Initiate Microsoft OAuth login"""
    redirect_uri = url_for('oauth.authorize_microsoft', _external=True)
    return oauth.microsoft.authorize_redirect(redirect_uri)


@oauth_bp.route('/authorize/microsoft')
def authorize_microsoft():
    """Microsoft OAuth callback"""
    try:
        token = oauth.microsoft.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            flash('Failed to get user information from Microsoft', 'danger')
            return redirect(url_for('login'))
        
        # Extract user information
        oauth_id = user_info.get('sub') or user_info.get('oid')
        email = user_info.get('email') or user_info.get('preferred_username')
        name = user_info.get('name', email.split('@')[0] if email else 'User')
        
        # Microsoft doesn't always provide picture in userinfo, but we can construct it
        profile_picture = None
        
        # Get or create user
        user, is_new = get_or_create_oauth_user('microsoft', oauth_id, email, name, profile_picture)
        
        # Set session
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.name
        
        if is_new:
            flash(f'¡Bienvenido {user.name}! Tu cuenta ha sido creada exitosamente.', 'success')
        else:
            flash(f'¡Bienvenido de nuevo {user.name}!', 'success')
        
        return redirect(url_for('home'))
        
    except Exception as e:
        print(f"Microsoft OAuth error: {e}")
        flash('Error al iniciar sesión con Microsoft. Por favor, intenta de nuevo.', 'danger')
        return redirect(url_for('login'))

