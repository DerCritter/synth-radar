import os
import sys
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    import google.generativeai as genai
except ImportError:
    logging.error("google-generativeai not installed")
    sys.exit(1)

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    logging.error("GEMINI_API_KEY environment variable is required")
    sys.exit(1)

genai.configure(api_key=API_KEY)

# Initialise model
model = genai.GenerativeModel('gemini-2.5-pro')

prompt = """
Escribe un artículo de blog atractivo (en español) sobre un sintetizador retro, caja de ritmos clásica o módulo eurorack famoso.
El artículo debe estar optimizado para SEO, buscando atraer a músicos, productores y coleccionistas que buscan comprar equipos de segunda mano.
El objetivo es que los lectores aterricen en el blog y luego hagan clic para ver las "Ofertas del día" en nuestra herramienta SynthRadar.
Estructura:
1. Título principal en <h1> (llamativo).
2. Introducción histórica.
3. Por qué es relevante hoy en día en la producción musical.
4. Una sección de "Alternativas modernas" o "¿Vale la pena comprarlo de segunda mano?".
5. Al final, un pequeño "Call to Action" invitando a usar SynthRadar para encontrar el mejor precio.

Devuelve el resultado ÚNICAMENTE en código HTML válido (sin etiquetas ```html ni head/body, solo el contenido interior que irá en el contenedor principal).
Usa clases CSS bonitas genéricas si es necesario.
"""

logging.info("Generating blog content using Gemini...")
try:
    response = model.generate_content(prompt)
    content = response.text.strip()
    
    # Remove markdown code blocks if present
    if content.startswith("```html"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
        
    date_str = datetime.now().strftime("%d de %B de %Y")
    
    # Create the blog post wrap
    full_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SynthRadar Blog | Retro Synths</title>
        <link rel="stylesheet" href="style.css">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    </head>
    <body class="dark-mode">
        <nav class="sticky-header">
            <div class="logo">SynthRadar Blog</div>
            <a href="index.html" class="btn btn-primary">Volver al Radar</a>
        </nav>
        <main class="blog-container">
            <article class="blog-post">
                <div class="blog-meta">Publicado el {date_str}</div>
                {content}
            </article>
        </main>
    </body>
    </html>
    """
    
    with open("blog.html", "w") as f:
        f.write(full_html)
        
    logging.info("blog.html generated successfully.")
except Exception as e:
    logging.error(f"Error generating blog: {e}")
    sys.exit(1)
