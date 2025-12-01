"""
Glopy Assistant Service

This service provides an intelligent chat assistant that helps users find properties
by understanding their natural language queries and leveraging OpenAI for natural conversations
and advanced vectorization.
"""

import json
import re
import os
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not available, try to read .env manually
    try:
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    except FileNotFoundError:
        pass

from sqlalchemy.orm import joinedload
from models import db, Announcement, PropertyVector, Geoname
from models import Vehicle, VehicleCategory, VehicleMake, VehicleModel, VehicleImage
from services.property_vectorizer import PropertyVectorizer

# OpenAI integration
try:
    import openai
    OPENAI_AVAILABLE = True
    # Check OpenAI version for compatibility
    try:
        openai_version = openai.__version__
        logging.info(f"OpenAI version: {openai_version}")
    except:
        logging.info("OpenAI version: unknown")
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI not available. Install with: pip install openai")

logger = logging.getLogger(__name__)

class GlopyAssistant:
    """
    Intelligent property search assistant that uses natural language processing
    and vectorization to help users find properties.
    """
    
    def __init__(self):
        self.vectorizer = PropertyVectorizer()
        self.is_initialized = False
        
        # OpenAI configuration
        self.openai_client = None
        self.assistant_id = None
        if OPENAI_AVAILABLE:
            api_key = os.getenv('OPENAI_API_KEY')
            assistant_id = os.getenv('OPENAI_ASSISTANT_ID')
            
            if api_key:
                logger.info(f"OpenAI API key found: {api_key[:10]}...")
                try:
                    # Try different initialization methods for compatibility
                    try:
                        self.openai_client = openai.OpenAI(api_key=api_key)
                        self.assistant_id = assistant_id
                        logger.info("OpenAI client initialized successfully (v1.0+ format)")
                        if assistant_id:
                            logger.info(f"OpenAI Assistant ID configured: {assistant_id}")
                        else:
                            logger.warning("No OPENAI_ASSISTANT_ID found - using chat completions instead")
                    except Exception as e1:
                        logger.warning(f"OpenAI v1.0+ initialization failed: {e1}")
                        # Fallback to older method if available
                        try:
                            openai.api_key = api_key
                            self.openai_client = openai
                            logger.info("OpenAI client initialized successfully (v0.x format)")
                        except Exception as e2:
                            logger.warning(f"OpenAI fallback initialization failed: {e2}")
                            self.openai_client = None
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI client: {e}")
                    self.openai_client = None
            else:
                logger.warning("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        else:
            logger.warning("OpenAI library not available. Install with: pip install openai")
        
        # Conversation context storage
        self.conversation_context = {}
        
        # Property search patterns and keywords
        self.property_patterns = {
            'price': {
                'keywords': ['precio', 'coste', 'costo', 'euros', '€', 'barato', 'caro', 'económico', 'price', 'cost', 'euros', 'cheap', 'expensive', 'budget'],
                'patterns': [
                    r'(\d+)\s*(?:mil|k|000)?\s*(?:euros?|€)',
                    r'(?:hasta|máximo|max|less than|under|below)\s*(\d+)\s*(?:mil|k|000)?\s*(?:euros?|€)?',
                    r'(?:desde|mínimo|min|from|more than|above)\s*(\d+)\s*(?:mil|k|000)?\s*(?:euros?|€)?',
                    r'entre\s*(\d+)\s*y\s*(\d+)\s*(?:mil|k|000)?\s*(?:euros?|€)',
                    r'between\s*(\d+)\s*and\s*(\d+)\s*(?:euros?|€)',
                    r'for\s*less\s*than\s*(\d+)\s*(?:euros?|€)?',
                    r'under\s*(\d+)\s*(?:euros?|€)?',
                    r'(\d+)\s*(?:euros?|€)?\s*(?:or\s*less|maximum|max)'
                ]
            },
            'rooms': {
                'keywords': ['habitaciones', 'dormitorios', 'hab', 'cuartos', 'piezas', 'bedrooms', 'rooms', 'bed', 'room'],
                'patterns': [
                    r'(\d+)\s*(?:habitaciones?|dormitorios?|hab|bedrooms?|rooms?)',
                    r'(\d+)[-–]\s*(?:bedroom|room)',
                    r'(?:al menos|mínimo|min|at least)\s*(\d+)\s*(?:habitaciones?|dormitorios?|bedrooms?|rooms?)',
                    r'(?:hasta|máximo|max|up to|maximum)\s*(\d+)\s*(?:habitaciones?|dormitorios?|bedrooms?|rooms?)'
                ]
            },
            'bathrooms': {
                'keywords': ['baños', 'aseos', 'servicios'],
                'patterns': [
                    r'(\d+)\s*(?:baños?|aseos?)',
                    r'(?:al menos|mínimo|min)\s*(\d+)\s*(?:baños?|aseos?)'
                ]
            },
            'size': {
                'keywords': ['metros', 'm2', 'm²', 'tamaño', 'superficie'],
                'patterns': [
                    r'(\d+)\s*(?:metros?\s*cuadrados?|m2|m²)',
                    r'(?:al menos|mínimo|min)\s*(\d+)\s*(?:metros?\s*cuadrados?|m2|m²)',
                    r'(?:hasta|máximo|max)\s*(\d+)\s*(?:metros?\s*cuadrados?|m2|m²)'
                ]
            },
            'location': {
                'keywords': ['en', 'cerca de', 'cerca', 'zona', 'barrio', 'distrito', 'ciudad', 'in', 'near', 'area', 'neighborhood', 'district', 'city'],
                'patterns': [
                    r'(?:en|cerca de|cerca)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s|$|,|\.|for)',
                    r'(?:zona|barrio|distrito)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s|$|,|\.)',
                    r'(?:in|near)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s|$|,|\.|for)',
                    r'(?:area|neighborhood|district|city)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s|$|,|\.)'
                ]
            },
            'property_type': {
                'keywords': ['piso', 'casa', 'apartamento', 'chalet', 'estudio', 'duplex', 'ático', 'house', 'apartment', 'flat', 'studio', 'penthouse', 'duplex'],
                'patterns': [
                    r'(piso|casa|apartamento|chalet|estudio|duplex|ático|house|apartment|flat|studio|penthouse)',
                    r'(?:busco|quiero|necesito|looking for|want|need)\s+(piso|casa|apartamento|chalet|estudio|duplex|ático|house|apartment|flat|studio|penthouse)'
                ]
            },
            'features': {
                'keywords': ['parking', 'garaje', 'piscina', 'jardín', 'terraza', 'ascensor', 'aire acondicionado'],
                'patterns': [
                    r'(?:con|que tenga|que tenga)\s+(parking|garaje|piscina|jardín|terraza|ascensor|aire acondicionado)',
                    r'(?:necesito|quiero)\s+(parking|garaje|piscina|jardín|terraza|ascensor|aire acondicionado)'
                ]
            }
        }
        
        # Conversation context
        self.conversation_context = {}
    
    def _initialize_vectorizer(self):
        """Initialize the vectorizer with existing properties."""
        if self.is_initialized:
            return
            
        try:
            # Get a sample of properties to fit the vectorizer
            properties = self._get_sample_properties(limit=1000)
            
            if properties:
                self.vectorizer.fit(properties)
                self.is_initialized = True
                logger.info(f"GlopyAssistant vectorizer initialized with {len(properties)} properties")
            else:
                logger.warning("No properties found for GlopyAssistant initialization")
                
        except Exception as e:
            logger.error(f"Error initializing GlopyAssistant vectorizer: {e}")
            raise
    
    def _get_sample_properties(self, limit: int = 1000) -> List[Dict]:
        """Get a sample of properties for vectorizer training."""
        try:
            properties = db.session.query(Announcement).options(
                joinedload(Announcement.location)
            ).limit(limit).all()
            
            property_data = []
            for prop in properties:
                prop_dict = {
                    'id': prop.id,
                    'title': prop.title,
                    'description': prop.description,
                    'price': prop.price,
                    'rooms': prop.rooms,
                    'number_of_bathrooms': prop.number_of_bathrooms,
                    'number_of_bedrooms': prop.number_of_bedrooms,
                    'square_meters': prop.square_meters,
                    'property_type': prop.property_type,
                    'housing_subtype': prop.housing_subtype,
                    'listing_type': prop.listing_type,
                    'latitude': prop.latitude,
                    'longitude': prop.longitude,
                    'location_name': prop.location.name if prop.location else '',
                    'has_parking': prop.has_parking,
                    'has_pool': prop.has_pool,
                    'has_garden': prop.has_garden,
                    'has_terrace': prop.has_terrace,
                    'has_air_conditioning': prop.has_air_conditioning,
                    'has_heating': prop.has_heating,
                    'has_elevator': prop.has_elevator,
                    'is_exterior': prop.is_exterior,
                    'pets_allowed': prop.pets_allowed,
                    'is_accessible': prop.is_accessible,
                    'extras': prop.extras,
                    'luxury_features': prop.luxury_features
                }
                property_data.append(prop_dict)
            
            return property_data
            
        except Exception as e:
            logger.error(f"Error getting sample properties: {e}")
            return []
    
    def _extract_search_criteria(self, user_message: str, conversation_history: List[Dict] = None) -> Dict:
        """Extract search criteria using GPT for intelligent understanding."""
        if not self.openai_client:
            return self._extract_search_criteria_fallback(user_message)
        
        try:
            # Build context from conversation history
            context = ""
            if conversation_history:
                context = "Previous conversation context:\n"
                for msg in conversation_history[-5:]:  # Last 5 messages
                    context += f"{msg['sender']}: {msg['content']}\n"
            
            # Create prompt for GPT to extract criteria
            extraction_prompt = f"""You are an intelligent search assistant for properties and vehicles. Extract search criteria from user messages and return them as JSON.

{context}

User message: "{user_message}"

First, determine the search type:
- search_type: "property", "vehicle", or "unknown"

Then extract the following criteria based on search type:

FOR PROPERTIES:
- max_price: maximum price (number)
- min_price: minimum price (number) 
- min_rooms: minimum number of bedrooms (number)
- max_rooms: maximum number of bedrooms (number)
- min_bathrooms: minimum number of bathrooms (number)
- location: city/area name (string)
- property_type: apartment, house, studio, etc. (string)
- features: list of desired features like parking, pool, garden, etc. (array)
- min_square_meters: minimum size (number)
- max_square_meters: maximum size (number)

FOR VEHICLES:
- max_price: maximum price (number)
- min_price: minimum price (number)
- make: vehicle brand like Toyota, BMW, etc. (string)
- model: vehicle model like Corolla, Golf, etc. (string)
- min_year: minimum year (number)
- max_year: maximum year (number)
- fuel_type: Gasolina, Diesel, Híbrido, Eléctrico (string)
- transmission: Manual, Automática (string)
- category: Coche, SUV, Motocicleta, etc. (string)
- condition: Nuevo, Usado (string)
- location: city/area name (string)

Return ONLY valid JSON with the criteria found. If no criteria are found, return {{"search_type": "unknown"}}.

Examples:
- "2 bedroom price 1500" → {{"search_type": "property", "min_rooms": 2, "max_price": 1500}}
- "quiero un Toyota usado barato" → {{"search_type": "vehicle", "make": "Toyota", "condition": "Usado", "max_price": 15000}}
- "busco algo barato en el centro" → {{"search_type": "unknown", "max_price": 1000, "location": "centro"}}
- "necesito un coche eléctrico" → {{"search_type": "vehicle", "fuel_type": "Eléctrico"}}

JSON:"""

            messages = [
                {"role": "system", "content": "You are an expert at extracting search criteria from natural language for properties and vehicles. Always return valid JSON only."},
                {"role": "user", "content": extraction_prompt}
            ]
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=300,
                temperature=0.1
            )
            
            # Parse JSON response
            import json
            criteria_text = response.choices[0].message.content.strip()
            
            # Clean up the response to extract JSON
            if criteria_text.startswith('```json'):
                criteria_text = criteria_text[7:]
            elif criteria_text.startswith('```'):
                criteria_text = criteria_text[3:]
            if criteria_text.endswith('```'):
                criteria_text = criteria_text[:-3]
            
            criteria = json.loads(criteria_text)
            return criteria
            
        except Exception as e:
            logger.error(f"Error in GPT criteria extraction: {e}")
            return self._extract_search_criteria_fallback(user_message)
    
    def _extract_search_criteria_fallback(self, user_message: str) -> Dict:
        """Fallback criteria extraction using pattern matching."""
        criteria = {}
        message_lower = user_message.lower()
        
        # Extract price information
        price_info = self._extract_price_criteria(message_lower)
        if price_info:
            criteria.update(price_info)
        
        # Extract room information
        room_info = self._extract_room_criteria(message_lower)
        if room_info:
            criteria.update(room_info)
        
        # Extract bathroom information
        bathroom_info = self._extract_bathroom_criteria(message_lower)
        if bathroom_info:
            criteria.update(bathroom_info)
        
        # Extract size information
        size_info = self._extract_size_criteria(message_lower)
        if size_info:
            criteria.update(size_info)
        
        # Extract location information
        location_info = self._extract_location_criteria(message_lower)
        if location_info:
            criteria.update(location_info)
        
        # Extract property type
        property_type = self._extract_property_type(message_lower)
        if property_type:
            criteria['property_type'] = property_type
        
        # Extract features
        features = self._extract_features(message_lower)
        if features:
            criteria['features'] = features
        
        return criteria
    
    def _has_sufficient_search_info(self, search_criteria: Dict, conversation_history: List[Dict], has_property_intent: bool) -> bool:
        """Determine if we have enough information to perform a meaningful search."""
        
        # If user explicitly asks for properties and we have some criteria, search
        if has_property_intent and search_criteria:
            # Check if we have at least one meaningful criterion
            meaningful_criteria = ['min_rooms', 'max_rooms', 'min_price', 'max_price', 'location', 'property_type']
            if any(criterion in search_criteria for criterion in meaningful_criteria):
                return True
        
        # If we have multiple criteria, it's worth searching
        if len(search_criteria) >= 2:
            return True
        
        # If we have a very specific criterion (like exact room count with price)
        if 'min_rooms' in search_criteria and ('min_price' in search_criteria or 'max_price' in search_criteria):
            return True
        
        # If user mentions specific features (like pool, parking)
        if 'features' in search_criteria and search_criteria['features']:
            return True
        
        # If conversation is long and user is being specific
        if len(conversation_history) > 2 and has_property_intent:
            return True
        
        return False
    
    def _extract_price_criteria(self, message: str) -> Dict:
        """Extract price criteria from message."""
        criteria = {}
        
        # Look for price patterns
        for pattern in self.property_patterns['price']['patterns']:
            matches = re.findall(pattern, message)
            if matches:
                if 'hasta' in pattern or 'máximo' in pattern or 'max' in pattern or 'less than' in pattern or 'under' in pattern or 'below' in pattern:
                    criteria['max_price'] = int(matches[0]) * (1000 if 'mil' in message or 'k' in message else 1)
                elif 'desde' in pattern or 'mínimo' in pattern or 'min' in pattern or 'from' in pattern or 'more than' in pattern or 'above' in pattern:
                    criteria['min_price'] = int(matches[0]) * (1000 if 'mil' in message or 'k' in message else 1)
                elif ('entre' in pattern or 'between' in pattern) and len(matches[0]) == 2:
                    criteria['min_price'] = int(matches[0][0]) * (1000 if 'mil' in message or 'k' in message else 1)
                    criteria['max_price'] = int(matches[0][1]) * (1000 if 'mil' in message or 'k' in message else 1)
                else:
                    # Single price mentioned - check if it's a max price (less than/under) or regular price
                    if 'less than' in message or 'under' in message or 'below' in message:
                        criteria['max_price'] = int(matches[0])
                    else:
                        price = int(matches[0]) * (1000 if 'mil' in message or 'k' in message else 1)
                        criteria['max_price'] = price * 1.2  # Add 20% tolerance
                        criteria['min_price'] = price * 0.8  # Subtract 20% tolerance
        
        return criteria
    
    def _extract_room_criteria(self, message: str) -> Dict:
        """Extract room criteria from message."""
        criteria = {}
        
        for pattern in self.property_patterns['rooms']['patterns']:
            matches = re.findall(pattern, message)
            if matches:
                rooms = int(matches[0])
                if 'al menos' in pattern or 'mínimo' in pattern or 'min' in pattern:
                    criteria['min_rooms'] = rooms
                elif 'hasta' in pattern or 'máximo' in pattern or 'max' in pattern:
                    criteria['max_rooms'] = rooms
                else:
                    criteria['min_rooms'] = rooms
        
        return criteria
    
    def _extract_bathroom_criteria(self, message: str) -> Dict:
        """Extract bathroom criteria from message."""
        criteria = {}
        
        for pattern in self.property_patterns['bathrooms']['patterns']:
            matches = re.findall(pattern, message)
            if matches:
                bathrooms = int(matches[0])
                if 'al menos' in pattern or 'mínimo' in pattern or 'min' in pattern:
                    criteria['min_bathrooms'] = bathrooms
                else:
                    criteria['min_bathrooms'] = bathrooms
        
        return criteria
    
    def _extract_size_criteria(self, message: str) -> Dict:
        """Extract size criteria from message."""
        criteria = {}
        
        for pattern in self.property_patterns['size']['patterns']:
            matches = re.findall(pattern, message)
            if matches:
                size = int(matches[0])
                if 'al menos' in pattern or 'mínimo' in pattern or 'min' in pattern:
                    criteria['min_square_meters'] = size
                elif 'hasta' in pattern or 'máximo' in pattern or 'max' in pattern:
                    criteria['max_square_meters'] = size
                else:
                    criteria['min_square_meters'] = size
        
        return criteria
    
    def _extract_location_criteria(self, message: str) -> Dict:
        """Extract location criteria from message."""
        criteria = {}
        
        for pattern in self.property_patterns['location']['patterns']:
            matches = re.findall(pattern, message)
            if matches:
                location = matches[0].strip()
                criteria['location'] = location
                break
        
        return criteria
    
    def _extract_property_type(self, message: str) -> Optional[str]:
        """Extract property type from message."""
        for pattern in self.property_patterns['property_type']['patterns']:
            matches = re.findall(pattern, message)
            if matches:
                return matches[0]
        return None
    
    def _extract_features(self, message: str) -> List[str]:
        """Extract property features from message."""
        features = []
        
        for pattern in self.property_patterns['features']['patterns']:
            matches = re.findall(pattern, message)
            features.extend(matches)
        
        return features
    
    def _get_assistant_response(self, user_message: str, conversation_history: List[Dict], properties: List[Dict] = None, search_criteria: Dict = None) -> str:
        """Get response using OpenAI Assistant API for consistent conversation."""
        if not self.openai_client or not self.assistant_id:
            return self._get_openai_response(user_message, conversation_history, properties, search_criteria)
        
        try:
            # For now, use chat completions instead of deprecated assistant API
            return self._get_openai_response(user_message, conversation_history, properties, search_criteria)
            
            # Build comprehensive context for the assistant
            context_parts = []
            
            # Add conversation history
            if conversation_history:
                context_parts.append("CONVERSATION HISTORY:")
                for msg in conversation_history[-3:]:  # Last 3 messages
                    context_parts.append(f"{msg['sender']}: {msg['content']}")
            
            # Add current user message
            context_parts.append(f"CURRENT USER MESSAGE: {user_message}")
            
            # Add search criteria context
            if search_criteria:
                context_parts.append(f"SEARCH CRITERIA EXTRACTED: {search_criteria}")
            
            # Add database context
            context_parts.append("DATABASE CONTEXT:")
            context_parts.append("- We have properties in Madrid and Valencia")
            context_parts.append("- Property types: apartamento, piso, estudio, casa")
            context_parts.append("- Price range in database: mostly 900-300000 euros")
            context_parts.append("- Most properties are 1-4 bedrooms")
            context_parts.append("- Pool properties are rare (only a few exist)")
            
            # Add search results context
            if properties is not None:
                if properties:
                    context_parts.append(f"SEARCH RESULTS: Found {len(properties)} matching properties")
                    for i, prop in enumerate(properties[:3], 1):
                        price = f"{prop['price']:,.0f}€" if prop['price'] else "Price not specified"
                        rooms = f"{prop['rooms']} rooms" if prop['rooms'] else "Rooms not specified"
                        location = prop.get('location', 'Location not specified')
                        context_parts.append(f"  {i}. {prop['title']} - {price}, {rooms} in {location}")
                else:
                    context_parts.append("SEARCH RESULTS: No properties found matching the criteria")
            else:
                context_parts.append("SEARCH RESULTS: No search performed yet")
            
            # Create context message
            context_message = "\n".join(context_parts)
            
            # Add user message to thread
            self.openai_client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=context_message
            )
            
            # Run the assistant
            run = self.openai_client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            
            # Wait for completion
            while run.status in ['queued', 'in_progress']:
                run = self.openai_client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                import time
                time.sleep(0.5)
            
            if run.status == 'completed':
                # Get the latest message from the assistant
                messages = self.openai_client.beta.threads.messages.list(thread_id=thread_id)
                for message in messages.data:
                    if message.role == 'assistant':
                        return message.content[0].text.value
            
            # Fallback if assistant fails
            return self._get_openai_response(user_message, conversation_history, properties, search_criteria)
            
        except Exception as e:
            logger.error(f"Error with OpenAI Assistant: {e}")
            return self._get_openai_response(user_message, conversation_history, properties, search_criteria)
    
    def _get_or_create_thread(self, conversation_history: List[Dict]) -> str:
        """Get or create a thread ID for the conversation."""
        # For now, create a new thread each time
        # In production, you'd want to maintain thread IDs per user/session
        try:
            thread = self.openai_client.beta.threads.create()
            return thread.id
        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            # Return a fallback thread ID
            return "fallback_thread"
    
    def _get_openai_response(self, user_message: str, conversation_history: List[Dict], properties: List[Dict] = None, search_criteria: Dict = None) -> str:
        """Get a natural response from OpenAI based on the conversation context."""
        if not self.openai_client:
            return self._generate_fallback_response(user_message, properties)
        
        try:
            # Build conversation context for OpenAI
            system_prompt = """Eres Glopy, un asistente inteligente y amigable que ayuda a usuarios a encontrar propiedades, vehículos y otros productos. Eres conversacional, natural y humano - como hablar con un amigo experto.

PERSONALIDAD:
- Hablas de forma natural y conversacional - nunca como un robot
- Eres muy inteligente y entiendes cualquier consulta en lenguaje natural
- Mantienes memoria completa de la conversación para refinar búsquedas progresivamente
- Usas emojis naturalmente cuando tiene sentido
- Haces preguntas inteligentes para entender mejor las necesidades
- Eres paciente, comprensivo y genuinamente útil

CONOCIMIENTO DEL SISTEMA:
Tienes acceso a dos tipos principales de datos:

1. PROPIEDADES/INMUEBLES:
   - Disponibles en múltiples ciudades (principalmente Madrid, Valencia y otras)
   - Tipos: apartamento, piso, estudio, casa, chalet, duplex, ático
   - Precios: desde 900€ hasta 300,000€+
   - Características: habitaciones (1-5+), baños, metros cuadrados, parking, piscina, jardín, terraza, ascensor, aire acondicionado, etc.
   - Ubicaciones: ciudades, barrios, distritos
   - Operaciones: venta y alquiler

2. VEHÍCULOS/AUTOS:
   - Categorías: Coche, SUV/4x4, Furgoneta, Motocicleta, Eléctrico/Híbrido, Camión, Caravana, Quad
   - Marcas: Toyota, BMW, Mercedes, Audi, VW, Seat, Renault, Peugeot, Citroën, Ford, Honda, Nissan, y más
   - Modelos: Corolla, Golf, Serie 3, A3, Focus, C3, etc.
   - Especificaciones: año, precio, kilometraje, combustible (Gasolina, Diesel, Híbrido, Eléctrico), transmisión (Manual, Automática), potencia, puertas, asientos, color
   - Ubicaciones: múltiples ciudades y provincias
   - Condición: Nuevo, Usado
   - Tipo vendedor: Privado, Profesional

CAPACIDADES:
- Entiendes consultas en cualquier formato natural: "busco un piso de 2 habitaciones en Madrid", "quiero un Toyota usado barato", "necesito un coche eléctrico en Valencia"
- Puedes distinguir automáticamente si el usuario busca propiedades o vehículos
- Mantienes contexto completo - recuerdas preferencias anteriores
- Refinas búsquedas progresivamente: "ahora quiero algo más barato", "mejor otra zona", "sin embargo prefiero automático"
- Entiendes contexto implícito y referencias a mensajes anteriores
- Haces búsquedas inteligentes incluso con información parcial

REGLAS DE CONVERSACIÓN:
- Si no está claro qué busca el usuario (propiedad vs vehículo), pregunta amigablemente
- Solo realiza búsquedas cuando tengas suficiente información o el usuario lo pida explícitamente
- Combina criterios de mensajes anteriores con nuevos criterios
- Muestra resultados SOLO cuando hayas realizado una búsqueda real
- Explica por qué ciertos resultados son buenas opciones de forma natural
- Si no hay resultados exactos, sé honesto y sugiere alternativas inteligentes
- NUNCA inventes datos que no existen
- Mantén el tono conversacional y natural en todo momento"""

            # Prepare conversation history
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            for msg in conversation_history[-6:]:  # Keep last 6 messages for context
                messages.append({
                    "role": "user" if msg["sender"] == "user" else "assistant",
                    "content": msg["content"]
                })
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Add search criteria context
            if search_criteria:
                criteria_context = f"\n\nCriterios de búsqueda actuales: {search_criteria}"
                messages.append({"role": "assistant", "content": criteria_context})
            
            # Add properties/vehicles context if available
            if properties:
                results_context = f"\n\nResultados encontrados ({len(properties)}):\n"
                for i, item in enumerate(properties[:5], 1):  # Limit to first 5 results
                    if 'title' in item:  # Property
                        price = f"{item['price']:,.0f}€" if item.get('price') else "Precio no especificado"
                        rooms = f"{item['rooms']} hab." if item.get('rooms') else ""
                        size = f"{item['square_meters']} m²" if item.get('square_meters') else ""
                        location = item.get('location', 'Ubicación no especificada')
                        
                        features = []
                        if item.get('has_parking'): features.append('parking')
                        if item.get('has_pool'): features.append('piscina')
                        if item.get('has_garden'): features.append('jardín')
                        if item.get('has_terrace'): features.append('terraza')
                        if item.get('has_elevator'): features.append('ascensor')
                        if item.get('has_air_conditioning'): features.append('aire acondicionado')
                        
                        features_str = f" ({', '.join(features)})" if features else ""
                        results_context += f"{i}. PROPIEDAD: {item['title']} - {price} {rooms} {size}{features_str} en {location}\n"
                    elif 'make' in item or 'year' in item:  # Vehicle
                        make = item.get('make', '')
                        model = item.get('model', '')
                        year = item.get('year', '')
                        price = f"{item['price']:,.0f}€" if item.get('price') else "Precio no especificado"
                        mileage = f"{item['mileage']:,} km" if item.get('mileage') else ""
                        fuel = item.get('fuel_type', '')
                        location = item.get('location', 'Ubicación no especificada')
                        results_context += f"{i}. VEHÍCULO: {make} {model} {year} - {price} {mileage} {fuel} en {location}\n"
                
                messages.append({"role": "assistant", "content": results_context})
            
            # Get response from OpenAI - try both new and old API formats
            try:
                # Try new v1.0+ API format
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=500,
                    temperature=0.7,
                    presence_penalty=0.1,
                    frequency_penalty=0.1
                )
                return response.choices[0].message.content.strip()
            except AttributeError:
                # Fallback to old API format
                response = self.openai_client.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=500,
                    temperature=0.7,
                    presence_penalty=0.1,
                    frequency_penalty=0.1
                )
                return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error getting OpenAI response: {e}")
            return self._generate_fallback_response(user_message, properties)
    
    def _generate_fallback_response(self, user_message: str, properties: List[Dict] = None) -> str:
        """Generate a fallback response when OpenAI is not available."""
        # Check if this is a greeting or initial message
        is_greeting = any(word in user_message.lower() for word in ['hola', 'hi', 'hello', 'buenas', 'buenos', 'hey'])
        
        if is_greeting:
            return "Hola! Soy Glopy, tu asistente inmobiliario. En que puedo ayudarte hoy? Estas buscando una nueva casa?"
        
        # If properties is None, it means no search was performed
        if properties is None:
            return "Hmm, necesito un poco mas de informacion para ayudarte mejor. Podrias contarme que tipo de propiedad buscas y en que zona te gustaria vivir?"
        
        # If properties is empty list, it means search was performed but no results
        if not properties:
            # Check if this was a specific search that returned no results
            if hasattr(self, '_last_search_criteria') and self._last_search_criteria.get('no_results'):
                return "Lo siento, no he encontrado propiedades que coincidan exactamente con tus criterios. Te gustaria que ajuste la busqueda? Por ejemplo, podriamos ampliar el rango de precios o considerar zonas cercanas. Que opinas?"
            return "Hmm, necesito un poco mas de informacion para ayudarte mejor. Podrias contarme que tipo de propiedad buscas y en que zona te gustaria vivir?"
        
        # We have properties to show
        property_count = len(properties)
        
        if property_count == 1:
            response = f"Perfecto! He encontrado {property_count} propiedad que coincide con lo que buscas:"
        else:
            response = f"Excelente! He encontrado {property_count} propiedades que coinciden con lo que buscas:"
        
        response += "\n\nAqui tienes algunas opciones:"
        
        for i, prop in enumerate(properties[:3], 1):
            price_str = f"{prop['price']:,.0f}€" if prop['price'] else "Precio no especificado"
            rooms_str = f"{prop['rooms']} hab." if prop['rooms'] else ""
            size_str = f"{prop['square_meters']} m²" if prop['square_meters'] else ""
            
            features = []
            if prop.get('has_parking'): features.append("parking")
            if prop.get('has_pool'): features.append("piscina")
            if prop.get('has_garden'): features.append("jardín")
            if prop.get('has_terrace'): features.append("terraza")
            
            features_str = f" ({', '.join(features)})" if features else ""
            
            response += f"\n{i}. {prop['title']} - {price_str} {rooms_str} {size_str}{features_str} en {prop.get('location', 'Ubicación no especificada')}"
        
        if property_count > 3:
            response += f"\n\nY {property_count - 3} propiedades más..."
        
        response += "\n\nTe interesa alguna en particular? Puedo darte mas detalles o ayudarte a refinar tu busqueda."
        
        return response
    
    def _build_flexible_search_query(self, criteria: Dict) -> Dict:
        """Build a more flexible search query when exact matches aren't found."""
        flexible_criteria = {}
        
        # For rooms, allow properties with fewer rooms (but at least 3 if asking for 5+)
        if 'min_rooms' in criteria:
            min_rooms = criteria['min_rooms']
            if min_rooms >= 5:
                flexible_criteria['min_rooms'] = 3  # Show 3+ rooms for 5+ requests
            elif min_rooms >= 3:
                flexible_criteria['min_rooms'] = min_rooms - 1  # Show 1 room less
            else:
                flexible_criteria['min_rooms'] = min_rooms
        
        # Keep features and location but be more flexible with property type
        for key in ['features', 'location']:
            if key in criteria:
                flexible_criteria[key] = criteria[key]
        
        # For property type, be more flexible - don't filter by type if asking for apartment/house
        if 'property_type' in criteria:
            prop_type = criteria['property_type'].lower()
            if prop_type in ['apartment', 'apartamento', 'flat', 'piso']:
                # Allow both apartments and houses for apartment requests
                flexible_criteria['property_type'] = ['apartamento', 'casa', 'piso']
            elif prop_type in ['house', 'casa', 'chalet']:
                # Allow both houses and apartments for house requests  
                flexible_criteria['property_type'] = ['casa', 'apartamento', 'chalet']
        
        # For price, if there's a max_price, increase it by 50%
        if 'max_price' in criteria:
            flexible_criteria['max_price'] = int(criteria['max_price'] * 1.5)
        
        return flexible_criteria
    
    def _build_search_query(self, criteria: Dict) -> Dict:
        """Build a search query from extracted criteria."""
        query = {}
        
        # Price filters
        if 'min_price' in criteria:
            query['min_price'] = criteria['min_price']
        if 'max_price' in criteria:
            query['max_price'] = criteria['max_price']
        
        # Room filters
        if 'min_rooms' in criteria:
            query['min_rooms'] = criteria['min_rooms']
        if 'max_rooms' in criteria:
            query['max_rooms'] = criteria['max_rooms']
        
        # Bathroom filters
        if 'min_bathrooms' in criteria:
            query['min_bathrooms'] = criteria['min_bathrooms']
        
        # Size filters
        if 'min_square_meters' in criteria:
            query['min_square_meters'] = criteria['min_square_meters']
        if 'max_square_meters' in criteria:
            query['max_square_meters'] = criteria['max_square_meters']
        
        # Location filter
        if 'location' in criteria:
            query['location'] = criteria['location']
        
        # Property type filter
        if 'property_type' in criteria:
            query['property_type'] = criteria['property_type']
        
        # Feature filters
        if 'features' in criteria:
            for feature in criteria['features']:
                if feature.lower() in ['parking', 'garaje']:
                    query['has_parking'] = True
                elif feature.lower() in ['piscina']:
                    query['has_pool'] = True
                elif feature.lower() in ['jardín']:
                    query['has_garden'] = True
                elif feature.lower() in ['terraza']:
                    query['has_terrace'] = True
                elif feature.lower() in ['ascensor']:
                    query['has_elevator'] = True
                elif feature.lower() in ['aire acondicionado']:
                    query['has_air_conditioning'] = True
        
        return query
    
    def _search_properties(self, search_query: Dict, limit: int = 20) -> List[Dict]:
        """Search properties based on the query."""
        try:
            # Start with base query
            query = db.session.query(Announcement).options(
                joinedload(Announcement.location)
            )
            
            # Apply filters
            if 'min_price' in search_query:
                query = query.filter(Announcement.price >= search_query['min_price'])
            if 'max_price' in search_query:
                query = query.filter(Announcement.price <= search_query['max_price'])
            
            if 'min_rooms' in search_query:
                query = query.filter(Announcement.rooms >= search_query['min_rooms'])
            if 'max_rooms' in search_query:
                query = query.filter(Announcement.rooms <= search_query['max_rooms'])
            
            if 'min_bathrooms' in search_query:
                query = query.filter(Announcement.number_of_bathrooms >= search_query['min_bathrooms'])
            
            if 'min_square_meters' in search_query:
                query = query.filter(Announcement.square_meters >= search_query['min_square_meters'])
            if 'max_square_meters' in search_query:
                query = query.filter(Announcement.square_meters <= search_query['max_square_meters'])
            
            if 'property_type' in search_query:
                # Handle both single property type and list of property types
                search_types = search_query['property_type']
                if not isinstance(search_types, list):
                    search_types = [search_types]
                
                # Map English property types to Spanish equivalents
                property_type_mapping = {
                    'apartment': 'apartamento',
                    'flat': 'piso',
                    'house': 'casa',
                    'studio': 'estudio',
                    'penthouse': 'ático',
                    'duplex': 'duplex'
                }
                
                # Build OR conditions for all property types
                type_conditions = []
                for search_type in search_types:
                    search_type = search_type.lower()
                    spanish_type = property_type_mapping.get(search_type, search_type)
                    
                    # Search for both the original term and the Spanish equivalent
                    type_conditions.extend([
                        Announcement.property_type.ilike(f"%{search_type}%"),
                        Announcement.property_type.ilike(f"%{spanish_type}%")
                    ])
                
                if type_conditions:
                    query = query.filter(db.or_(*type_conditions))
            
            # Feature filters
            if search_query.get('has_parking'):
                query = query.filter(Announcement.has_parking == True)
            if search_query.get('has_pool'):
                query = query.filter(Announcement.has_pool == True)
            if search_query.get('has_garden'):
                query = query.filter(Announcement.has_garden == True)
            if search_query.get('has_terrace'):
                query = query.filter(Announcement.has_terrace == True)
            if search_query.get('has_elevator'):
                query = query.filter(Announcement.has_elevator == True)
            if search_query.get('has_air_conditioning'):
                query = query.filter(Announcement.has_air_conditioning == True)
            
            # Location filter (if specified)
            if 'location' in search_query:
                location_name = search_query['location']
                query = query.join(Geoname).filter(Geoname.name.ilike(f"%{location_name}%"))
            
            # Get results
            properties = query.limit(limit).all()
            
            # Convert to dictionary format
            results = []
            for prop in properties:
                prop_dict = {
                    'id': prop.id,
                    'title': prop.title,
                    'description': prop.description,
                    'price': prop.price,
                    'rooms': prop.rooms,
                    'bathrooms': prop.number_of_bathrooms,
                    'square_meters': prop.square_meters,
                    'property_type': prop.property_type,
                    'location': prop.location.name if prop.location else 'Ubicación no especificada',
                    'has_parking': prop.has_parking,
                    'has_pool': prop.has_pool,
                    'has_garden': prop.has_garden,
                    'has_terrace': prop.has_terrace,
                    'has_elevator': prop.has_elevator,
                    'has_air_conditioning': prop.has_air_conditioning,
                    'images': [img.image_url for img in prop.images] if prop.images else []
                }
                results.append(prop_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching properties: {e}")
            return []
    
    def _search_vehicles(self, search_query: Dict, limit: int = 20) -> List[Dict]:
        """Search vehicles based on the query."""
        try:
            # Start with base query
            query = db.session.query(Vehicle).options(
                joinedload(Vehicle.make),
                joinedload(Vehicle.model),
                joinedload(Vehicle.category),
                joinedload(Vehicle.location)
            )
            
            # Apply filters
            if 'min_price' in search_query:
                query = query.filter(Vehicle.price >= search_query['min_price'])
            if 'max_price' in search_query:
                query = query.filter(Vehicle.price <= search_query['max_price'])
            
            if 'min_year' in search_query:
                query = query.filter(Vehicle.year >= search_query['min_year'])
            if 'max_year' in search_query:
                query = query.filter(Vehicle.year <= search_query['max_year'])
            
            if 'make' in search_query:
                make_name = search_query['make']
                query = query.join(VehicleMake).filter(VehicleMake.name.ilike(f"%{make_name}%"))
            
            if 'model' in search_query:
                model_name = search_query['model']
                query = query.join(VehicleModel).filter(VehicleModel.name.ilike(f"%{model_name}%"))
            
            if 'fuel_type' in search_query:
                fuel = search_query['fuel_type']
                fuel_mapping = {
                    'gasolina': 'Gasolina',
                    'diesel': 'Diesel',
                    'híbrido': 'Híbrido',
                    'hibrido': 'Híbrido',
                    'eléctrico': 'Eléctrico',
                    'electrico': 'Eléctrico',
                    'electric': 'Eléctrico',
                    'hybrid': 'Híbrido'
                }
                fuel_normalized = fuel_mapping.get(fuel.lower(), fuel)
                query = query.filter(Vehicle.fuel_type.ilike(f"%{fuel_normalized}%"))
            
            if 'transmission' in search_query:
                transmission = search_query['transmission']
                transmission_mapping = {
                    'manual': 'Manual',
                    'automática': 'Automática',
                    'automatica': 'Automática',
                    'automatic': 'Automática'
                }
                transmission_normalized = transmission_mapping.get(transmission.lower(), transmission)
                query = query.filter(Vehicle.transmission.ilike(f"%{transmission_normalized}%"))
            
            if 'category' in search_query:
                category_name = search_query['category']
                query = query.join(VehicleCategory).filter(VehicleCategory.name.ilike(f"%{category_name}%"))
            
            if 'condition' in search_query:
                condition = search_query['condition']
                query = query.filter(Vehicle.condition.ilike(f"%{condition}%"))
            
            if 'location' in search_query:
                location_name = search_query['location']
                query = query.join(Geoname).filter(Geoname.name.ilike(f"%{location_name}%"))
            
            # Get results
            vehicles = query.limit(limit).all()
            
            # Convert to dictionary format
            results = []
            for vehicle in vehicles:
                vehicle_dict = {
                    'id': vehicle.id,
                    'title': vehicle.title,
                    'description': vehicle.description,
                    'price': vehicle.price,
                    'make': vehicle.make.name if vehicle.make else '',
                    'model': vehicle.model.name if vehicle.model else '',
                    'year': vehicle.year,
                    'mileage': vehicle.mileage,
                    'fuel_type': vehicle.fuel_type,
                    'transmission': vehicle.transmission,
                    'category': vehicle.category.name if vehicle.category else '',
                    'condition': vehicle.condition,
                    'location': vehicle.location.name if vehicle.location else 'Ubicación no especificada',
                    'images': [img.image_url for img in vehicle.images] if vehicle.images else []
                }
                results.append(vehicle_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching vehicles: {e}")
            return []
    
    def _generate_response(self, user_message: str, search_criteria: Dict, properties: List[Dict]) -> str:
        """Generate a natural language response to the user."""
        if not properties:
            return "Lo siento, no he encontrado propiedades que coincidan con tus criterios. ¿Podrías ser más específico sobre lo que buscas?"
        
        # Count properties found
        property_count = len(properties)
        
        # Build response
        response_parts = []
        
        if property_count == 1:
            response_parts.append(f"¡Perfecto! He encontrado {property_count} propiedad que coincide con lo que buscas:")
        else:
            response_parts.append(f"¡Excelente! He encontrado {property_count} propiedades que coinciden con lo que buscas:")
        
        # Add criteria summary
        criteria_summary = []
        if 'min_price' in search_criteria or 'max_price' in search_criteria:
            if 'min_price' in search_criteria and 'max_price' in search_criteria:
                criteria_summary.append(f"precio entre {search_criteria['min_price']:,.0f}€ y {search_criteria['max_price']:,.0f}€")
            elif 'min_price' in search_criteria:
                criteria_summary.append(f"precio desde {search_criteria['min_price']:,.0f}€")
            elif 'max_price' in search_criteria:
                criteria_summary.append(f"precio hasta {search_criteria['max_price']:,.0f}€")
        
        if 'min_rooms' in search_criteria:
            criteria_summary.append(f"mínimo {search_criteria['min_rooms']} habitaciones")
        
        if 'min_bathrooms' in search_criteria:
            criteria_summary.append(f"mínimo {search_criteria['min_bathrooms']} baños")
        
        if 'min_square_meters' in search_criteria:
            criteria_summary.append(f"mínimo {search_criteria['min_square_meters']} m²")
        
        if 'location' in search_criteria:
            criteria_summary.append(f"en {search_criteria['location']}")
        
        if 'property_type' in search_criteria:
            criteria_summary.append(f"tipo {search_criteria['property_type']}")
        
        if criteria_summary:
            response_parts.append(f"Basándome en tus criterios: {', '.join(criteria_summary)}")
        
        # Add property highlights
        response_parts.append("\nAquí tienes algunas opciones:")
        
        for i, prop in enumerate(properties[:3], 1):  # Show first 3 properties
            price_str = f"{prop['price']:,.0f}€" if prop['price'] else "Precio no especificado"
            rooms_str = f"{prop['rooms']} hab." if prop['rooms'] else ""
            size_str = f"{prop['square_meters']} m²" if prop['square_meters'] else ""
            
            features = []
            if prop['has_parking']:
                features.append("parking")
            if prop['has_pool']:
                features.append("piscina")
            if prop['has_garden']:
                features.append("jardín")
            if prop['has_terrace']:
                features.append("terraza")
            
            features_str = f" ({', '.join(features)})" if features else ""
            
            response_parts.append(
                f"{i}. {prop['title']} - {price_str} {rooms_str} {size_str}{features_str} en {prop['location']}"
            )
        
        if property_count > 3:
            response_parts.append(f"\nY {property_count - 3} propiedades más...")
        
        response_parts.append("\n¿Te interesa alguna en particular? Puedo darte más detalles o ayudarte a refinar tu búsqueda.")
        
        return "\n".join(response_parts)
    
    def process_message(self, user_message: str, user_id: Optional[int] = None, conversation_history: List[Dict] = None) -> Dict:
        """
        Process a user message and return a response with property suggestions.
        
        Args:
            user_message: The user's message
            user_id: Optional user ID for conversation context
            conversation_history: List of previous conversation messages
        
        Returns:
            Dictionary with response and properties
        """
        try:
            # Initialize vectorizer if needed
            self._initialize_vectorizer()
            
            # Get or create conversation context
            if user_id and user_id not in self.conversation_context:
                self.conversation_context[user_id] = []
            
            # Add current message to conversation history
            if user_id:
                self.conversation_context[user_id].append({
                    "sender": "user",
                    "content": user_message,
                    "timestamp": datetime.utcnow()
                })
            
            # Get conversation history for context
            history = conversation_history or (self.conversation_context.get(user_id, []) if user_id else [])
            
            # Check if this is a greeting or initial message
            is_greeting = any(word in user_message.lower() for word in ['hola', 'hi', 'hello', 'buenas', 'buenos', 'hey'])
            is_initial = len(history) <= 1
            
            # Only search for properties if we have enough information or user explicitly asks for properties
            properties = []
            search_criteria = {}
            
            # Extract criteria intelligently (includes search_type detection)
            search_criteria = self._extract_search_criteria(user_message, history)
            
            # Determine search type
            search_type = search_criteria.get('search_type', 'unknown')
            
            # Fallback detection if search_type is unknown
            if search_type == 'unknown':
                vehicle_keywords = ['coche', 'auto', 'vehículo', 'vehiculo', 'carro', 'car', 'vehicle', 'toyota', 'bmw', 'mercedes', 
                                  'motocicleta', 'moto', 'suv', 'furgoneta', 'camión', 'camion']
                property_keywords = ['propiedad', 'casa', 'piso', 'apartamento', 'vivienda', 'inmueble', 'habitacion', 'habitación']
                
                message_lower = user_message.lower()
                has_vehicle_keywords = any(keyword in message_lower for keyword in vehicle_keywords)
                has_property_keywords = any(keyword in message_lower for keyword in property_keywords)
                
                if has_vehicle_keywords and not has_property_keywords:
                    search_type = 'vehicle'
                elif has_property_keywords:
                    search_type = 'property'
            
            # Determine if we have enough information to search
            has_enough_info = self._has_sufficient_search_info(search_criteria, history, search_type != 'unknown')
            
            # Only search if we have enough information
            results = []
            if has_enough_info:
                if search_type == 'vehicle':
                    # Build vehicle search query
                    vehicle_query = self._build_vehicle_search_query(search_criteria)
                    results = self._search_vehicles(vehicle_query, limit=20)
                else:  # property or unknown (default to property)
                    # Build property search query
                    search_query = self._build_search_query(search_criteria)
                    results = self._search_properties(search_query, limit=20)
                    
                    # If no properties found, try a more flexible search
                    if not results and search_criteria:
                        search_criteria['no_results'] = True
                        self._last_search_criteria = search_criteria
                        flexible_query = self._build_flexible_search_query(search_criteria)
                        results = self._search_properties(flexible_query, limit=10)
                        if results:
                            search_criteria['flexible_results'] = True
            
            # Generate response using OpenAI Assistant if available, otherwise fallback
            if self.openai_client:
                response = self._get_assistant_response(user_message, history, results, search_criteria)
            else:
                response = self._generate_fallback_response(user_message, results)
            
            # Add assistant response to conversation history
            if user_id:
                self.conversation_context[user_id].append({
                    "sender": "assistant",
                    "content": response,
                    "timestamp": datetime.utcnow()
                })
            
            return {
                'success': True,
                'response': response,
                'properties': results,  # Kept as 'properties' for backward compatibility with frontend
                'search_criteria': search_criteria,
                'property_count': len(results),
                'conversation_id': user_id
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'success': False,
                'response': "Lo siento, ha ocurrido un error. Por favor, intenta de nuevo.",
                'properties': [],
                'error': str(e)
            }
    
    def _build_vehicle_search_query(self, criteria: Dict) -> Dict:
        """Build a vehicle search query from extracted criteria."""
        query = {}
        
        # Price filters
        if 'min_price' in criteria:
            query['min_price'] = criteria['min_price']
        if 'max_price' in criteria:
            query['max_price'] = criteria['max_price']
        
        # Year filters
        if 'min_year' in criteria:
            query['min_year'] = criteria['min_year']
        if 'max_year' in criteria:
            query['max_year'] = criteria['max_year']
        
        # Make and Model
        if 'make' in criteria:
            query['make'] = criteria['make']
        if 'model' in criteria:
            query['model'] = criteria['model']
        
        # Fuel type
        if 'fuel_type' in criteria:
            query['fuel_type'] = criteria['fuel_type']
        
        # Transmission
        if 'transmission' in criteria:
            query['transmission'] = criteria['transmission']
        
        # Category
        if 'category' in criteria:
            query['category'] = criteria['category']
        
        # Condition
        if 'condition' in criteria:
            query['condition'] = criteria['condition']
        
        # Location
        if 'location' in criteria:
            query['location'] = criteria['location']
        
        return query
    
    def get_suggested_questions(self) -> List[str]:
        """Get suggested questions to help users start a conversation."""
        return [
            "¿Hola! ¿En qué puedo ayudarte hoy?",
            "¿Estás buscando una propiedad o un vehículo?",
            "Busco un piso de 2 habitaciones en Madrid",
            "Quiero un coche usado barato",
            "¿Qué tipo de propiedad te interesa?",
            "¿Qué marca de coche buscas?",
            "¿Cuál es tu presupuesto?"
        ]
