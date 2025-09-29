import logging
import asyncio
import time # Importar el módulo time
from typing import List, Dict
from pydantic import ValidationError
from publishers.supabase_client import SupabaseClient, Article
from scrapers.anti_detection import AntiDetectionScraper
from ai_orchestrator.consensus_engine import AIOrchestrator, OrchestratorConfig, REAL_CONFIG_DICT
from ai_orchestrator.prompt_optimizer import PromptOptimizer # Importar PromptOptimizer
from trends_analyzer import TrendsAnalyzer # Importar TrendsAnalyzer
from utils.resilient_image_fetcher import ResilientImageFetcher # Importar ResilientImageFetcher
from scrapers.video_processor import YouTubeProcessor, YOUTUBE_SOURCES # Importar video processor
from utils.quality_controller import QualityController # Importar QualityController

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def process_video_content(video_data, youtube_processor, supabase_client, ai_orchestrator, quality_controller):
    """Convierte video en artículo escrito"""
    logging.info(f"Procesando video: {video_data['title']}")

    # Obtener transcript
    transcript = youtube_processor.get_video_transcript(video_data['video_id'])
    content_for_ia = transcript or video_data['description']

    # Generar artículo basado en el video
    prompt = f"""
    Convierte este contenido de video en un artículo escrito de 800-1200 palabras:

    TÍTULO: {video_data['title']}
    DESCRIPCIÓN: {video_data['description']}
    CONTENIDO: {content_for_ia[:3000]}

    Crea un artículo bien estructurado que capture las ideas principales del video.
    """

    ai_content = await ai_orchestrator.get_consensus(prompt)

    if ai_content:
        passes_quality, quality_report = quality_controller.analyze_content_quality(ai_content, video_data['title'])

        if passes_quality:
            # Guardar como artículo
            article = Article(
                title=video_data['title'],
                url=video_data['url'],
                content=ai_content,
                source=f"YouTube - {video_data['channel_title']}",
                image_url=video_data['thumbnail'],
                quality_score=quality_report['metrics']['readability_score'] # Usar readability como score inicial
            )

            is_new = supabase_client.save_article(article)
            if is_new:
                logging.info(f"Video convertido a artículo: {video_data['title']} (Calidad: {quality_report['metrics']['readability_score']:.2f})")
        else:
            logging.warning(f"Contenido de video para '{video_data['title']}' no pasó el control de calidad: {quality_report['issues']}")

# --- BIBLIOTECA DE CONTENIDO ---
CONTENT_SOURCES: List[Dict[str, str]] = [
    # --- NOTICIAS IA (Actuales) ---
    {"type": "rss", "category": "noticias_ia", "name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"type": "rss", "category": "reviews_tech", "name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},

    # --- BLOGS OFICIALES IA ---
    {"type": "rss", "category": "ai_research", "name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"},
    {"type": "rss", "category": "ai_research", "name": "OpenAI Blog", "url": "https://openai.com/index.xml"},
    {"type": "rss", "category": "ai_research", "name": "Microsoft AI Blog", "url": "https://blogs.microsoft.com/ai/feed/", "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"}},
    {"type": "rss", "category": "ai_research", "name": "Meta AI Blog", "url": "https://ai.meta.com/blog/feed/"},

    # --- MEDIOS TECNOLÓGICOS ---
    {"type": "rss", "category": "tech_news", "name": "Wired AI", "url": "https://www.wired.com/feed/category/science/ai/latest-rss/"},
    {"type": "rss", "category": "business_ai", "name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
    {"type": "rss", "category": "ai_news", "name": "Artificial Intelligence News", "url": "https://www.artificialintelligence-news.com/feed/"},

    # --- BLOGS TÉCNICOS ---
    {"type": "rss", "category": "developer_ai", "name": "Towards Data Science", "url": "https://towardsdatascience.com/feed"},
    {"type": "rss", "category": "machine_learning", "name": "Machine Learning Mastery", "url": "https://machinelearningmastery.com/blog/feed/"},
    {"type": "rss", "category": "ai_trends", "name": "AI Trends", "url": "https://www.aitrends.com/feed/"},

    # --- MEDIOS INTERNACIONALES ---
    {"type": "rss", "category": "ai_ethics", "name": "MIT Technology Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/"},
    {"type": "rss", "category": "tech_analysis", "name": "Ars Technica AI", "url": "https://feeds.arstechnica.com/arstechnica/index/"},

    # --- NICHOS ESPECÍFICOS ---
    {"type": "rss", "category": "ai_business", "name": "Forbes AI", "url": "https://www.forbes.com/ai/feed/"},
    {"type": "rss", "category": "ai_health", "name": "AI in Healthcare", "url": "https://www.healthcareitnews.com/topic/artificial-intelligence/feed"}
]

