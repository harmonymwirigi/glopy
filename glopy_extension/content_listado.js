/******************************************************
 * content_listado.js
 * Inyectado en la página LISTADO de anuncios:
 *   1) Scrollear hasta el final
 *   2) Tomar el HTML completo
 *   3) Pedir al background el selector (pasándole el HTML)
 *   4) Recoger URLs de anuncios y enviarlos al background
 ******************************************************/


async function startScrapingFlow() {
  await scrollToEnd();
  console.log('Scrolling al final completado.');

  const domain = window.location.hostname;
  const entireHtml = document.body.outerHTML;

  chrome.runtime.sendMessage({
    type: 'getSelectorForDomain',
    domain,
    entireHtml: entireHtml
  }, async (resp) => {
    if (chrome.runtime.lastError || !resp || !resp.selector) {
      console.error('❌ Error pidiendo selectores o respuesta inválida:', chrome.runtime.lastError || 'Respuesta vacía');
      console.error('📋 Asegúrate de haber seleccionado el tipo correcto en el popup (🏠 Inmuebles o 🚗 Vehículos)');
      return;
    }

    console.log('📦 Selectores recibidos del background:', resp.selector);

    // Ahora 'resp.selector' es el objeto que contiene todos nuestros selectores
    const { selectorGeneral, titulo: selectorTitulo, precio: selectorPrecio, logo } = resp.selector;
    const selectorContenedor = selectorGeneral;

    if (!selectorContenedor || !selectorTitulo || !selectorPrecio) {
      console.error('❌ FALTAN SELECTORES CLAVE. La IA no pudo detectarlos.');
      console.error('📋 Selectores recibidos:', resp.selector);
      console.error('🔧 Soluciones:');
      console.error('   1. Verifica que estás en una página de LISTADOS (no de detalle)');
      console.error('   2. Usa "🗑 Resetear dominio actual" en el popup');
      console.error('   3. Intenta de nuevo - la IA aprenderá mejor en el segundo intento');
      console.error('   4. Este sitio web podría tener una estructura muy compleja');
      return;
    }

    console.log(`Selectores obtenidos y validados:`, { selectorContenedor, selectorTitulo, selectorPrecio });

    const logoUrl = getLogo(logo);
    chrome.runtime.sendMessage({ type: 'logoExtracted', logoUrl });

    const adElements = document.querySelectorAll(selectorContenedor);
    console.log(`Encontrados ${adElements.length} anuncios con el selector contenedor.`);

    const anunciosConDatos = [];
    adElements.forEach((contenedor, index) => {
      const linkElement = contenedor.querySelector('a[href]');
      const tituloElement = contenedor.querySelector(selectorTitulo);
      const precioElement = contenedor.querySelector(selectorPrecio);

      if (linkElement && tituloElement && precioElement) {
        const anuncio = {
          link: linkElement.href,
          titulo: tituloElement.innerText.trim(),
          precio: precioElement.innerText.trim()
        };
        anunciosConDatos.push(anuncio);
      } else {
        console.warn(`Anuncio ${index + 1} omitido por falta de datos.`);
      }
    });

    console.log(`Se han procesado ${anunciosConDatos.length} anuncios con datos completos.`);

    if (anunciosConDatos.length > 0) {
      chrome.runtime.sendMessage({ type: 'processUrlsList', anuncios: anunciosConDatos });
    }
  });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'clickNextAndScrapeAgain') {
    console.log('🔁 Mensaje recibido: clickNextAndScrapeAgain');

    const domain = window.location.hostname;

    chrome.storage.local.get(['domainInstructions'], async (res) => {
      const instrucciones = res.domainInstructions || {};
      const botonSelector = instrucciones[domain]?.boton_siguiente;

      if (!botonSelector) {
        console.warn('❌ No hay botón_siguiente definido en storage. Finalizando ciclo.');
        return;
      }

      const boton = document.querySelector(botonSelector);
      if (boton) {
        console.log('➡️ Haciendo click en el botón "Siguiente" para iniciar la recarga...');
        boton.scrollIntoView({ behavior: 'smooth', block: 'center' });
        boton.click();
        // NADA MÁS. El script ha cumplido su misión. La recarga de la página lo destruirá.
        // El background se encargará de reinyectarlo.
      } else {
        console.warn('⚠️ Botón "Siguiente" no encontrado en la página. Finalizando ciclo.');
      }
    });
  }
});


/**
 * Hace scroll progresivo hasta el final de la página,
 * deteniéndose cuando la altura del body deja de crecer.
 */

function getLogo(logo){
  const logoEl = document.querySelector(logo); // 'logo' es el selector

  let logoUrl = null;

  if (logoEl) {
    if (logoEl.tagName.toLowerCase() === 'img') {
      // Si es una etiqueta <img>, saca el src
      logoUrl = logoEl.src || logoEl.getAttribute('src');
    } else if (logoEl.tagName.toLowerCase() === 'a') {
      // Si es un <a>, saca el href
      logoUrl = logoEl.href || logoEl.getAttribute('href');
    } else {
      // Busca si dentro tiene una <img> o <a>
      const innerImg = logoEl.querySelector('img');
      const innerLink = logoEl.querySelector('a');
      if (innerImg) {
        logoUrl = innerImg.src || innerImg.getAttribute('src');
      } else if (innerLink) {
        logoUrl = innerLink.href || innerLink.getAttribute('href');
      }
    }
  }

  if (logoUrl) {
    console.log("✅ Logo URL extraído:", logoUrl);
  } else {
    console.warn("❌ No se pudo extraer el logo.");
  }
  return logoUrl
}

    

async function scrollToEnd() {
  let posicionActual = 0;
  let alturaAnterior = 0;
  const pasoPx = 800;
  const tiempoEspera = 1000;

  while (true) {
    posicionActual += pasoPx;
    const alturaTotal = document.body.scrollHeight;
    if (posicionActual > alturaTotal) {
      posicionActual = alturaTotal;
    }

    window.scrollTo(0, posicionActual);
    await esperar(tiempoEspera);

    const nuevaAltura = document.body.scrollHeight;
    // Si la altura no crece más y hemos llegado al final, paramos.
    if (nuevaAltura === alturaAnterior && posicionActual >= nuevaAltura) {
      break;
    }
    alturaAnterior = nuevaAltura;
  }
  console.log('Scrolling completo hasta el final.');
}

/**
 * Función auxiliar de espera en milisegundos.
 */
function esperar(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

