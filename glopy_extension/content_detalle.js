/******************************************************
 * content_detalle.js
 * Inyectado en la pestaña de DETALLE (el anuncio).
 * Extrae la info relevante (texto, imágenes, etc.)
 * y la manda al background (mensaje type: 'adDetailExtracted').
 ******************************************************/


setTimeout(async () => {
  console.log('[content_detalle] Esperando carga dinámica');
  await scrollToEnd();
  const domain = window.location.hostname;
  const entireHtml = document.body.outerHTML;
  const fullPageText = document.body.innerText;
  //Calculamos el punto de corte para el 75%.
  const cutoffIndex = Math.floor(fullPageText.length * 0.75);
  const top75PercentText = fullPageText.slice(0, cutoffIndex);
  chrome.runtime.sendMessage({
    type: 'extractAdInfo',
    domain,
    url: location.href,
    entireHtml,
    entirePageText: top75PercentText
  }, (response) => {
    console.log('[content_detalle] Resultado extraído:', response);
  });
}, 3000); // 

/**
 * Hace scroll progresivo hasta el final de la página,
 * deteniéndose cuando la altura del body deja de crecer.
 */
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

