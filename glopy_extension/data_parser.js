/**
 * DATA PARSER - Intelligent Data Extraction and Validation
 *
 * Fixes common scraping errors by parsing titles and validating extracted fields.
 * Use this BEFORE sending data to the API.
 */

/**
 * Intelligently parse and validate vehicle/property data extracted from the page.
 * Fixes common extraction errors like wrong fields, missing data, etc.
 * @param {object} rawData - The raw extracted data from selectors
 * @param {string} title - The listing title (most reliable source)
 * @param {string} fullPageText - Full page text for fallback extraction
 * @returns {object} Cleaned and validated data
 */
function intelligentDataParsing(rawData, title, fullPageText = '') {
    const cleaned = {...rawData};
    title = title || '';

    console.log('🔍 Starting intelligent data parsing...');
    console.log('📝 Title:', title);
    console.log('📊 Raw data:', rawData);

    // ===== YEAR EXTRACTION =====
    // Extract year from title (most reliable): "2012 Audi A5" -> 2012
    if (!cleaned.year || String(cleaned.year).length > 4 || isNaN(cleaned.year)) {
        const yearMatch = title.match(/\b(19|20)\d{2}\b/);
        if (yearMatch) {
            cleaned.year = parseInt(yearMatch[0]);
            console.log(`✅ Extracted year from title: ${cleaned.year}`);
        } else {
            cleaned.year = null;
        }
    }

    // ===== MAKE EXTRACTION =====
    // If make is null, a number, or looks wrong, extract from title
    if (!cleaned.make || /^\d+$/.test(cleaned.make) || cleaned.make.toLowerCase().includes('mileage')) {
        const knownMakes = [
            'Audi', 'BMW', 'Mercedes', 'Volkswagen', 'Toyota', 'Honda', 'Ford', 'Chevrolet',
            'Nissan', 'Mazda', 'Hyundai', 'Kia', 'Lexus', 'Jeep', 'Dodge', 'Ram', 'GMC',
            'Subaru', 'Volvo', 'Porsche', 'Tesla', 'Land Rover', 'Acura', 'Infiniti',
            'Lincoln', 'Cadillac', 'Buick', 'Chrysler', 'Jaguar', 'Maserati', 'Bentley',
            'Rolls Royce', 'Ferrari', 'Lamborghini', 'McLaren', 'Aston Martin', 'Alfa Romeo',
            'Genesis', 'MINI', 'Smart', 'Fiat', 'Mitsubishi', 'Suzuki', 'Isuzu', 'Peugeot',
            'Renault', 'Citroen', 'Seat', 'Skoda', 'Opel', 'Vauxhall'
        ];

        for (const make of knownMakes) {
            if (title.toLowerCase().includes(make.toLowerCase())) {
                cleaned.make = make;
                console.log(`✅ Extracted make from title: ${cleaned.make}`);
                break;
            }
        }
    }

    // ===== MODEL EXTRACTION =====
    // Extract model from title after make
    if ((!cleaned.model || /^\d+$/.test(cleaned.model)) && cleaned.make) {
        const titleLower = title.toLowerCase();
        const makeIndex = titleLower.indexOf(cleaned.make.toLowerCase());

        if (makeIndex !== -1) {
            // Get text after make
            const afterMake = title.substring(makeIndex + cleaned.make.length).trim();
            // Take first 1-3 words as model (before price, year, or other details)
            const modelMatch = afterMake.match(/^([A-Za-z0-9\-]+(?:\s+[A-Za-z0-9\-]+){0,2})/);
            if (modelMatch) {
                let modelName = modelMatch[1].trim();
                // Clean up model name (remove year, mileage, price indicators)
                modelName = modelName.replace(/\b(19|20)\d{2}\b/, '').trim();
                modelName = modelName.replace(/\b\d+K\b/i, '').trim(); // Remove "46K"
                modelName = modelName.replace(/\b(Miles?|Km|Kilometers?)\b/i, '').trim();
                modelName = modelName.split(/\s+(Price|For|Sale|Offered)/i)[0].trim();

                if (modelName && modelName.length > 0) {
                    cleaned.model = modelName;
                    console.log(`✅ Extracted model from title: ${cleaned.model}`);
                }
            }
        }
    }

    // ===== PRICE CLEANING =====
    // Clean price: remove $, €, £, commas, whitespace
    if (cleaned.price && typeof cleaned.price === 'string') {
        const priceMatch = cleaned.price.match(/[\d,]+(?:\.\d{2})?/);
        if (priceMatch) {
            cleaned.price = parseFloat(priceMatch[0].replace(/,/g, ''));
            console.log(`✅ Cleaned price: $${cleaned.price}`);
        }
    }

    // ===== MILEAGE CLEANING =====
    // Clean mileage: remove "km", "miles", commas, non-numeric text
    if (cleaned.mileage && typeof cleaned.mileage === 'string') {
        // Remove everything except numbers and commas
        const mileageMatch = cleaned.mileage.match(/[\d,]+/);
        if (mileageMatch) {
            cleaned.mileage = parseInt(mileageMatch[0].replace(/,/g, ''));
            console.log(`✅ Cleaned mileage: ${cleaned.mileage}`);
        } else {
            cleaned.mileage = null;
        }
    }

    // ===== COLOR VALIDATION =====
    // If color contains "mileage", "price", "year", or numbers, it's wrong
    if (cleaned.color && /mileage|price|year|\d{3,}/i.test(cleaned.color)) {
        console.warn(`⚠️ Invalid color detected: "${cleaned.color}" - setting to null`);
        cleaned.color = null;
    }

    // ===== TRANSMISSION VALIDATION =====
    // Validate transmission is one of: Manual, Automatic, Semi-Automatic, CVT
    if (cleaned.transmission && !/automatic|manual|semi|cvt/i.test(cleaned.transmission)) {
        console.warn(`⚠️ Invalid transmission detected: "${cleaned.transmission}" - setting to null`);
        cleaned.transmission = null;
    }

    // ===== LOCATION CLEANING =====
    // If location contains "price", "sale", "offered", it's seller info, not location
    if (cleaned.location && /price|sale|offered|call|mention/i.test(cleaned.location)) {
        console.warn(`⚠️ Invalid location detected (contains seller info): "${cleaned.location}"`);
        // Try to extract actual location from title or page text
        const locationMatch = title.match(/\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+([A-Z]{2})\b/);
        if (locationMatch) {
            cleaned.location = `${locationMatch[1]}, ${locationMatch[2]}`;
            console.log(`✅ Extracted location from title: ${cleaned.location}`);
        } else {
            cleaned.location = null;
        }
    }

    // ===== FUEL TYPE VALIDATION =====
    // Standardize fuel type
    if (cleaned.fuel_type) {
        const fuelTypes = {
            'Gasoline': ['gasoline', 'petrol', 'gas'],
            'Diesel': ['diesel'],
            'Electric': ['electric', 'ev', 'battery'],
            'Hybrid': ['hybrid', 'plug-in'],
            'Other': ['lpg', 'cng', 'hydrogen']
        };

        const fuelLower = cleaned.fuel_type.toLowerCase();
        for (const [standard, variants] of Object.entries(fuelTypes)) {
            if (variants.some(v => fuelLower.includes(v))) {
                cleaned.fuel_type = standard;
                break;
            }
        }
    }

    // ===== CONDITION STANDARDIZATION =====
    if (cleaned.condition) {
        if (/new|nuevo|neuf/i.test(cleaned.condition)) {
            cleaned.condition = 'New';
        } else if (/used|segundo|occasion|pre-owned/i.test(cleaned.condition)) {
            cleaned.condition = 'Used';
        }
    }

    // ===== FEATURES EXTRACTION =====
    // Extract key features from title if not already present
    if (!cleaned.features && title.toLowerCase().includes('low mile')) {
        cleaned.features = 'Low Miles';
        console.log(`✅ Extracted features from title: ${cleaned.features}`);
    }

    console.log('✨ Data after intelligent parsing:', {
        year: cleaned.year,
        make: cleaned.make,
        model: cleaned.model,
        price: cleaned.price,
        mileage: cleaned.mileage,
        color: cleaned.color,
        transmission: cleaned.transmission,
        fuel_type: cleaned.fuel_type,
        condition: cleaned.condition,
        location: cleaned.location,
        features: cleaned.features
    });

    return cleaned;
}

// Export for use in background.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { intelligentDataParsing };
}
