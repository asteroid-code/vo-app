import requests
import os
import logging
from typing import Optional, List

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class UnsplashImageFetcher:
    def __init__(self):
        self.access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        self.base_url = "https://api.unsplash.com"

        if not self.access_key:
            logging.error("UNSPLASH_ACCESS_KEY no encontrada en las variables de entorno.")
            # Podrías lanzar una excepción o manejar esto de otra manera
            # Por ahora, simplemente loggeamos el error.

    def search_image(self, query: str) -> Optional[str]:
        """
        Busca una imagen en Unsplash basada en el query
        Retorna la URL de la imagen o None si falla
        """
        if not self.access_key:
            logging.warning("No hay UNSPLASH_ACCESS_KEY configurada. No se pueden buscar imágenes.")
            return None

        logging.info(f"Buscando imagen en Unsplash para el query: '{query}'")
        try:
            headers = {"Authorization": f"Client-ID {self.access_key}"}
            params = {
                "query": query,
                "per_page": 1,
                "orientation": "landscape"
            }

            response = requests.get(
                f"{self.base_url}/search/photos",
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if data["results"]:
                image_url = data["results"][0]["urls"]["regular"]
                logging.info(f"Imagen encontrada para '{query}': {image_url}")
                return image_url
            else:
                logging.info(f"No se encontraron imágenes en Unsplash para el query: '{query}'")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error de red/API al buscar imagen para '{query}': {e}")
        except Exception as e:
            logging.error(f"Error inesperado buscando imagen para '{query}': {e}")

        return None

    def generate_image_queries(self, article_topic: str) -> List[str]:
        """Genera consultas de búsqueda basadas en el tema del artículo"""
        # Podrías hacer esto más sofisticado, por ejemplo, usando la IA para generar queries
        return [
            f"{article_topic} technology",
            "artificial intelligence abstract",
            "future technology concept",
            "digital transformation background",
            f"{article_topic} innovation"
        ]

# --- Ejemplo de Uso ---
if __name__ == "__main__":
    # Para probar esto, asegúrate de tener UNSPLASH_ACCESS_KEY en tu .env
    # y ejecutar `python -m dotenv run python utils/image_fetcher.py`
    logging.info("Iniciando demostración de UnsplashImageFetcher...")
    fetcher = UnsplashImageFetcher()

    test_topic = "Inteligencia Artificial"
    queries = fetcher.generate_image_queries(test_topic)
    logging.info(f"Queries generadas para '{test_topic}': {queries}")

    for query in queries:
        image_url = fetcher.search_image(query)
        if image_url:
            logging.info(f"Imagen para '{query}': {image_url}")
            break # Tomar la primera imagen exitosa
    else:
        logging.warning(f"No se pudo encontrar ninguna imagen para el tema '{test_topic}'.")

    logging.info("Demostración de UnsplashImageFetcher finalizada.")