# --- SISTEMA DE PLANTILLAS DE CONTENIDO ---
CONTENT_TEMPLATES = {
    "tutorial": """
    ESTRUCTURA: Problema → Solución → Implementación → Resultados
    TONO: Instructivo, paso a paso
    """,
    "análisis": """
    ESTRUCTURA: Tesis → Evidencia → Análisis → Conclusión
    TONO: Analítico, basado en datos
    """,
    "noticia": """
    ESTRUCTURA: Qué → Quién → Cuándo → Por qué → Impacto
    TONO: Informativo, objetivo
    """
}


# --- SISTEMA DE PERSONALIZACIÓN POR AUDIENCIA ---
AUDIENCE_PROFILES = {
    "principiante_desarrollador": {
        "nivel_tecnico": "Principiante",
        "objetivo_lector": "Desarrollador",
        "instrucciones_adicionales": "Usa explicaciones simples, evita la jerga técnica compleja, enfócate en los primeros pasos y ejemplos de código básicos."
    },
    "intermedio_desarrollador": {
        "nivel_tecnico": "Intermedio",
        "objetivo_lector": "Desarrollador",
        "instrucciones_adicionales": "Balancea la profundidad técnica con la practicidad, incluye ejemplos de código moderados y discute patrones de diseño."
    },
    "avanzado_desarrollador": {
        "nivel_tecnico": "Avanzado",
        "objetivo_lector": "Desarrollador",
        "instrucciones_adicionales": "Profundiza en detalles técnicos, arquitectura, optimización y patrones de código complejos. Asume un alto nivel de conocimiento."
    },
    "ejecutivo": {
        "nivel_tecnico": "Principiante", # Nivel técnico simplificado para ejecutivos
        "objetivo_lector": "Ejecutivo",
        "instrucciones_adicionales": "Enfócate en el ROI, impacto de negocio, estrategias, tendencias de mercado y casos de éxito. Evita detalles técnicos innecesarios."
    },
    "emprendedor": {
        "nivel_tecnico": "Intermedio", # Un emprendedor puede necesitar algo de detalle técnico pero enfocado en aplicación
        "objetivo_lector": "Emprendedor",
        "instrucciones_adicionales": "Céntrate en aplicaciones prácticas, oportunidades de mercado, modelos de negocio, escalabilidad y consejos para la implementación en startups."
    }
}

