"""
Property Deduplication Service

This service handles the detection and prevention of duplicate property listings
using vectorization and similarity matching.
"""

import json
import hashlib
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import joinedload
from models import db, Announcement, PropertyVector, PropertySimilarity, Geoname, Domain
from .property_vectorizer import PropertyVectorizer

logger = logging.getLogger(__name__)

class PropertyDeduplicator:
    """
    Service for detecting and preventing duplicate property listings.
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.vectorizer = PropertyVectorizer()
        self.similarity_threshold = similarity_threshold
        self.is_initialized = False
        
    def _initialize_vectorizer(self):
        """Initialize the vectorizer with existing properties if not already done."""
        if self.is_initialized:
            return
            
        try:
            # Get a sample of existing properties to fit the vectorizer
            sample_properties = self._get_sample_properties(limit=1000)
            
            if sample_properties:
                self.vectorizer.fit(sample_properties)
                self.is_initialized = True
                logger.info(f"Vectorizer initialized with {len(sample_properties)} properties")
            else:
                logger.warning("No existing properties found for vectorizer initialization")
                
        except Exception as e:
            logger.error(f"Error initializing vectorizer: {e}")
            raise
    
    def _get_sample_properties(self, limit: int = 1000) -> List[Dict]:
        """Get a sample of properties for vectorizer training."""
        try:
            properties = Announcement.query.options(
                joinedload(Announcement.location),
                joinedload(Announcement.images)
            ).limit(limit).all()
            
            return [self._announcement_to_dict(prop) for prop in properties]
            
        except Exception as e:
            logger.error(f"Error getting sample properties: {e}")
            return []
    
    def _announcement_to_dict(self, announcement: Announcement) -> Dict:
        """Convert an Announcement object to a dictionary for vectorization."""
        location = announcement.location
        domain = None
        
        # Get domain information if available
        if announcement.image:
            try:
                domain_id = int(announcement.image)
                domain = Domain.query.get(domain_id)
            except (ValueError, TypeError):
                pass
        
        return {
            'id': announcement.id,
            'title': announcement.title or '',
            'description': announcement.description or '',
            'price': announcement.price or 0,
            'square_meters': announcement.square_meters or 0,
            'rooms': announcement.rooms or 0,
            'number_of_bathrooms': announcement.number_of_bathrooms or 0,
            'number_of_bedrooms': announcement.number_of_bedrooms or 0,
            'property_type': announcement.property_type or '',
            'housing_subtype': announcement.housing_subtype or '',
            'listing_type': announcement.listing_type or '',
            'extras': announcement.extras or '',
            'luxury_features': announcement.luxury_features or '',
            'has_parking': announcement.has_parking or False,
            'has_pool': announcement.has_pool or False,
            'has_garden': announcement.has_garden or False,
            'has_terrace': announcement.has_terrace or False,
            'has_air_conditioning': announcement.has_air_conditioning or False,
            'has_heating': announcement.has_heating or False,
            'has_elevator': announcement.has_elevator or False,
            'is_exterior': announcement.is_exterior or False,
            'pets_allowed': announcement.pets_allowed or False,
            'is_accessible': announcement.is_accessible or False,
            'latitude': location.latitude if location else None,
            'longitude': location.longitude if location else None,
            'location_name': location.name if location else '',
            'domain': domain.domain if domain else '',
            'official_link': announcement.official_link or '',
            'published_date': announcement.published_date
        }
    
    def _create_vector_hash(self, property_data: Dict) -> str:
        """Create a hash for the property data to detect exact duplicates."""
        # Create a string representation of key property characteristics
        key_data = {
            'title': property_data.get('title', ''),
            'price': property_data.get('price', 0),
            'square_meters': property_data.get('square_meters', 0),
            'rooms': property_data.get('rooms', 0),
            'latitude': property_data.get('latitude'),
            'longitude': property_data.get('longitude'),
            'official_link': property_data.get('official_link', '')
        }
        
        # Convert to JSON string and create hash
        data_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def _get_candidate_properties(self, new_property: Dict, limit: int = 100) -> List[Dict]:
        """Get candidate properties for similarity comparison."""
        try:
            from sqlalchemy import func
            
            # Try to filter by coordinates first (most accurate)
            latitude = new_property.get('latitude')
            longitude = new_property.get('longitude')
            
            if latitude and longitude:
                # Filter by proximity (within ~5km radius)
                # Using Haversine formula approximation: ~111km per degree
                # So 0.045 degrees ≈ 5km
                radius = 0.045  # ~5km in degrees
                
                candidates = Announcement.query.filter(
                    Announcement.latitude.isnot(None),
                    Announcement.longitude.isnot(None),
                    Announcement.latitude.between(latitude - radius, latitude + radius),
                    Announcement.longitude.between(longitude - radius, longitude + radius)
                ).options(
                    joinedload(Announcement.location),
                    joinedload(Announcement.images)
                ).limit(limit).all()
                
                if candidates:
                    logger.info(f"Found {len(candidates)} candidates by coordinates proximity")
                    return [self._announcement_to_dict(prop) for prop in candidates]
            
            # Fallback: filter by location_id (sector_id)
            location_id = new_property.get('location_id')
            if location_id:
                candidates = Announcement.query.filter(
                    Announcement.sector_id == location_id
                ).options(
                    joinedload(Announcement.location),
                    joinedload(Announcement.images)
                ).limit(limit).all()
                
                if candidates:
                    logger.info(f"Found {len(candidates)} candidates by location_id")
                    return [self._announcement_to_dict(prop) for prop in candidates]
            
            # Last resort: get recent properties
            logger.info("No location filter, using recent properties")
            candidates = Announcement.query.order_by(
                Announcement.published_date.desc()
            ).options(
                joinedload(Announcement.location),
                joinedload(Announcement.images)
            ).limit(limit).all()
            
            return [self._announcement_to_dict(prop) for prop in candidates]
            
        except Exception as e:
            logger.error(f"Error getting candidate properties: {e}")
            return []
    
    def _extract_address_from_title(self, title: str) -> str:
        """Extract street address from title (usually at the beginning)."""
        if not title:
            return ""
        
        # Address is usually at the start before any description
        # Pattern: "123 Main St, City, State ZIP" or "123 Main Street"
        import re
        
        # Try to extract address pattern (numbers + street name)
        # Match pattern like "1124 NE 172nd Ave" or "16387 SW Dekalb St"
        address_pattern = r'^([0-9]+\s+[A-Z]{0,2}\s+[A-Z0-9\s]+?(?:St|Ave|Rd|Dr|Blvd|Way|Ln|Ct|Pl|Pkwy|Cir|Trl|Hwy|Street|Avenue|Road|Drive|Boulevard|Lane|Court|Place|Parkway|Circle|Trail|Highway)[,\s]?)'
        
        match = re.match(address_pattern, title, re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()
        
        # Fallback: extract first part before comma or common separators
        parts = re.split(r'[,\|\-]', title)
        if parts:
            # Take first part and extract address-like pattern
            first_part = parts[0].strip()
            # If it contains numbers and looks like address
            if re.search(r'\d+', first_part) and len(first_part) < 100:
                return first_part.upper()
        
        return ""
    
    def _addresses_are_different(self, address1: str, address2: str) -> bool:
        """Check if two addresses are clearly different."""
        if not address1 or not address2:
            return False  # Can't compare if one is missing
        
        # Normalize addresses
        addr1 = address1.upper().strip()
        addr2 = address2.upper().strip()
        
        # If addresses are very similar, they might be the same
        if addr1 == addr2:
            return False
        
        # Extract street numbers
        import re
        num1_match = re.match(r'^(\d+)', addr1)
        num2_match = re.match(r'^(\d+)', addr2)
        
        if num1_match and num2_match:
            num1 = num1_match.group(1)
            num2 = num2_match.group(1)
            
            # If street numbers are different, addresses are different
            if num1 != num2:
                return True
        
        # Extract street names (after number and directionals)
        # Remove common directionals for comparison
        directionals = ['NE', 'NW', 'SE', 'SW', 'N', 'S', 'E', 'W', 'NORTH', 'SOUTH', 'EAST', 'WEST']
        street1 = addr1
        street2 = addr2
        
        for dir in directionals:
            street1 = street1.replace(dir, '').strip()
            street2 = street2.replace(dir, '').strip()
        
        # Remove street numbers
        street1 = re.sub(r'^\d+\s*', '', street1).strip()
        street2 = re.sub(r'^\d+\s*', '', street2).strip()
        
        # Extract first significant word (street name)
        words1 = street1.split()
        words2 = street2.split()
        
        if words1 and words2:
            # Compare first meaningful word (skip directionals)
            street_name1 = words1[0] if words1 else ""
            street_name2 = words2[0] if words2 else ""
            
            # If street names are clearly different, addresses are different
            if street_name1 and street_name2 and street_name1 != street_name2:
                # Allow some similarity (typos, abbreviations)
                if len(street_name1) > 3 and len(street_name2) > 3:
                    # Check if first 3-4 chars match (handles abbreviations)
                    if street_name1[:3] != street_name2[:3]:
                        return True
        
        return False
    
    def check_for_duplicates(self, new_property: Dict) -> Tuple[bool, List[Dict]]:
        """
        Check if a new property is a duplicate of existing properties.
        
        Args:
            new_property: Dictionary containing property data
            
        Returns:
            Tuple of (is_duplicate, list_of_duplicate_properties)
        """
        try:
            # Initialize vectorizer if needed
            self._initialize_vectorizer()
            
            # Check for exact duplicates first (same hash)
            vector_hash = self._create_vector_hash(new_property)
            existing_vector = PropertyVector.query.filter_by(vector_hash=vector_hash).first()
            
            if existing_vector:
                logger.info(f"Exact duplicate found for property: {new_property.get('title')}")
                return True, [self._announcement_to_dict(existing_vector.announcement)]
            
            # Get candidate properties for similarity comparison
            candidates = self._get_candidate_properties(new_property)
            
            if not candidates:
                logger.info("No candidate properties found for comparison")
                return False, []
            
            # Extract address from new property title
            new_address = self._extract_address_from_title(new_property.get('title', ''))
            
            # Find similar properties using vectorization
            similar_properties = self.vectorizer.find_similar_properties(
                new_property, 
                candidates, 
                self.similarity_threshold
            )
            
            if similar_properties:
                duplicate_properties = []
                for idx, similarity_score in similar_properties:
                    candidate = candidates[idx]
                    candidate_address = self._extract_address_from_title(candidate.get('title', ''))
                    
                    # IMPORTANT: If addresses are clearly different, reject as duplicate
                    # even if similarity score is high (different properties!)
                    if new_address and candidate_address:
                        if self._addresses_are_different(new_address, candidate_address):
                            logger.info(f"Rejecting duplicate match: addresses are different")
                            logger.info(f"  New: {new_address}")
                            logger.info(f"  Existing: {candidate_address}")
                            logger.info(f"  Similarity was: {similarity_score:.2%}")
                            continue  # Skip this candidate
                    
                    duplicate_properties.append({
                        'property': candidate,
                        'similarity_score': similarity_score
                    })
                
                if duplicate_properties:
                    logger.info(f"Found {len(duplicate_properties)} similar properties after address filtering")
                    return True, duplicate_properties
            
            return False, []
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return False, []
    
    def store_property_vector(self, announcement_id: int, property_data: Dict) -> bool:
        """Store the vector representation of a property."""
        try:
            # Initialize vectorizer if needed
            self._initialize_vectorizer()
            
            # Create vector
            vector = self.vectorizer.transform([property_data])[0]
            
            # Create hash
            vector_hash = self._create_vector_hash(property_data)
            
            # Store in database
            property_vector = PropertyVector(
                announcement_id=announcement_id,
                vector_data=json.dumps(vector.tolist()),
                vector_hash=vector_hash
            )
            
            db.session.add(property_vector)
            db.session.commit()
            
            logger.info(f"Property vector stored for announcement {announcement_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing property vector: {e}")
            db.session.rollback()
            return False
    
    def update_similarity_scores(self, property1_id: int, property2_id: int, similarity_score: float):
        """Update similarity scores between two properties."""
        try:
            # Ensure property1_id < property2_id for consistency
            if property1_id > property2_id:
                property1_id, property2_id = property2_id, property1_id
            
            # Check if similarity already exists
            existing_similarity = PropertySimilarity.query.filter_by(
                property1_id=property1_id,
                property2_id=property2_id
            ).first()
            
            if existing_similarity:
                # Update existing similarity
                existing_similarity.similarity_score = similarity_score
                existing_similarity.is_duplicate = similarity_score >= self.similarity_threshold
            else:
                # Create new similarity record
                similarity = PropertySimilarity(
                    property1_id=property1_id,
                    property2_id=property2_id,
                    similarity_score=similarity_score,
                    is_duplicate=similarity_score >= self.similarity_threshold
                )
                db.session.add(similarity)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating similarity scores: {e}")
            db.session.rollback()
    
    def get_duplicate_properties(self, announcement_id: int) -> List[Dict]:
        """Get all properties that are duplicates of the given property."""
        try:
            similarities = PropertySimilarity.query.filter(
                (PropertySimilarity.property1_id == announcement_id) |
                (PropertySimilarity.property2_id == announcement_id)
            ).filter(
                PropertySimilarity.is_duplicate == True
            ).all()
            
            duplicate_properties = []
            for similarity in similarities:
                # Get the other property (not the one we're checking)
                other_property_id = (similarity.property2_id if similarity.property1_id == announcement_id 
                                   else similarity.property1_id)
                
                other_property = Announcement.query.get(other_property_id)
                if other_property:
                    duplicate_properties.append({
                        'property': self._announcement_to_dict(other_property),
                        'similarity_score': similarity.similarity_score
                    })
            
            return duplicate_properties
            
        except Exception as e:
            logger.error(f"Error getting duplicate properties: {e}")
            return []
    
    def cleanup_old_similarities(self, days: int = 30):
        """Clean up old similarity records to keep the database clean."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            old_similarities = PropertySimilarity.query.filter(
                PropertySimilarity.created_at < cutoff_date
            ).all()
            
            for similarity in old_similarities:
                db.session.delete(similarity)
            
            db.session.commit()
            logger.info(f"Cleaned up {len(old_similarities)} old similarity records")
            
        except Exception as e:
            logger.error(f"Error cleaning up old similarities: {e}")
            db.session.rollback()
