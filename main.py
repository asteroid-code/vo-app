import logging
import asyncio
import time # Importar el módulo time
from typing import List, Dict
from pydantic import ValidationError
from publishers.supabase_client import SupabaseClient, Article
from scrapers.anti_detection import AntiDetectionScraper
from ai_orchestrator.consensus_engine import AIOrchestrator, OrchestratorConfig, REAL_CONFIG_DICT

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
                    process_article_with_ai(article, scraper, supabase_client, ai_orchestrator)
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

async def process_article_with_ai(
    article: Article,
    scraper: AntiDetectionScraper,
    supabase_client: SupabaseClient,
    ai_orchestrator: AIOrchestrator
) -> bool:
    """
    Procesa un artículo nuevo con la IA: obtiene el contenido completo,
    llama al orquestador de IA y actualiza el artículo en Supabase.

    Args:
        article (Article): El objeto Article a procesar.
        scraper (AntiDetectionScraper): Instancia del scraper para obtener contenido completo.
        supabase_client (SupabaseClient): Instancia del cliente de Supabase para actualizar el artículo.
        ai_orchestrator (AIOrchestrator): Instancia del orquestador de IA.

    Returns:
        bool: True si el procesamiento fue exitoso, False en caso de fallo.
    """
    logging.info(f"Artículo nuevo: '{article.title}'. Obteniendo contenido completo para la IA...")
    full_content = scraper.fetch_article_content(str(article.url))

    if full_content:
        prompt_para_ia = f"""
        Actúa como un analista de tecnología experto. Analiza el siguiente artículo y proporciona dos cosas en formato JSON:
        1. Un resumen conciso en INGLÉS (english_summary).
        2. El mismo resumen, traducido con alta calidad al ESPAÑOL (spanish_summary).

        Artículo: '{full_content[:4000]}'
        """

        logging.info("Llamando al orquestador de IA... (Esto puede tardar)")
        ai_response = await ai_orchestrator.get_consensus(prompt_para_ia)

        if ai_response:
            # FUTURO: Aquí parsearíamos el JSON de la respuesta de la IA
            # Por ahora, usamos la respuesta completa como contenido.
            update_data = {
                "content": ai_response, # Contenido principal en inglés
                "content_es": ai_response, # Contenido en español (mejora futura: parsear JSON)
                "processed_by_ai": True
            }
            supabase_client.update_article(str(article.url), update_data)
            return True
        else:
            logging.warning(f"El orquestador de IA no devolvió contenido para '{article.title}'.")
            return False
    else:
        logging.warning(f"No se pudo obtener el contenido completo del artículo para '{article.title}'.")
        return False

if __name__ == "__main__":
    asyncio.run(main_workflow())
