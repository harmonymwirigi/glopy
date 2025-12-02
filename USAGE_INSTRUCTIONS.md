# GLOPY EXTENSION - USAGE INSTRUCTIONS

## 🚨 CRITICAL: Select Correct Listing Type!

### Before Scraping ANY Website:

**YOU MUST SELECT THE CORRECT TYPE IN THE EXTENSION POPUP!**

---

## 📋 Step-by-Step Instructions

### For Vehicle Websites (cars.com, autabuy.com, coches.net, etc.):

1. **Navigate to the vehicle listing page**
   - Example: https://www.cars.com/shopping/results/

2. **Open Glopy extension popup** (click icon)

3. **SELECT: 🚗 Vehículos / Automobiles** ← CRITICAL!

4. **Click "Start" button**

5. **Watch console logs** (F12):
   ```
   ✅ 🎯 TIPO DE LISTADO ACTUAL: VEHICLES  ← Should say VEHICLES!
   ✅ 📍 Dominio: www.cars.com
   ✅ ✅ Extracted year from title: 2025
   ✅ ✅ Extracted make from title: Tesla
   ```

---

### For Real Estate Websites (idealista.com, fotocasa.es, etc.):

1. **Navigate to the property listing page**

2. **Open Glopy extension popup**

3. **SELECT: 🏠 Inmuebles / Real Estate** ← CRITICAL!

4. **Click "Start" button**

5. **Watch console logs**:
   ```
   ✅ 🎯 TIPO DE LISTADO ACTUAL: INMUEBLES
   ✅ Extracted property data...
   ```

---

## ⚠️ Common Mistakes

### ❌ MISTAKE #1: Wrong Type Selected
```
Scraping: cars.com (vehicles)
Selected: Inmuebles (real estate) ← WRONG!

Result: All fields = null, API rejects data
```

**FIX**: Select "Vehículos" before clicking Start!

---

### ❌ MISTAKE #2: Not Reloading After Type Change
```
1. Selected "Inmuebles"
2. Started scraping
3. Stopped and selected "Vehículos"
4. Started again
Result: Still using old type!
```

**FIX**: Reload the target page after changing type!

---

## 🔍 How to Verify Correct Type

### Check Console Logs:

**For Vehicles (cars.com, autabuy.com):**
```javascript
✅ 🎯 TIPO DE LISTADO ACTUAL: VEHICLES  ← Must say VEHICLES!
✅ 🚗 Preparando payload para vehículo...
✅ 📡 Enviando vehicles a .../api/vehicles...
```

**For Real Estate (idealista.com):**
```javascript
✅ 🎯 TIPO DE LISTADO ACTUAL: INMUEBLES  ← Must say INMUEBLES!
✅ 🏠 Preparando payload para inmueble...
✅ 📡 Enviando inmuebles a .../api/inmuebles...
```

---

## 🎯 Quick Reference Table

| Website Type | Select in Popup | API Endpoint | Expected Fields |
|--------------|-----------------|--------------|-----------------|
| cars.com | 🚗 Vehículos | `/api/vehicles` | make, model, year |
| autabuy.com | 🚗 Vehículos | `/api/vehicles` | make, model, year |
| coches.net | 🚗 Vehículos | `/api/vehicles` | make, model, year |
| idealista.com | 🏠 Inmuebles | `/api/inmuebles` | rooms, sqm, type |
| fotocasa.es | 🏠 Inmuebles | `/api/inmuebles` | rooms, sqm, type |

---

## 🐛 Troubleshooting

### Issue: "All fields are null"

**Check:**
1. Is the correct type selected? (Vehículos for cars, Inmuebles for properties)
2. Did you reload the page after changing type?
3. Check console: Does it say the correct "TIPO DE LISTADO"?

**Fix:**
1. Reload the target page
2. Open extension popup
3. Select correct type
4. Click Start

---

### Issue: "API rejects data - 'title' is required"

**This means:**
- Fields were not extracted (all null)
- Usually because wrong type is selected

**Fix:**
- Verify type selection in popup
- Make sure console shows correct type
- Reload page and try again

---

### Issue: "Comparing Audi with Volkswagen"

**This means:**
- Data was extracted correctly
- Deduplication is working!
- Pre-filtering prevents false matches

**Expected:**
```
✅ Pre-filtering: 100 total vehicles → 3 candidates
✅ Comparing with Audi A-5 2012: 93%
```

---

## 💡 Pro Tips

1. **Always check console first**: Look for "TIPO DE LISTADO ACTUAL"
2. **Reload after type change**: Extension needs fresh page load
3. **Test with single listing first**: Don't run full scrape until verified
4. **Watch for "intelligentDataParsing"**: Should see year/make extraction logs

---

## ✅ Success Indicators

When everything is working correctly, you'll see:

```javascript
🔍 Running intelligent data parsing...
📝 Title: 2025 Tesla Model 3 Long Range
✅ Extracted year from title: 2025
✅ Extracted make from title: Tesla
✅ Extracted model from title: Model 3 Long Range
✅ Cleaned price: $37985
✨ Parsed data: {year: 2025, make: "Tesla", model: "Model 3 Long Range", ...}
📡 Enviando vehicles a http://127.0.0.1:5001/api/vehicles...
✅ Vehicle created successfully!
```

---

## 📞 Still Having Issues?

If you're still getting null fields after:
1. ✅ Selected correct type
2. ✅ Reloaded page
3. ✅ Console shows correct "TIPO DE LISTADO"

Then the AI might have detected wrong selectors. Check the documentation or clear cache and try again.

---

**Remember**: The most common mistake is forgetting to select the correct listing type before clicking Start!