async def main_workflow():
    """
    El flujo de trabajo principal y final que orquesta el scraping,
    guardado y enriquecimiento por IA para múltiples idiomas.
    """
    logging.info("--- INICIANDO EL WORKER DE vo.app (vFinal: IA Multilingüe) ---")

    try:
        # 1. Inicializar todos nuestros clientes
        scraper = AntiDetectionScraper()
        supabase_client = SupabaseClient()
        orchestrator_config = OrchestratorConfig(**REAL_CONFIG_DICT)
        ai_orchestrator = AIOrchestrator(orchestrator_config)
        trends_analyzer = TrendsAnalyzer() # Inicializar TrendsAnalyzer
        image_fetcher = ResilientImageFetcher() # Inicializar ResilientImageFetcher
        quality_controller = QualityController() # Inicializar QualityController
        prompt_optimizer = PromptOptimizer() # Inicializar PromptOptimizer

        # Obtener temas trending de IA/tecnología
        trending_topics = trends_analyzer.get_ai_trending_topics()
        if not trending_topics:
            logging.error("No se pudieron obtener temas trending de IA. El workflow no generará contenido original.")
            # Considerar salir o usar un prompt genérico si no hay temas trending
            return
        logging.info(f"Temas trending de IA/tecnología obtenidos: {trending_topics}")

        logging.info(f"Se procesarán {len(CONTENT_SOURCES)} fuentes de contenido.")

        for source_info in CONTENT_SOURCES:
            start_time = time.time() # Iniciar contador de tiempo por fuente
            articles_found = 0
            new_articles_count = 0
            ai_processed_count = 0

            source_name, feed_url = source_info["name"], source_info["url"]
            source_headers = source_info.get("headers") # Get headers if they exist
            logging.info(f"\n--- Procesando fuente: {source_name} ---")

            feed_data = scraper.fetch_rss_feed(feed_url, headers=source_headers)
            if not feed_data or not feed_data.entries:
                logging.warning(f"No se encontraron artículos en {source_name}. Saltando.")
                continue

            articles_found = len(feed_data.entries)
            logging.info(f"Se encontraron {articles_found} artículos. Preparando para procesamiento por lotes...")

            # 2. Recolectar todos los artículos potenciales y sus URLs
            potential_articles: List[Article] = []
            potential_urls: List[str] = []
            for entry in reversed(feed_data.entries):
                try:
                    if hasattr(entry, 'link') and entry.link:
                        article = Article(
                            title=getattr(entry, 'title', 'Sin Título'),
                            url=entry.link,
                            content=getattr(entry, 'summary', 'Sin Resumen'),
                            source=source_name
                        )
                        potential_articles.append(article)
                        potential_urls.append(str(article.url))
                except ValidationError as e:
                    logging.warning(f"Artículo omitido por URL inválida: {getattr(entry, 'link', 'N/A')}. Error: {e}")
                except Exception as e:
                    logging.error(f"Error al preparar artículo '{getattr(entry, 'title', 'N/A')}': {e}")

            if not potential_articles:
                logging.info(f"No hay artículos válidos para procesar de la fuente {source_name}.")
                continue

            # 3. Obtener todos los artículos existentes para la deduplicación semántica
            all_existing_articles = supabase_client.get_all_articles() # Asume que este método existe y devuelve List[Article]

            # 4. Filtrar artículos nuevos, primero por URL y luego semánticamente
            articles_after_url_check = [
                article for article in potential_articles
                if str(article.url) not in [ea.url for ea in all_existing_articles] # Check against URLs of all existing articles
            ]

            new_articles_to_save = []
            for article in articles_after_url_check:
                if not check_for_duplicates_semantically(article, all_existing_articles):
                    new_articles_to_save.append(article)
                else:
                    logging.info(f"Artículo '{article.title}' omitido por duplicación semántica.")

            new_articles_count = len(new_articles_to_save)

            if new_articles_to_save:
                logging.info(f"Se encontraron {new_articles_count} artículos nuevos. Insertando por lotes...")
                successfully_inserted_articles = supabase_client.save_articles_batch(new_articles_to_save)

                # 5. Procesar solo los artículos nuevos insertados con la IA
                processing_tasks = [
                    process_article_with_ai(article, scraper, supabase_client, ai_orchestrator, trending_topics, image_fetcher, quality_controller, prompt_optimizer)
                    for article in successfully_inserted_articles
                ]
                ai_processing_results = await asyncio.gather(*processing_tasks)
                ai_processed_count = sum(1 for result in ai_processing_results if result)
            else:
                logging.info(f"No se encontraron artículos nuevos de la fuente {source_name} para insertar.")

            # Métricas por fuente
            end_time = time.time()
            processing_time = end_time - start_time

            # Calcular métricas de fuente
            conversion_rate = (ai_processed_count / new_articles_count) * 100 if new_articles_count > 0 else 0

            # Para la calidad promedio, necesitaríamos recuperar los quality_score de los artículos procesados
            # Por ahora, solo loguearemos los contadores. Una implementación más robusta implicaría
            # recuperar los artículos recién actualizados o pasar los scores directamente.

            logging.info(f"--- Fuente {source_name} procesada: {articles_found} encontrados, {new_articles_count} nuevos, {ai_processed_count} enriquecidos con IA, Tasa de Conversión: {conversion_rate:.2f}%, tiempo: {processing_time:.2f}s ---")

        # PROCESAR VIDEOS (nuevo)
        logging.info("--- Procesando fuentes de video ---")
        youtube_processor = YouTubeProcessor()

        for video_source in YOUTUBE_SOURCES:
            logging.info(f"Procesando videos de: {video_source['name']}")

            # Obtener videos trending
            videos = youtube_processor.get_trending_ai_videos(max_results=3)

            for video in videos:
                # Verificar si el video ya existe
                video_exists = supabase_client.check_existing_articles([video['url']])
                if video['url'] not in video_exists:
                    # Procesar video y generar artículo
                    await process_video_content(video, youtube_processor, supabase_client, ai_orchestrator, quality_controller)

    except Exception as e:
        logging.critical(f"Ha ocurrido un error fatal en el workflow principal: {e}")

    logging.info("--- WORKER DE vo.app HA FINALIZADO SU EJECUCIÓN ---")

