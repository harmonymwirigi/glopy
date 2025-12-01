"""
Vehicle Vectorizer Service

This service converts vehicle data into numerical vectors for similarity comparison
using TF-IDF for text features and scaling for numerical features.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)

class VehicleVectorizer:
    """
    Service for converting vehicle data into numerical vectors.
    """
    
    def __init__(self):
        self.text_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
        
    def fit(self, vehicles: List[Dict]):
        """
        Fit the vectorizer with training data.
        
        Args:
            vehicles: List of vehicle dictionaries
        """
        try:
            if not vehicles:
                logger.warning("No vehicles provided for fitting")
                return
            
            # Prepare text data
            text_data = self._prepare_text_data(vehicles)
            
            # Prepare numerical data
            numerical_data = self._prepare_numerical_data(vehicles)
            
            # Fit text vectorizer
            if text_data:
                self.text_vectorizer.fit(text_data)
            
            # Fit numerical scaler
            if len(numerical_data) > 0:
                self.scaler.fit(numerical_data)
            
            self.is_fitted = True
            logger.info(f"Vehicle vectorizer fitted with {len(vehicles)} vehicles")
            
        except Exception as e:
            logger.error(f"Error fitting vehicle vectorizer: {e}")
            raise
    
    def transform_single(self, vehicle_data: Dict) -> Optional[np.ndarray]:
        """
        Transform a single vehicle into a vector.
        
        Args:
            vehicle_data: Dictionary containing vehicle information
            
        Returns:
            Numpy array representing the vehicle vector
        """
        try:
            if not self.is_fitted:
                logger.warning("Vectorizer not fitted, fitting with single vehicle")
                self.fit([vehicle_data])
            
            # Prepare text data
            text_data = self._prepare_text_data([vehicle_data])
            text_vector = None
            if text_data and text_data[0]:
                text_vector = self.text_vectorizer.transform(text_data).toarray()[0]
            
            # Prepare numerical data
            numerical_data = self._prepare_numerical_data([vehicle_data])
            numerical_vector = None
            if len(numerical_data) > 0:
                numerical_vector = self.scaler.transform(numerical_data)[0]
            
            # Combine vectors
            vectors = []
            if text_vector is not None:
                vectors.append(text_vector)
            if numerical_vector is not None:
                vectors.append(numerical_vector)
            
            if not vectors:
                logger.warning("No valid data to vectorize")
                return None
            
            # Concatenate all vectors
            combined_vector = np.concatenate(vectors)
            return combined_vector
            
        except Exception as e:
            logger.error(f"Error transforming vehicle data: {e}")
            return None
    
    def calculate_similarity(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vector1: First vector
            vector2: Second vector
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            # Ensure vectors have the same shape
            if vector1.shape != vector2.shape:
                logger.warning(f"Vector shape mismatch: {vector1.shape} vs {vector2.shape}")
                return 0.0
            
            # Calculate cosine similarity
            similarity = cosine_similarity([vector1], [vector2])[0][0]
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def _prepare_text_data(self, vehicles: List[Dict]) -> List[str]:
        """Prepare text data for TF-IDF vectorization."""
        text_data = []
        
        for vehicle in vehicles:
            # Combine all text fields
            text_parts = []
            
            # Title
            if vehicle.get('title'):
                text_parts.append(str(vehicle['title']))
            
            # Description
            if vehicle.get('description'):
                text_parts.append(str(vehicle['description']))
            
            # Make and model
            if vehicle.get('make'):
                text_parts.append(str(vehicle['make']))
            if vehicle.get('model'):
                text_parts.append(str(vehicle['model']))
            
            # Fuel type and transmission
            if vehicle.get('fuel_type'):
                text_parts.append(str(vehicle['fuel_type']))
            if vehicle.get('transmission'):
                text_parts.append(str(vehicle['transmission']))
            
            # Color
            if vehicle.get('color'):
                text_parts.append(str(vehicle['color']))
            
            # Location
            if vehicle.get('location'):
                text_parts.append(str(vehicle['location']))
            
            # Join all text parts
            combined_text = ' '.join(text_parts)
            text_data.append(combined_text)
        
        return text_data
    
    def _prepare_numerical_data(self, vehicles: List[Dict]) -> List[List[float]]:
        """Prepare numerical data for scaling."""
        numerical_data = []
        
        for vehicle in vehicles:
            row = []
            
            # Year (normalize to 0-1 range)
            year = vehicle.get('year')
            if year and year > 1900:
                # Normalize year to 0-1 range (1900-2030)
                normalized_year = (year - 1900) / 130.0
                row.append(normalized_year)
            else:
                row.append(0.5)  # Default middle value
            
            # Price (log scale)
            price = vehicle.get('price')
            if price and price > 0:
                # Use log scale for price
                log_price = np.log10(price)
                row.append(log_price)
            else:
                row.append(0.0)
            
            # Mileage (log scale)
            mileage = vehicle.get('mileage')
            if mileage and mileage > 0:
                # Use log scale for mileage
                log_mileage = np.log10(mileage)
                row.append(log_mileage)
            else:
                row.append(0.0)
            
            # Latitude and longitude
            lat = vehicle.get('latitude')
            lon = vehicle.get('longitude')
            if lat is not None and lon is not None:
                row.append(lat)
                row.append(lon)
            else:
                row.append(0.0)  # Default latitude
                row.append(0.0)  # Default longitude
            
            numerical_data.append(row)
        
        return numerical_data
