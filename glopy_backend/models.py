from flask_sqlalchemy import SQLAlchemy
from datetime import datetime  # <-- AÑADIDO para manejar fechas

# NUEVO (autoload):
from sqlalchemy import Table, MetaData, text, BigInteger  # <-- Añadimos BigInteger

db = SQLAlchemy()

class Sector(db.Model):
    __tablename__ = 'sectors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    image_path = db.Column(db.String(200), nullable=True)
    # announcements = db.relationship('Announcement', backref='sector', lazy=True)

class RealEstateCategory(db.Model):
    __tablename__ = 'real_estate_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

class Announcement(db.Model):
    __tablename__ = 'announcements3'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)  # Para filtrar rangos de precio
    image = db.Column(db.String(200), nullable=True)

    # Categoría inmobiliaria (Venta, Alquiler, etc.)
    category_id = db.Column(db.Integer, db.ForeignKey('real_estate_categories.id'), nullable=True)
    sector_id = db.Column(db.Integer, db.ForeignKey('geoname.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # User who created the ad

    # 2. Le decimos explícitamente a la relación 'location' que use 'sector_id'
    #    como la clave foránea para la unión.
    location = db.relationship('Geoname', foreign_keys=[sector_id], backref='announcements', lazy='joined')
    # -----------------------------
    # NUEVOS CAMPOS PARA FILTROS
    # -----------------------------
    auction_end_date = db.Column(db.String(30), nullable=True)
    capacity = db.Column(db.Integer, nullable=True)
    commercial_type = db.Column(db.String(50), nullable=True)
    community_included = db.Column(db.Boolean, default=False)
    entity_type = db.Column(db.String(50), nullable=True)
    extras = db.Column(db.String(300), nullable=True)
    furnished = db.Column(db.String(10), nullable=True)
    has_air_conditioning = db.Column(db.Boolean, default=False)
    has_balcony = db.Column(db.Boolean, default=False)
    has_elevator = db.Column(db.Boolean, default=False)
    has_fitted_wardrobes = db.Column(db.Boolean, default=False)
    has_garden = db.Column(db.Boolean, default=False)
    has_heating = db.Column(db.Boolean, default=False)
    has_licence = db.Column(db.Boolean, default=False)
    has_parking = db.Column(db.Boolean, default=False)
    has_pool = db.Column(db.Boolean, default=False)
    has_storage_room = db.Column(db.Boolean, default=False)
    has_street_access = db.Column(db.Boolean, default=False)
    has_terrace = db.Column(db.Boolean, default=False)
    housing_subtype = db.Column(db.String(50), nullable=True)
    industrial_use = db.Column(db.String(50), nullable=True)
    is_accessible = db.Column(db.Boolean, default=False)
    is_conditioned = db.Column(db.Boolean, default=False)
    is_exterior = db.Column(db.Boolean, default=False)
    land_use = db.Column(db.String(50), nullable=True)
    listing_type = db.Column(db.String(20), nullable=True)
    # location_text = db.Column(db.String(100), nullable=True)
    luxury_features = db.Column(db.String(300), nullable=True)
    near_beach = db.Column(db.Boolean, default=False)
    number_of_bathrooms = db.Column(db.Integer, nullable=True)
    number_of_bedrooms = db.Column(db.Integer, nullable=True)
    official_link = db.Column(db.String(300), nullable=True)
    pets_allowed = db.Column(db.Boolean, default=False)
    property_main_type = db.Column(db.String(50), nullable=True)
    property_state = db.Column(db.String(50), nullable=True)
    property_type = db.Column(db.String(50), nullable=True)
    published_at = db.Column(db.String(50), nullable=True)
    published_date = db.Column(db.Date, default=datetime.utcnow)
    relevancy = db.Column(db.Integer, nullable=True)
    rental_duration = db.Column(db.String(50), nullable=True)
    rooms = db.Column(db.Integer, nullable=True)
    search_radius_km = db.Column(db.Float, nullable=True)
    special_tags = db.Column(db.String(300), nullable=True)
    square_meters = db.Column(db.Float, nullable=True)
    vacation_duration = db.Column(db.String(20), nullable=True)
    
    # Map coordinates
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    images = db.relationship(
        'AnnouncementImage', 
        back_populates='announcement', 
        cascade="all, delete-orphan"
    )


# -----------------------------------------------------------------
# NUEVO (autoload) + PK declarada para evitar error sin contexto
# -----------------------------------------------------------------
from sqlalchemy import MetaData, Table

class ProvinciaAuto(db.Model):
    """
    Tabla 'provincia' creada externamente (por .sql).
    Añadimos la PK manual, para que SQLAlchemy no se queje.
    """
    __tablename__ = 'provincia'
    __table_args__ = {'extend_existing': True}

    # FORZAMOS la PK (BigInteger) para que no se queje.
    id_provincia = db.Column(BigInteger, primary_key=True)

    # AÑADIDO: Columna para poder usar p.nombre
    nombre = db.Column(db.String(255), nullable=True)


class MunicipioAuto(db.Model):
    """
    Tabla 'municipio' creada externamente (por .sql).
    Igual, forzamos la PK.
    """
    __tablename__ = 'municipio'
    __table_args__ = {'extend_existing': True}

    id_municipio = db.Column(BigInteger, primary_key=True)

    # AÑADIDO: Para que puedas acceder a p.id_provincia y p.nombre
    id_provincia = db.Column(BigInteger, nullable=False)
    nombre = db.Column(db.String(255), nullable=False)


# Agrega este bloque al final de models.py (sin eliminar el código existente)
class AnnouncementImage(db.Model):
    __tablename__ = 'announcement_images'
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements3.id'), nullable=False)
    image_url = db.Column(db.String(1000), nullable=False)  # Increased for long image URLs
    order = db.Column(db.Integer, nullable=True)

    # Relación: cada imagen pertenece a un anuncio.
    announcement = db.relationship(
        'Announcement', 
        back_populates='images'
    )

class Domain(db.Model):
    """
    Modelo que representa la tabla 'domain'.
    Almacena los dominios de los sitios web y una URL a su logo/imagen.
    """
    __tablename__ = 'domain' # Asegúrate de que el nombre coincida con tu tabla

    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(255), unique=True, nullable=False)
    image = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f'<Domain {self.domain}>'
    
class Geoname2(db.Model):
    """
    Modelo que representa la tabla 'geoname2'
    """
    __tablename__ = 'geoname2'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    ascii_name = db.Column(db.Text)
    alternate_names = db.Column(db.Text)
    latitude = db.Column(db.REAL) 
    longitude = db.Column(db.REAL)
    feature_class = db.Column(db.Text)
    feature_code = db.Column(db.Text)
    country_code = db.Column(db.Text)
    cc2 = db.Column(db.Text)
    admin1_code = db.Column(db.Integer) 
    admin2_code = db.Column(db.Text)
    admin3_code = db.Column(db.Text)
    admin4_code = db.Column(db.Text)
    population = db.Column(db.Integer)
    elevation = db.Column(db.Text) 
    dem = db.Column(db.Integer)
    timezone = db.Column(db.Text)

    def __repr__(self):
        return f'<Geoname2 ID: {self.id}, Name: {self.name}>'


class PropertyVector(db.Model):
    """
    Modelo para almacenar vectores de propiedades para deduplicación.
    """
    __tablename__ = 'property_vectors'
    
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements3.id'), nullable=False, unique=True)
    vector_data = db.Column(db.Text, nullable=False)  # JSON string with vector data
    vector_hash = db.Column(db.String(64), nullable=False, unique=True)  # Hash for quick lookup
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con el anuncio
    announcement = db.relationship('Announcement', backref='property_vector')
    
    def __repr__(self):
        return f'<PropertyVector {self.id} for Announcement {self.announcement_id}>'


class PropertySimilarity(db.Model):
    """
    Modelo para almacenar similitudes calculadas entre propiedades.
    """
    __tablename__ = 'property_similarities'
    
    id = db.Column(db.Integer, primary_key=True)
    property1_id = db.Column(db.Integer, db.ForeignKey('announcements3.id'), nullable=False)
    property2_id = db.Column(db.Integer, db.ForeignKey('announcements3.id'), nullable=False)
    similarity_score = db.Column(db.Float, nullable=False)
    is_duplicate = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    property1 = db.relationship('Announcement', foreign_keys=[property1_id], backref='similarities_as_property1')
    property2 = db.relationship('Announcement', foreign_keys=[property2_id], backref='similarities_as_property2')
    
    # Índice único para evitar duplicados
    __table_args__ = (
        db.UniqueConstraint('property1_id', 'property2_id', name='unique_property_pair'),
    )
    
    def __repr__(self):
        return f'<PropertySimilarity {self.property1_id} <-> {self.property2_id}: {self.similarity_score:.3f}>'


class Geoname(db.Model):
    """
    Modelo que representa la tabla 'geoname'
    """
    __tablename__ = 'geoname'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    latitude = db.Column(db.REAL) 
    longitude = db.Column(db.REAL)
    city = db.Column(db.Text)
    state = db.Column(db.Text)
    country = db.Column(db.Text)
    countryCode = db.Column(db.Text)

    def __repr__(self):
        return f'<Geoname ID: {self.id}, Name: {self.name}>'


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Changed to nullable for OAuth users
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255), unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # OAuth fields
    oauth_provider = db.Column(db.String(50), nullable=True)  # 'google', 'facebook', 'microsoft'
    oauth_id = db.Column(db.String(255), nullable=True)  # OAuth provider user ID
    oauth_token = db.Column(db.Text, nullable=True)  # OAuth access token (encrypted)
    profile_picture = db.Column(db.String(500), nullable=True)  # Profile picture URL from OAuth
    
    # Email alert preferences
    email_alerts_enabled = db.Column(db.Boolean, default=True)
    email_frequency = db.Column(db.String(20), default='daily')  # daily, weekly, immediate
    last_alert_sent = db.Column(db.DateTime, nullable=True)
    
    # Glopy points system
    glopy_points = db.Column(db.Integer, default=0)
    
    # Invitation system
    invited_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    invitation_code = db.Column(db.String(50), unique=True, nullable=True)
    
    # Admin and premium features
    is_admin = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    premium_expires_at = db.Column(db.DateTime, nullable=True)
    free_ads_used = db.Column(db.Integer, default=0)  # Track free ads used
    
    # Company information
    is_company = db.Column(db.Boolean, default=False)
    cif = db.Column(db.String(20), nullable=True)  # CIF for company users
    company_logo = db.Column(db.String(200), nullable=True)  # Logo file path
    
    # Unique constraint for OAuth provider + ID combination
    __table_args__ = (
        db.Index('idx_oauth_provider_id', 'oauth_provider', 'oauth_id'),
    )

    def set_password(self, password: str):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        from werkzeug.security import check_password_hash
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