def check_for_duplicates_semantically(new_article: Article, existing_articles: List[Article], threshold: float = 0.5) -> bool:
    """
    Compara un nuevo artículo con una lista de artículos existentes para detectar duplicados semánticos.
    Utiliza una comparación de palabras clave simple para determinar la similitud.
    """
    new_title_words = set(new_article.title.lower().split())
    new_content_words = set(new_article.content.lower().split())

    for existing_article in existing_articles:
        existing_title_words = set(existing_article.title.lower().split())
        existing_content_words = set(existing_article.content.lower().split())

        # Comparación de títulos
        title_intersection = len(new_title_words.intersection(existing_title_words))
        title_union = len(new_title_words.union(existing_title_words))
        title_similarity = title_intersection / title_union if title_union > 0 else 0

        # Comparación de contenido (primeros 200 palabras para eficiencia)
        existing_short_content_words = set(existing_article.content.lower().split()[:200])
        content_intersection = len(new_content_words.intersection(existing_short_content_words))
        content_union = len(new_content_words.union(existing_short_content_words))
        content_similarity = content_intersection / content_union if content_union > 0 else 0

        # Si ambos son muy similares, consideramos un duplicado
        if title_similarity > threshold and content_similarity > threshold:
            logging.info(f"Duplicado semántico detectado: '{new_article.title}' es similar a '{existing_article.title}'.")
            return True
    return False




