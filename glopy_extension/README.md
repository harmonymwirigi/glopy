# Glopy Extension - Universal Scraper with AI

Este repositorio contiene la extensión de Chrome para Glopy que permite **scrapear anuncios de cualquier sitio web** usando inteligencia artificial (OpenAI GPT-4) para detectar automáticamente los selectores CSS.

## 🎯 Tipos de Listados Soportados

- 🏠 **Inmuebles / Real Estate** - Propiedades, casas, apartamentos
- 🚗 **Vehículos / Automobiles** - Coches, motos, camiones

La extensión detecta automáticamente los campos relevantes para cada tipo y los envía a la API correspondiente de Glopy.

---

## 🔑 Acceso al Repositorio

> 📌 **Importante:** Este repositorio es **privado**. Para clonarlo necesitas:
- Tener una cuenta en GitHub.
- Tener permisos de acceso al repositorio.
- Estar logueado en GitHub (por HTTPS con token personal o por SSH con llave configurada).

---

## 🧭 Pasos para clonar e instalar el proyecto localmente

### 1️⃣ Crea una carpeta donde guardarás el proyecto (opcional pero recomendado)

Abre tu terminal (CMD, PowerShell, Terminal, etc.) y ejecuta:

```bash
mkdir proyectos
cd proyectos
```

⚠️ Si ves este error al intentar hacer un commit:

```bash
*** Please tell me who you are.

fatal: unable to auto-detect email address
```

✅ Solución: Ejecuta estos comandos para configurar tu nombre y correo:

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu-email@example.com"
```

## 🧩 Cómo cargar la extensión en Google Chrome

1. Abre Google Chrome
2. Ve a `chrome://extensions` en la barra de direcciones
3. Activa el **Modo desarrollador** (arriba a la derecha)
4. Haz clic en **"Cargar descomprimida"** o **"Load unpacked"**
5. Selecciona la carpeta `glopy_extension`

¡Listo! La extensión debería aparecer cargada.

📌 **Nota:** Si haces cambios en el código, deberás darle a "Actualizar" en la página de extensiones.

## 🚀 Cómo usar la extensión

1. **Abre la extensión** (click en el icono)
2. **Selecciona el tipo de listado:**
   - 🏠 Inmuebles / Real Estate
   - 🚗 Vehículos / Automobiles
3. **Navega** a una página de listados (ej: Idealista, Coches.net)
4. **Click en "Iniciar (Plan A)"**
5. **Observa** en la consola del navegador (F12) el progreso

La extensión automáticamente:
- ✅ Hace scroll hasta el final de la página
- ✅ Detecta selectores CSS con IA (primera vez)
- ✅ Guarda selectores en caché (siguientes veces son instantáneas)
- ✅ Extrae datos de cada anuncio
- ✅ Envía a la API de Glopy correspondiente
- ✅ Navega a la siguiente página automáticamente

## 📚 Documentación

- **[DUAL_MODE_GUIDE.md](./DUAL_MODE_GUIDE.md)** - Guía completa de uso
- **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)** - Detalles técnicos de implementación

🧠 Notas adicionales
Si quieres hacer cambios en la extensión, trabaja en una rama nueva:

```bash
git checkout -b nombre-de-tu-rama origin/nombre-de-tu-rama
```

Esta extensión solo funcionará en Chrome (o navegadores compatibles con extensiones tipo Chrome como Edge).
