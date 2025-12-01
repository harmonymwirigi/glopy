"""
OAuth Configuration for Google, Facebook, and Microsoft
"""
from authlib.integrations.flask_client import OAuth
import os

# Initialize OAuth
oauth = OAuth()

def init_oauth(app):
    """Initialize OAuth providers with the Flask app"""
    oauth.init_app(app)
    
    # Google OAuth
    oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
            'prompt': 'select_account',  # Force account selection
        }
    )
    
    # Facebook OAuth
    oauth.register(
        name='facebook',
        client_id=os.environ.get('FACEBOOK_CLIENT_ID'),
        client_secret=os.environ.get('FACEBOOK_CLIENT_SECRET'),
        access_token_url='https://graph.facebook.com/oauth/access_token',
        access_token_params=None,
        authorize_url='https://www.facebook.com/dialog/oauth',
        authorize_params=None,
        api_base_url='https://graph.facebook.com/',
        client_kwargs={
            'scope': 'email public_profile',
        }
    )
    
    # Microsoft OAuth
    oauth.register(
        name='microsoft',
        client_id=os.environ.get('MICROSOFT_CLIENT_ID'),
        client_secret=os.environ.get('MICROSOFT_CLIENT_SECRET'),
        server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
        }
    )
    
    return oauth

