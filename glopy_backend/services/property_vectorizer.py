"""
Property Vectorization Service for Deduplication

This service creates numerical vectors from property data to enable similarity matching
and duplicate detection across different real estate platforms.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import re
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class PropertyVectorizer:
    """
    Service for vectorizing property data and finding similar properties.
    """
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=None,  # We'll handle Spanish stop words manually
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
        
    def _normalize_text(self, text: str) -> str:
        """Normalize text for better vectorization."""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep spaces and basic punctuation
        text = re.sub(r'[^\w\s\-.,]', ' ', text)
        
        # Spanish stop words to remove
        spanish_stop_words = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las', 'una', 'unos', 'unas', 'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas', 'aquel', 'aquella', 'aquellos', 'aquellas', 'mi', 'tu', 'su', 'nuestro', 'nuestra', 'nuestros', 'nuestras', 'vuestro', 'vuestra', 'vuestros', 'vuestras', 'muy', 'más', 'menos', 'mucho', 'poco', 'todo', 'nada', 'algo', 'alguien', 'nadie', 'cada', 'cual', 'cuál', 'cuáles', 'cuando', 'cuándo', 'donde', 'dónde', 'como', 'cómo', 'porque', 'por qué', 'si', 'sí', 'no', 'también', 'tampoco', 'solo', 'sólo', 'ya', 'aún', 'aun', 'siempre', 'nunca', 'jamás', 'aquí', 'allí', 'ahí', 'entonces', 'después', 'antes', 'ahora', 'hoy', 'ayer', 'mañana', 'siempre', 'nunca', 'también', 'tampoco', 'solo', 'sólo', 'ya', 'aún', 'aun', 'muy', 'más', 'menos', 'mucho', 'poco', 'todo', 'nada', 'algo', 'alguien', 'nadie', 'cada', 'cual', 'cuál', 'cuáles', 'cuando', 'cuándo', 'donde', 'dónde', 'como', 'cómo', 'porque', 'por qué', 'si', 'sí', 'no', 'también', 'tampoco', 'solo', 'sólo', 'ya', 'aún', 'aun', 'siempre', 'nunca', 'jamás', 'aquí', 'allí', 'ahí', 'entonces', 'después', 'antes', 'ahora', 'hoy', 'ayer', 'mañana'
        }
        
        # Remove stop words
        words = text.split()
        words = [word for word in words if word not in spanish_stop_words]
        text = ' '.join(words)
        
        # Normalize common real estate terms
        replacements = {
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
        
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _create_text_features(self, properties: List[Dict]) -> List[str]:
        """Create combined text features for each property."""
        text_features = []
        
        for prop in properties:
            # Combine title, description, and other text fields
            # IMPORTANT: Title (address) is repeated 3x to give it more weight
            text_parts = []
            
            if prop.get('title'):
                title_text = self._normalize_text(prop['title'])
                # Repeat title 3 times to increase its importance in vectorization
                # This ensures addresses are given more weight
                text_parts.append(title_text)
                text_parts.append(title_text)  # Second time
                text_parts.append(title_text)  # Third time
            
            if prop.get('description'):
                text_parts.append(self._normalize_text(prop['description']))
            
            if prop.get('property_type'):
                text_parts.append(self._normalize_text(prop['property_type']))
            
            if prop.get('housing_subtype'):
                text_parts.append(self._normalize_text(prop['housing_subtype']))
            
            if prop.get('extras'):
                text_parts.append(self._normalize_text(prop['extras']))
            
            if prop.get('luxury_features'):
                text_parts.append(self._normalize_text(prop['luxury_features']))
            
            # Add location information
            if prop.get('location_name'):
                text_parts.append(self._normalize_text(prop['location_name']))
            
            combined_text = ' '.join(text_parts)
            text_features.append(combined_text)
        
        return text_features
    
    def _create_numerical_features(self, properties: List[Dict]) -> np.ndarray:
        """Create numerical feature matrix."""
        features = []
        
        for prop in properties:
            feature_vector = []
            
            # Price (normalized)
            price = prop.get('price', 0) or 0
            feature_vector.append(price)
            
            # Square meters
            sq_meters = prop.get('square_meters', 0) or 0
            feature_vector.append(sq_meters)
            
            # Rooms
            rooms = prop.get('rooms', 0) or 0
            feature_vector.append(rooms)
            
            # Bathrooms
            bathrooms = prop.get('number_of_bathrooms', 0) or 0
            feature_vector.append(bathrooms)
            
            # Bedrooms
            bedrooms = prop.get('number_of_bedrooms', 0) or 0
            feature_vector.append(bedrooms)
            
            # Location coordinates (if available)
            lat = prop.get('latitude', 0) or 0
            lon = prop.get('longitude', 0) or 0
            feature_vector.extend([lat, lon])
            
            # Boolean features (convert to 0/1)
            boolean_features = [
                'has_parking', 'has_pool', 'has_garden', 'has_terrace',
                'has_air_conditioning', 'has_heating', 'has_elevator',
                'is_exterior', 'pets_allowed', 'is_accessible'
            ]
            
            for feature in boolean_features:
                value = 1 if prop.get(feature) else 0
                feature_vector.append(value)
            
            # Categorical features (one-hot encoded)
            listing_type = prop.get('listing_type', '')
            if listing_type == 'venta':
                feature_vector.extend([1, 0])  # [venta, alquiler]
            elif listing_type == 'alquiler':
                feature_vector.extend([0, 1])
            else:
                feature_vector.extend([0, 0])
            
            features.append(feature_vector)
        
        return np.array(features)
    
    def fit(self, properties: List[Dict]):
        """Fit the vectorizer on a set of properties."""
        try:
            # Create text features
            text_features = self._create_text_features(properties)
            
            # Fit TF-IDF vectorizer
            if text_features:
                self.tfidf_vectorizer.fit(text_features)
            
            # Create and fit numerical features
            numerical_features = self._create_numerical_features(properties)
            if len(numerical_features) > 0:
                self.scaler.fit(numerical_features)
            
            self.is_fitted = True
            logger.info(f"PropertyVectorizer fitted on {len(properties)} properties")
            
        except Exception as e:
            logger.error(f"Error fitting PropertyVectorizer: {e}")
            raise
    
    def transform(self, properties: List[Dict]) -> np.ndarray:
        """Transform properties into vectors."""
        if not self.is_fitted:
            raise ValueError("Vectorizer must be fitted before transforming")
        
        try:
            # Create text features
            text_features = self._create_text_features(properties)
            
            # Transform text features
            if text_features:
                text_vectors = self.tfidf_vectorizer.transform(text_features).toarray()
            else:
                text_vectors = np.zeros((len(properties), 1000))  # Default size
            
            # Create numerical features
            numerical_features = self._create_numerical_features(properties)
            if len(numerical_features) > 0:
                numerical_vectors = self.scaler.transform(numerical_features)
            else:
                numerical_vectors = np.zeros((len(properties), 20))  # Default size
            
            # Combine text and numerical features
            combined_vectors = np.hstack([text_vectors, numerical_vectors])
            
            return combined_vectors
            
        except Exception as e:
            logger.error(f"Error transforming properties: {e}")
            raise
    
    def find_similar_properties(self, 
                              target_property: Dict, 
                              candidate_properties: List[Dict], 
                              similarity_threshold: float = 0.8) -> List[Tuple[int, float]]:
        """
        Find properties similar to the target property.
        
        Args:
            target_property: The property to find matches for
            candidate_properties: List of candidate properties to compare against
            similarity_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of tuples (property_index, similarity_score) sorted by similarity
        """
        if not candidate_properties:
            return []
        
        try:
            # Transform target and candidate properties
            target_vector = self.transform([target_property])
            candidate_vectors = self.transform(candidate_properties)
            
            # Calculate cosine similarities
            similarities = cosine_similarity(target_vector, candidate_vectors)[0]
            
            # Find properties above threshold
            similar_indices = []
            for i, similarity in enumerate(similarities):
                if similarity >= similarity_threshold:
                    similar_indices.append((i, similarity))
            
            # Sort by similarity (highest first)
            similar_indices.sort(key=lambda x: x[1], reverse=True)
            
            return similar_indices
            
        except Exception as e:
            logger.error(f"Error finding similar properties: {e}")
            return []
    
    def is_duplicate(self, 
                    target_property: Dict, 
                    candidate_property: Dict, 
                    similarity_threshold: float = 0.85) -> bool:
        """
        Check if two properties are duplicates.
        
        Args:
            target_property: First property
            candidate_property: Second property
            similarity_threshold: Minimum similarity score to consider as duplicate
        
        Returns:
            True if properties are considered duplicates
        """
        similar_properties = self.find_similar_properties(
            target_property, 
            [candidate_property], 
            similarity_threshold
        )
        
        return len(similar_properties) > 0 and similar_properties[0][1] >= similarity_threshold
