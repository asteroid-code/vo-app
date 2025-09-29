import logging
import asyncio
import time # Importar el módulo time
from typing import List, Dict
from pydantic import ValidationError
from publishers.supabase_client import SupabaseClient, Article
from scrapers.anti_detection import AntiDetectionScraper
from ai_orchestrator.consensus_engine import AIOrchestrator, OrchestratorConfig, REAL_CONFIG_DICT
from trends_analyzer import TrendsAnalyzer # Importar TrendsAnalyzer
from utils.image_fetcher import UnsplashImageFetcher # Importar UnsplashImageFetcher

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- BIBLIOTECA DE CONTENIDO ---
CONTENT_SOURCES: List[Dict[str, str]] = [
    {"type": "rss", "category": "noticias_ia", "name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"type": "rss", "category": "reviews_tech", "name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
]

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
        image_fetcher = UnsplashImageFetcher() # Inicializar UnsplashImageFetcher

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
            logging.info(f"\n--- Procesando fuente: {source_name} ---")

            feed_data = scraper.fetch_rss_feed(feed_url)
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

            # 3. Verificar existencia en Supabase en una sola consulta por lote
            existing_urls = supabase_client.check_existing_articles_batch(potential_urls)

            # 4. Filtrar artículos nuevos y guardarlos por lote
            new_articles_to_save = [
                article for article in potential_articles
                if str(article.url) not in existing_urls
            ]
            new_articles_count = len(new_articles_to_save)

            if new_articles_to_save:
                logging.info(f"Se encontraron {new_articles_count} artículos nuevos. Insertando por lotes...")
                successfully_inserted_articles = supabase_client.save_articles_batch(new_articles_to_save)

                # 5. Procesar solo los artículos nuevos insertados con la IA
                processing_tasks = [
                    process_article_with_ai(article, scraper, supabase_client, ai_orchestrator, trending_topics, image_fetcher)
                    for article in successfully_inserted_articles
                ]
                ai_processing_results = await asyncio.gather(*processing_tasks)
                ai_processed_count = sum(1 for result in ai_processing_results if result)
            else:
                logging.info(f"No se encontraron artículos nuevos de la fuente {source_name} para insertar.")

            # Métricas por fuente
            end_time = time.time()
            processing_time = end_time - start_time
            logging.info(f"--- Fuente {source_name} procesada: {articles_found} encontrados, {new_articles_count} nuevos, {ai_processed_count} enriquecidos con IA, tiempo: {processing_time:.2f}s ---")

    except Exception as e:
        logging.critical(f"Ha ocurrido un error fatal en el workflow principal: {e}")

    logging.info("--- WORKER DE vo.app HA FINALIZADO SU EJECUCIÓN ---")

def create_content_creation_prompt(trending_topic: str, reference_content: str) -> str:
    return f"""
ANALYST_ROLE: Eres un analista senior de tecnología y un escritor especializado.

MISIÓN: Crear contenido ORIGINAL de 800-1200 palabras, no un resumen.

TEMA_PRINCIPAL: {trending_topic}
CONTENIDO_REFERENCIA: {reference_content[:3000]}  # Primeros 3000 chars como contexto

INSTRUCCIONES_ESCRITURA:
1. INVESTIGACIÓN ORIGINAL: Desarrolla análisis y perspectivas únicas
2. ESTRUCTURA COMPLETA:
   - Introducción atractiva (100-150 palabras)
   - 3-4 secciones principales con subtítulos
   - Análisis de impacto práctico
   - Casos de estudio o ejemplos reales
   - Conclusiones y perspectivas futuras
3. PROFUNDIDAD TÉCNICA: Incluye datos específicos, estadísticas cuando sea posible
4. TONO: Profesional pero accesible, evitando jerga técnica innecesaria
5. LONGITUD: 800-1200 palabras mínimo

FORMATO_SALIDA:
El contenido completo en formato de artículo bien estructurado, listo para publicación.

IMPORTANTE: Este debe ser contenido NUEVO, desarrollado a partir del tema, no una reescritura del contenido de referencia.
"""

async def process_article_with_ai(
    article: Article,
    scraper: AntiDetectionScraper,
    supabase_client: SupabaseClient,
    ai_orchestrator: AIOrchestrator,
    trending_topics: List[str], # Añadir trending_topics como argumento
    image_fetcher: UnsplashImageFetcher # Añadir image_fetcher como argumento
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
        prompt_para_ia = create_content_creation_prompt(trending_topic, full_content)

        logging.info(f"Llamando al orquestador de IA para generar contenido sobre '{trending_topic}'... (Esto puede tardar)")
        ai_response = await ai_orchestrator.get_consensus(prompt_para_ia)

        if ai_response:
            # Aquí se asume que la respuesta de la IA es el contenido original completo
            # Para manejar múltiples contenidos por artículo, podríamos necesitar un nuevo campo
            # en el modelo Article o una tabla relacionada. Por ahora, actualizaremos el mismo artículo
            # con el contenido del ÚLTIMO tema trending procesado, o podríamos concatenarlos/elegir uno.
            # Buscar imagen relacionada
            image_queries = image_fetcher.generate_image_queries(trending_topic)
            image_url = None
            for query in image_queries:
                image_url = image_fetcher.search_image(query)
                if image_url:
                    break

            update_data = {
                "title_es": article.title, # Mantener el título original o generar uno nuevo si la IA lo permite
                "content": ai_response, # Contenido principal generado por IA (en inglés o el idioma principal)
                "content_es": ai_response, # Asumimos que la IA puede generar en español si se le pide, o se necesitaría otra llamada/traducción
                "processed_by_ai": True
            }
            if image_url:
                update_data["image_url"] = image_url

            supabase_client.update_article(str(article.url), update_data)
            successful_ai_generations += 1
            logging.info(f"Contenido generado para '{trending_topic}' y actualizado para '{article.title}'. Imagen: {image_url or 'No encontrada'}")
        else:
            logging.warning(f"El orquestador de IA no devolvió contenido para '{article.title}' sobre el tema '{trending_topic}'.")

    return successful_ai_generations > 0

if __name__ == "__main__":
    asyncio.run(main_workflow())
