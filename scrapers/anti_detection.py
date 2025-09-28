import cloudscraper
from bs4 import BeautifulSoup
import feedparser
import time
import random
import logging
from typing import Dict, Any, Optional

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Diccionario de Configuración ---
SCRAPER_CONFIG = {
    "delay_range_seconds": (3, 8),
    "timeout_seconds": 20,
}

class AntiDetectionScraper:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        logging.info("AntiDetectionScraper (Final Version) inicializado con CloudScraper.")

    def _apply_random_delay(self):
        delay = random.uniform(*SCRAPER_CONFIG["delay_range_seconds"])
        logging.info(f"Aplicando retraso aleatorio de {delay:.2f} segundos...")
        time.sleep(delay)

    def fetch_rss_feed(self, rss_url: str) -> Optional[Dict[str, Any]]:
        logging.info(f"Intentando descargar y parsear feed RSS de: {rss_url}")
        self._apply_random_delay()

        try:
            response = self.scraper.get(rss_url, timeout=SCRAPER_CONFIG["timeout_seconds"])
            response.raise_for_status()

            logging.info("Petición a través de CloudScraper exitosa. Procediendo a parsear el contenido descomprimido...")

            # --- SOLUCIÓN FINAL ---
            # `response.content` nos da los bytes descomprimidos, que es lo que
            # feedparser necesita para manejar correctamente la codificación.
            feed = feedparser.parse(response.content)

            if feed.bozo:
                # Este warning puede aparecer a veces por detalles menores en el feed, no siempre es un error crítico.
                logging.warning(f"Posibles errores menores al parsear RSS (esto puede ser normal): {feed.bozo_exception}")

            if not feed.entries:
                logging.error(f"Feed de {rss_url} descargado, pero no se encontraron entradas.")
                return None

            logging.info(f"¡ÉXITO! Feed RSS de {rss_url} parseado con {len(feed.entries)} entradas.")
            return feed

        except Exception as e:
            logging.error(f"Error crítico al intentar obtener el feed {rss_url}: {e}")
            return None

    def fetch_article_content(self, article_url: str) -> Optional[str]:
        logging.info(f"Intentando descargar contenido del artículo de: {article_url}")
        self._apply_random_delay()
        try:
            response = self.scraper.get(article_url, timeout=SCRAPER_CONFIG["timeout_seconds"])
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            article_body = soup.find('article') or soup.find('main')

            if article_body:
                for unwanted_tag in article_body(['script', 'style', 'nav', 'footer', 'aside']):
                    unwanted_tag.decompose()
                text_content = article_body.get_text(separator='\n', strip=True)
                logging.info(f"Contenido del artículo extraído con éxito.")
                return text_content
            else:
                logging.warning(f"No se pudo encontrar el cuerpo principal del artículo en {article_url}.")
                return soup.get_text(separator='\n', strip=True)
        except Exception as e:
            logging.error(f"Error crítico al obtener el contenido del artículo {article_url}: {e}")
            return None

# --- Ejemplo de Uso ---
if __name__ == "__main__":
    def run_scraper_demo():
        logging.info("Iniciando DEMO FINAL del AntiDetectionScraper...")
        scraper = AntiDetectionScraper()

        rss_feed_url = "https://techcrunch.com/category/artificial-intelligence/feed/"
        logging.info(f"\n--- Scrapeando feed RSS: {rss_feed_url} ---")
        feed_data = scraper.fetch_rss_feed(rss_feed_url)

        if feed_data and feed_data.entries:
            first_entry = feed_data.entries[0] # Corregido para acceder al primer elemento
            article_link = first_entry.link
            logging.info(f"Primer artículo encontrado: '{first_entry.title}' - {article_link}")

            logging.info(f"\n--- Scrapeando contenido del artículo: {article_link} ---")
            article_content = scraper.fetch_article_content(article_link)

            if article_content:
                logging.info(f"Contenido del artículo (primeros 500 caracteres):\n{article_content[:500]}...")
        else:
            logging.error("FALLO FINAL: No se pudo obtener o parsear el feed RSS.")

        logging.info("\n--- Demostración finalizada ---")

    run_scraper_demo()