class SavedAd(db.Model):
    __tablename__ = 'saved_ads'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements3.id'), nullable=False)
    saved_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='saved_ads')
    announcement = db.relationship('Announcement', backref='saved_by_users')
    
    # Unique constraint to prevent duplicate saves
    __table_args__ = (db.UniqueConstraint('user_id', 'announcement_id', name='unique_user_announcement'),)

class SavedSearch(db.Model):
    __tablename__ = 'saved_searches'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    search_name = db.Column(db.String(200), nullable=False)
    search_text = db.Column(db.String(500), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    min_price = db.Column(db.Float, nullable=True)
    max_price = db.Column(db.Float, nullable=True)
    property_type = db.Column(db.String(50), nullable=True)
    min_rooms = db.Column(db.Integer, nullable=True)
    min_bathrooms = db.Column(db.Integer, nullable=True)
    features = db.Column(db.JSON, nullable=True)  # Store features as JSON
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_date = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    user = db.relationship('User', backref='saved_searches')


class Invitation(db.Model):
    """Model for tracking user invitations"""
    __tablename__ = 'invitations'
    
    id = db.Column(db.Integer, primary_key=True)
    inviter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invited_email = db.Column(db.String(255), nullable=False)
    invitation_code = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    inviter = db.relationship('User', foreign_keys=[inviter_id], backref='sent_invitations')
    
    def __repr__(self):
        return f'<Invitation {self.id}: {self.invited_email} by {self.inviter_id}>'


class PointsTransaction(db.Model):
    """Model for tracking Glopy points transactions"""
    __tablename__ = 'points_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    points = db.Column(db.Integer, nullable=False)  # Can be positive or negative
    transaction_type = db.Column(db.String(50), nullable=False)  # invitation_reward, purchase, etc.
    description = db.Column(db.String(255), nullable=True)
    related_invitation_id = db.Column(db.Integer, db.ForeignKey('invitations.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='points_transactions')
    related_invitation = db.relationship('Invitation', backref='points_transactions')
    
    def __repr__(self):
        return f'<PointsTransaction {self.id}: {self.points} points for user {self.user_id}>'


class PricingPlan(db.Model):
    """Model for pricing plans and configurations"""
    __tablename__ = 'pricing_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price_per_ad = db.Column(db.Float, nullable=False)  # Price in euros
    max_free_ads = db.Column(db.Integer, default=100000)  # High limit for app launch period
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<PricingPlan {self.name}: €{self.price_per_ad}/ad>'


class Payment(db.Model):
    """Model for tracking payments and transactions"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stripe_payment_intent_id = db.Column(db.String(255), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)  # Amount in euros
    currency = db.Column(db.String(3), default='EUR')
    status = db.Column(db.String(20), default='pending')  # pending, succeeded, failed, canceled
    payment_method = db.Column(db.String(50), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='payments')
    
    def __repr__(self):
        return f'<Payment {self.id}: €{self.amount} for user {self.user_id}>'


class PremiumAd(db.Model):
    """Model for tracking premium ad purchases"""
    __tablename__ = 'premium_ads'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements3.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=False)
    price_paid = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='premium_ads')
    announcement = db.relationship('Announcement', backref='premium_purchases')
    payment = db.relationship('Payment', backref='premium_ads')
    
    def __repr__(self):
        return f'<PremiumAd {self.id}: Ad {self.announcement_id} by user {self.user_id}>'


class AdminLog(db.Model):
    """Model for tracking admin actions"""
    __tablename__ = 'admin_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # e.g., 'user_created', 'ad_deleted'
    target_type = db.Column(db.String(50), nullable=True)  # 'user', 'ad', 'category'
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    admin = db.relationship('User', backref='admin_logs')
    
    def __repr__(self):
        return f'<AdminLog {self.id}: {self.action} by admin {self.admin_id}>'


class CommercialAd(db.Model):
    """Model for commercial advertisements that companies pay for"""
    __tablename__ = 'commercial_ads'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Ad Content
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    target_url = db.Column(db.String(500), nullable=False)  # Where users go when clicking
    call_to_action = db.Column(db.String(100), default='Ver más')  # Button text
    
    # Company Information
    company_name = db.Column(db.String(200), nullable=False)
    company_logo = db.Column(db.String(500), nullable=True)
    contact_email = db.Column(db.String(255), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    
    # Placement & Display Settings
    placement_frequency = db.Column(db.Integer, default=4)  # Show every N posts (default 4)
    priority = db.Column(db.Integer, default=1)  # Higher priority = shown more often
    category_id = db.Column(db.Integer, db.ForeignKey('real_estate_categories.id'), nullable=True)  # Target specific category
    
    # Status & Scheduling
    status = db.Column(db.String(20), default='active')  # active, paused, expired, pending
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    
    # Payment & Pricing
    price_paid = db.Column(db.Float, nullable=True)  # Amount paid for this ad
    payment_reference = db.Column(db.String(255), nullable=True)
    
    # Analytics & Tracking
    views_count = db.Column(db.Integer, default=0)
    clicks_count = db.Column(db.Integer, default=0)
    last_shown_at = db.Column(db.DateTime, nullable=True)
    
    # Administrative
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)  # Internal notes
    
    # Relationships
    created_by = db.relationship('User', backref='commercial_ads_created')
    category = db.relationship('RealEstateCategory', backref='commercial_ads')
    
    def is_active(self):
        """Check if ad is currently active and within date range"""
        if self.status != 'active':
            return False
        now = datetime.utcnow()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True
    
    def increment_views(self):
        """Increment view counter"""
        self.views_count += 1
        self.last_shown_at = datetime.utcnow()
        db.session.commit()
    
    def increment_clicks(self):
        """Increment click counter"""
        self.clicks_count += 1
        db.session.commit()
    
    def get_ctr(self):
        """Calculate click-through rate"""
        if self.views_count == 0:
            return 0
        return (self.clicks_count / self.views_count) * 100
    
    def __repr__(self):
        return f'<CommercialAd {self.id}: {self.company_name} - {self.title}>'


class CommercialAdView(db.Model):
    """Track individual views of commercial ads"""
    __tablename__ = 'commercial_ad_views'
    
    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey('commercial_ads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Null if not logged in
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ad = db.relationship('CommercialAd', backref='views')
    user = db.relationship('User', backref='commercial_ad_views')
    
    def __repr__(self):
        return f'<CommercialAdView {self.id}: Ad {self.ad_id}>'


class CommercialAdClick(db.Model):
    """Track individual clicks on commercial ads"""
    __tablename__ = 'commercial_ad_clicks'
    
    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey('commercial_ads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Null if not logged in
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ad = db.relationship('CommercialAd', backref='clicks')
    user = db.relationship('User', backref='commercial_ad_clicks')
    
    def __repr__(self):
        return f'<CommercialAdClick {self.id}: Ad {self.ad_id}>'


# ============================================
# AUTOMOBILES / VEHICLES SYSTEM
# ============================================

class VehicleCategory(db.Model):
    """Categories for vehicles (Car, SUV, Motorcycle, etc.)"""
    __tablename__ = 'vehicle_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)  # e.g., 'car', 'suv-4x4'
    icon = db.Column(db.String(50), nullable=True)  # Icon class or emoji
    display_order = db.Column(db.Integer, default=0)
    is_popular = db.Column(db.Boolean, default=False)  # Show in main 5 categories
    
    def __repr__(self):
        return f'<VehicleCategory {self.name}>'


class VehicleMake(db.Model):
    """Vehicle manufacturers (Toyota, BMW, Honda, etc.)"""
    __tablename__ = 'vehicle_makes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    logo_url = db.Column(db.String(500), nullable=True)
    display_order = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<VehicleMake {self.name}>'


class VehicleModel(db.Model):
    """Vehicle models (Corolla, Camry, 3 Series, etc.)"""
    __tablename__ = 'vehicle_models'
    
    id = db.Column(db.Integer, primary_key=True)
    make_id = db.Column(db.Integer, db.ForeignKey('vehicle_makes.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False)
    
    # Relationship
    make = db.relationship('VehicleMake', backref='models')
    
    # Unique constraint: same model name can exist for different makes
    __table_args__ = (
        db.UniqueConstraint('make_id', 'name', name='unique_make_model'),
    )
    
    def __repr__(self):
        return f'<VehicleModel {self.make.name if self.make else "?"} {self.name}>'


class Vehicle(db.Model):
    """Main vehicle listing model"""
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Information
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    
    # Vehicle Specifications
    category_id = db.Column(db.Integer, db.ForeignKey('vehicle_categories.id'), nullable=True)  # Optional - will default to "Car"
    make_id = db.Column(db.Integer, db.ForeignKey('vehicle_makes.id'), nullable=True)  # Optional - will extract from title
    model_id = db.Column(db.Integer, db.ForeignKey('vehicle_models.id'), nullable=True)
    year = db.Column(db.Integer, nullable=True)  # Optional - will extract from title
    
    # Technical Details
    fuel_type = db.Column(db.String(50), nullable=True)  # Gasoline, Diesel, Electric, Hybrid
    transmission = db.Column(db.String(50), nullable=True)  # Manual, Automatic
    mileage = db.Column(db.Integer, nullable=True)  # in kilometers
    engine_size = db.Column(db.Float, nullable=True)  # in liters (e.g., 2.0)
    horsepower = db.Column(db.Integer, nullable=True)  # HP
    doors = db.Column(db.Integer, nullable=True)  # Number of doors
    seats = db.Column(db.Integer, nullable=True)  # Number of seats
    color = db.Column(db.String(50), nullable=True)
    
    # Condition
    condition = db.Column(db.String(20), nullable=True)  # New, Used
    seller_type = db.Column(db.String(20), nullable=True)  # Private, Professional
    
    # Features (comma-separated or JSON)
    features = db.Column(db.Text, nullable=True)  # GPS, Leather seats, Sunroof, etc.
    
    # Location
    location_id = db.Column(db.Integer, db.ForeignKey('geoname.id'), nullable=True)  # Optional - location may not be available
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Status & Promotion
    is_featured = db.Column(db.Boolean, default=False)
    is_urgent = db.Column(db.Boolean, default=False)
    is_guaranteed = db.Column(db.Boolean, default=False)
    is_new = db.Column(db.Boolean, default=False)
    
    # Ownership
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    published_date = db.Column(db.Date, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # External reference (if imported from another site)
    external_id = db.Column(db.String(200), nullable=True)
    external_url = db.Column(db.String(500), nullable=True)
    
    # Relationships
    category = db.relationship('VehicleCategory', backref='vehicles')
    make = db.relationship('VehicleMake', backref='vehicles')
    model = db.relationship('VehicleModel', backref='vehicles')
    location = db.relationship('Geoname', backref='vehicles')
    user = db.relationship('User', backref='vehicles')
    images = db.relationship('VehicleImage', back_populates='vehicle', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Vehicle {self.id}: {self.make.name if self.make else "?"} {self.model.name if self.model else "?"} {self.year}>'


class VehicleImage(db.Model):
    """Images for vehicle listings"""
    __tablename__ = 'vehicle_images'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    image_url = db.Column(db.String(1000), nullable=False)  # Increased for long tracking URLs
    order = db.Column(db.Integer, default=0)
    is_primary = db.Column(db.Boolean, default=False)
    
    # Relationship
    vehicle = db.relationship('Vehicle', back_populates='images')
    
    def __repr__(self):
        return f'<VehicleImage {self.id}: Vehicle {self.vehicle_id}>'


class SavedVehicle(db.Model):
    """User saved/favorited vehicles"""
    __tablename__ = 'saved_vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    saved_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='saved_vehicles')
    vehicle = db.relationship('Vehicle', backref='saved_by_users')
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('user_id', 'vehicle_id', name='unique_user_vehicle'),
    )
    
    def __repr__(self):
        return f'<SavedVehicle {self.id}: User {self.user_id} -> Vehicle {self.vehicle_id}>'


# ============================================
# VEHICLE DEDUPLICATION MODELS
# ============================================

class VehicleVector(db.Model):
    """
    Store vehicle vectors for FREE duplicate detection using Sentence-BERT.
    
    Unlike PropertyVector (which uses expensive OpenAI embeddings), this uses
    FREE local Sentence-BERT models with ZERO API costs!
    """
    __tablename__ = 'vehicle_vectors'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False, unique=True)
    vector_data = db.Column(db.Text, nullable=False)  # JSON string with vector data
    vector_hash = db.Column(db.String(64), nullable=False, unique=True)  # Hash for quick lookup
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    vehicle = db.relationship('Vehicle', backref='vehicle_vector')
    
    def __repr__(self):
        return f'<VehicleVector {self.id}: Vehicle {self.vehicle_id}>'


class VehicleSimilarity(db.Model):
    """
    Store calculated similarities between vehicles for duplicate detection.
    """
    __tablename__ = 'vehicle_similarities'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle1_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    vehicle2_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    similarity_score = db.Column(db.Float, nullable=False)
    is_duplicate = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    vehicle1 = db.relationship('Vehicle', foreign_keys=[vehicle1_id], backref='similarities_as_vehicle1')
    vehicle2 = db.relationship('Vehicle', foreign_keys=[vehicle2_id], backref='similarities_as_vehicle2')
    
    # Unique constraint to prevent duplicate similarity records
    __table_args__ = (
        db.UniqueConstraint('vehicle1_id', 'vehicle2_id', name='unique_vehicle_pair'),
    )
    
    def __repr__(self):
        return f'<VehicleSimilarity {self.id}: Vehicle {self.vehicle1_id} <-> {self.vehicle2_id} (score: {self.similarity_score})>'
