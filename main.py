import logging
import asyncio
from typing import List, Dict
from pydantic import ValidationError
from publishers.supabase_client import SupabaseClient, Article
from scrapers.anti_detection import AntiDetectionScraper
from ai_orchestrator.consensus_engine import AIOrchestrator, OrchestratorConfig, EXAMPLE_CONFIG_DICT

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- BIBLIOTECA DE CONTENIDO CENTRALIZADA ---
CONTENT_SOURCES: List[Dict[str, str]] = [
    {"type": "rss", "category": "noticias_ia", "name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"type": "rss", "category": "reviews_tech", "name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    # Limitamos a 2 fuentes para una prueba más rápida y barata
]

async def main_workflow():
    """
    El flujo de trabajo principal y final que orquesta el scraping,
    guardado y enriquecimiento por IA.
    """
    logging.info("--- INICIANDO EL WORKER DE vo.app (vFinal: CON IA INTEGRADA) ---")

    try:
        # 1. Inicializar todos nuestros clientes
        scraper = AntiDetectionScraper()
        supabase_client = SupabaseClient()
        orchestrator_config = OrchestratorConfig(**EXAMPLE_CONFIG_DICT)
        ai_orchestrator = AIOrchestrator(orchestrator_config)

        logging.info(f"Se procesarán {len(CONTENT_SOURCES)} fuentes de contenido.")

        for source_info in CONTENT_SOURCES:
            source_name = source_info["name"]
            feed_url = source_info["url"]

            logging.info(f"\n--- Procesando fuente: {source_name} ---")

            feed_data = scraper.fetch_rss_feed(feed_url)

            if not feed_data or not feed_data.entries:
                logging.warning(f"No se encontraron artículos en {source_name}. Saltando.")
                continue

            logging.info(f"Se encontraron {len(feed_data.entries)} artículos. Validando y guardando...")

            for entry in reversed(feed_data.entries):
                try:
                    if hasattr(entry, 'link') and entry.link:
                        # 2. Guardar el artículo base para ver si es nuevo
                        article = Article(
                            title=getattr(entry, 'title', 'Sin Título'),
                            url=entry.link,
                            content=getattr(entry, 'summary', 'Sin Resumen'),
                            source=source_name
                        )
                        is_new = supabase_client.save_article(article)

                        # 3. SI Y SOLO SI el artículo es nuevo, lo procesamos con la IA
                        if is_new:
                            logging.info(f"Artículo nuevo: '{article.title}'. Obteniendo contenido completo para la IA...")

                            # Obtener el contenido completo
                            full_content = scraper.fetch_article_content(str(article.url))

                            if full_content:
                                # 4. Crear un prompt y llamar al orquestador
                                prompt_para_ia = f"Resume el siguiente artículo en 3 puntos clave y extrae los nombres de hasta 2 productos o empresas mencionados. Artículo: '{full_content[:4000]}'"

                                logging.info("Llamando al orquestador de IA... (Esto puede tardar)")
                                ai_consensus_content = await ai_orchestrator.get_consensus(prompt_para_ia)

                                if ai_consensus_content:
                                    # 5. Actualizar el artículo en Supabase con el contenido enriquecido
                                    update_data = {
                                        "content": ai_consensus_content,
                                        "processed_by_ai": True
                                    }
                                    supabase_client.update_article(str(article.url), update_data)
                                else:
                                    logging.warning("El orquestador de IA no devolvió contenido.")
                            else:
                                logging.warning(f"No se pudo obtener el contenido completo del artículo.")

                except ValidationError as e:
                    logging.warning(f"Artículo omitido por URL inválida: {getattr(entry, 'link', 'N/A')}")
                except Exception as e:
                    logging.error(f"Error procesando el artículo '{getattr(entry, 'title', 'N/A')}': {e}")

            logging.info(f"--- Fuente {source_name} procesada con éxito. ---")

    except Exception as e:
        logging.critical(f"Ha ocurrido un error fatal en el workflow principal: {e}")

    logging.info("--- WORKER DE vo.app HA FINALIZADO SU EJECUCIÓN ---")

if __name__ == "__main__":
    asyncio.run(main_workflow())
