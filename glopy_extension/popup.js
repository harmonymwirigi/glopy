document.addEventListener('DOMContentLoaded', () => {
    const btnStart = document.getElementById('btnStart');
    const btnDisable = document.getElementById('btnDisable');
    const btnShowStorage = document.getElementById('btnShowStorage');
  
    // Activa la extensión y arranca el flujo en la pestaña actual
    btnStart.addEventListener('click', () => {
      // ACTUALIZADO: Obtener el tipo de listado seleccionado
      const listingTypeSelect = document.getElementById('listingType');
      const selectedListingType = listingTypeSelect.value;
      
      console.log(`🎯 Tipo seleccionado: ${selectedListingType}`);
      
      // 1) Habilitar la extensión en background con el tipo de listado
      chrome.runtime.sendMessage({ 
        type: 'enableExtension',
        listingType: selectedListingType 
      }, (resp) => {
        console.log('Respuesta al habilitar extensión:', resp);
  
        // 2) Inyecta (o reinyecta) el script de LISTADO en la pestaña activa
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (!tabs || !tabs[0]) {
            console.warn('No hay pestaña activa');
            return;
          }
          const tabId = tabs[0].id;
  
          // Inyectar content_listado.js
          chrome.scripting.executeScript({
            target: { tabId },
            files: ['content_listado.js']
          }, () => {
            // 3) Ejecutar la función startScrapingFlow() en el contexto de la pestaña
            chrome.scripting.executeScript({
              target: { tabId },
              func: () => {
                startScrapingFlow();
              }
            });
          });
        });
      });
    });
  
    // Deshabilita la extensión
    btnDisable.addEventListener('click', () => {
      chrome.runtime.sendMessage({ type: 'disableExtension' }, (resp) => {
        console.log('Extensión deshabilitada:', resp);
      });
    });
  
    // Muestra el contenido de chrome.storage (dominio->selector)
    btnShowStorage.addEventListener('click', () => {
      chrome.storage.local.get(null, (res) => {
        const instrucciones = res.domainInstructions || {};
    
        // ACTUALIZADO: Buscar claves que empiecen por "fieldSelectors_" con tipo
        const fieldSelectorsPorDominio = {};
        
        Object.keys(res).forEach(key => {
          if (key.startsWith('fieldSelectors_')) {
            // Extraer tipo y dominio: fieldSelectors_vehicles_example.com
            const parts = key.replace('fieldSelectors_', '').split('_');
            const tipo = parts[0]; // vehicles o inmuebles
            const dominio = parts.slice(1).join('_');
            
            if (!fieldSelectorsPorDominio[dominio]) {
              fieldSelectorsPorDominio[dominio] = {};
            }
            fieldSelectorsPorDominio[dominio][tipo] = res[key];
          }
        });
    
        // Crear un objeto combinado y legible
        const resumen = {};
    
        for (const dominio in fieldSelectorsPorDominio) {
          const tipos = fieldSelectorsPorDominio[dominio];
          resumen[dominio] = {};
          
          for (const tipo in tipos) {
            const campos = tipos[tipo] || {};
            const primeros5Campos = Object.keys(campos)
              .slice(0, 5)
              .reduce((obj, key) => {
                obj[key] = campos[key];
                return obj;
              }, {});
              
            resumen[dominio][tipo] = {
              camposExtraidos: primeros5Campos,
              totalCampos: Object.keys(campos).length
            };
          }
        }
    
        // Agregar también domainInstructions (selectores generales)
        if (Object.keys(instrucciones).length > 0) {
          resumen['_domainInstructions'] = instrucciones;
        }
    
        // Mostrarlo ordenado y legible
        alert("📦 Storage actual:\n\n" + JSON.stringify(resumen, null, 2));
      });
    });
    
  });

document.getElementById('btnResetDomain').addEventListener('click', () => {
  // 1. Obtener el dominio de la pestaña activa
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs || !tabs[0] || !tabs[0].url) {
      alert('No se pudo obtener la pestaña activa o su URL.');
      return;
    }

    try {
      const url = new URL(tabs[0].url);
      const domain = url.hostname;

      // ACTUALIZADO: Construir claves para ambos tipos
      const fieldSelectorsKeyInmuebles = `fieldSelectors_inmuebles_${domain}`;
      const fieldSelectorsKeyVehicles = `fieldSelectors_vehicles_${domain}`;

      // 3. Obtener los datos actuales del storage
      chrome.storage.local.get(['domainInstructions', fieldSelectorsKeyInmuebles, fieldSelectorsKeyVehicles], (res) => {
        if (chrome.runtime.lastError) {
          alert('Error al leer el storage: ' + chrome.runtime.lastError.message);
          return;
        }
        
        const updatedInstructions = { ...res.domainInstructions };

        // 4. Eliminar las propiedades del objeto de selectores generales
        delete updatedInstructions[domain];

        // 5. Preparar la lista de claves a eliminar (ambos tipos)
        const keysToRemove = [fieldSelectorsKeyInmuebles, fieldSelectorsKeyVehicles];
        
        // 6. Guardar el objeto de selectores generales actualizado Y eliminar las claves de campos
        chrome.storage.local.set({
          domainInstructions: updatedInstructions
        }, () => {
          // Una vez guardado, procedemos a eliminar las otras claves
          chrome.storage.local.remove(keysToRemove, () => {
            if (chrome.runtime.lastError) {
              alert('Error al limpiar los selectores de campos: ' + chrome.runtime.lastError.message);
            } else {
              alert(`🧹 Reset completado para: ${domain}\n\nSe han eliminado los selectores de inmuebles y vehículos.`);
              console.log(`✅ Selectores eliminados para ${domain} (inmuebles y vehicles)`);
            }
          });
        });
      });
    } catch (e) {
      alert('La URL de la pestaña actual no es válida. Intenta en una página web normal.');
    }
  });
});
  