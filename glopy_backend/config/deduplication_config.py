"""
Configuration settings for property deduplication system.
"""

# Similarity thresholds
SIMILARITY_THRESHOLD = 0.85  # Minimum similarity score to consider as duplicate
SIMILARITY_THRESHOLD_STRICT = 0.90  # For very strict duplicate detection
SIMILARITY_THRESHOLD_LOOSE = 0.75   # For loose duplicate detection

# Vectorization settings
TFIDF_MAX_FEATURES = 1000
TFIDF_NGRAM_RANGE = (1, 2)
TFIDF_MIN_DF = 1
TFIDF_MAX_DF = 0.95

# Candidate selection settings
MAX_CANDIDATES_PER_LOCATION = 100
MAX_CANDIDATES_GLOBAL = 500

# Text normalization settings
TEXT_NORMALIZATION_RULES = {
    'piso': 'apartamento',
    'casa': 'vivienda',
    'chalet': 'casa',
    'estudio': 'apartamento',
    'duplex': 'apartamento',
    'atico': 'apartamento',
    'habitaciones': 'dormitorios',
    'hab': 'dormitorios',
    'baños': 'aseos',
    'baño': 'aseo',
    'm2': 'metros cuadrados',
    'm²': 'metros cuadrados',
    '€': 'euros',
    'euros': 'euros'
}

# Feature weights for similarity calculation
FEATURE_WEIGHTS = {
    'title': 0.3,
    'description': 0.2,
    'price': 0.15,
    'square_meters': 0.1,
    'rooms': 0.1,
    'location': 0.1,
    'boolean_features': 0.05
}

# Price tolerance for duplicate detection (percentage)
PRICE_TOLERANCE_PERCENT = 10  # 10% price difference is acceptable

# Location tolerance for duplicate detection (meters)
LOCATION_TOLERANCE_METERS = 100  # Properties within 100m are considered same location

# Database cleanup settings
CLEANUP_OLD_SIMILARITIES_DAYS = 30  # Clean up similarities older than 30 days
BATCH_SIZE_FOR_CLEANUP = 1000  # Process similarities in batches

# Logging settings
LOG_DUPLICATE_DETECTION = True
LOG_SIMILARITY_SCORES = True
LOG_VECTORIZATION_STATS = True