async def process_article_with_ai(
    article: Article,
    scraper: AntiDetectionScraper,
    supabase_client: SupabaseClient,
    ai_orchestrator: AIOrchestrator,
    trending_topics: List[str], # Añadir trending_topics como argumento
    image_fetcher: ResilientImageFetcher, # Añadir image_fetcher como argumento
    quality_controller: QualityController, # Añadir quality_controller como argumento
    prompt_optimizer: PromptOptimizer # Añadir prompt_optimizer como argumento
) -> bool:
    """
    Procesa un artículo nuevo con la IA: obtiene el contenido completo,
    llama al orquestador de IA y actualiza el artículo en Supabase.
    Genera contenido original para cada tema trending relevante.

    Args:
        article (Article): El objeto Article a procesar.
        scraper (AntiDetectionScraper): Instancia del scraper para obtener contenido completo.
        supabase_client (SupabaseClient): Instancia del cliente de Supabase para actualizar el artículo.
        ai_orchestrator (AIOrchestrator): Instancia del orquestador de IA.
        trending_topics (List[str]): Lista de temas trending de IA/tecnología.

    Returns:
        bool: True si al menos un procesamiento fue exitoso, False en caso de fallo total.
    """
    logging.info(f"Artículo nuevo: '{article.title}'. Obteniendo contenido completo para la IA...")
    full_content = scraper.fetch_article_content(str(article.url))

    if not full_content:
        logging.warning(f"No se pudo obtener el contenido completo del artículo para '{article.title}'.")
        return False

    successful_ai_generations = 0
    for trending_topic in trending_topics:
        best_ai_response = None
        best_quality_score = -1.0
        best_prompt_version = "N/A"
        best_generation_time = 0.0
        ai_provider_name = "Default_AI_Provider" # Placeholder, should come from ai_orchestrator

        # Usar PromptOptimizer para seleccionar el mejor prompt
        # Asumimos 'technical_analysis' como content_type por defecto para este contexto
        selected_prompt_template = prompt_optimizer.get_optimized_prompt(trending_topic, "technical_analysis")
        selected_prompt_name = "technical_deep_dive" # Placeholder, should come from prompt_optimizer

        current_ai_response = None
        generation_start_time = time.time()
        current_quality_score = 0.0

        # Iteración para mejorar la calidad para el prompt actual
        max_retries = 3
        for attempt in range(max_retries):
            prompt_para_ia = selected_prompt_template.format(topic=trending_topic, reference_content=full_content[:3000])
            current_ai_response = await ai_orchestrator.get_consensus(prompt_para_ia)
            if current_ai_response:
                passes_quality, quality_report = quality_controller.analyze_content_quality(current_ai_response, trending_topic)
                if passes_quality:
                    current_quality_score = quality_report['metrics']['readability_score']
                    logging.info(f"Contenido generado con '{selected_prompt_name}' aprobado en el intento {attempt + 1}. Calidad: {current_quality_score:.2f}")
                    break
                else:
                    current_quality_score = 0.0 # No pasó el control de calidad
                    logging.warning(f"Fallo de calidad con '{selected_prompt_name}' en el intento {attempt + 1}: {quality_report['issues']}. Regenerando...")
                    selected_prompt_template += "\n\nFEEDBACK: El contenido anterior no cumplió con los estándares de calidad. Por favor, mejora la densidad de keywords, la estructura de párrafos y evita repeticiones. Asegúrate de que el contenido sea más profundo y original."
            else:
                logging.warning(f"El orquestador de IA no devolvió contenido con '{selected_prompt_name}' en el intento {attempt + 1}.")
                current_quality_score = 0.0

        generation_end_time = time.time()
        current_generation_time = generation_end_time - generation_start_time

        # Actualizar performance del prompt en el optimizador
        prompt_optimizer.update_performance(selected_prompt_name, current_quality_score, current_quality_score > 0)

        best_ai_response = current_ai_response
        best_quality_score = current_quality_score
        best_prompt_version = selected_prompt_name
        best_generation_time = current_generation_time

        logging.info(f"Prompt '{selected_prompt_name}' para '{trending_topic}': Calidad: {current_quality_score:.2f}, Tiempo: {current_generation_time:.2f}s")

        if best_ai_response:
            # Buscar imagen relacionada usando el ResilientImageFetcher
            image_url = await image_fetcher.get_image_for_article(trending_topic)

            update_data = {
                "title_es": article.title,
                "content": best_ai_response,
                "content_es": best_ai_response,
                "processed_by_ai": True,
                "generation_time": best_generation_time,
                "quality_score": best_quality_score,
                "ai_provider": ai_provider_name # Considerar cómo obtener el nombre real del proveedor
            }
            if image_url:
                update_data["image_url"] = image_url

            supabase_client.update_article(str(article.url), update_data)
            successful_ai_generations += 1
            logging.info(f"Contenido final para '{trending_topic}' (Prompt: {best_prompt_version}) y actualizado para '{article.title}'. Imagen: {image_url or 'No encontrada'}. Tiempo: {best_generation_time:.2f}s, Calidad: {best_quality_score:.2f}")
        else:
            logging.warning(f"No se pudo generar contenido de calidad para '{article.title}' sobre el tema '{trending_topic}' con ningún prompt.")
    return successful_ai_generations > 0

if __name__ == "__main__":
    asyncio.run(main_workflow())
