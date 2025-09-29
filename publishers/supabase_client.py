import os
import asyncio
from dotenv import load_dotenv
from pydantic import BaseModel, HttpUrl, Field
from supabase import create_client, Client
import logging
from typing import Optional, List, Dict, Any

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cargar variables de entorno desde .env
load_dotenv()

class Article(BaseModel):
    """
    Modelo de datos final para un artículo, incluyendo todos los campos de enriquecimiento.
    """
    title: str
    url: HttpUrl
    content: Optional[str] = None
    source: str

    # Campos opcionales para enriquecimiento (pueden ser nulos)
    title_es: Optional[str] = None
    content_es: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    related_products: Optional[List[Dict[str, Any]]] = None
    processed_by_ai: bool = Field(default=False)
    generation_time: Optional[float] = None # Tiempo en segundos
    quality_score: Optional[float] = None # Puntuación de calidad (0.0 a 1.0)
    ai_provider: Optional[str] = None # Nombre del proveedor de IA que generó el contenido

class SupabaseClient:
    """Cliente final para interactuar con la base de datos Supabase."""

    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("Faltan las credenciales de Supabase en la configuración.")

        self.client: Client = create_client(supabase_url, supabase_key)
        self._url_cache: set[str] = set() # Cache en memoria para URLs recientes
        logging.info("Cliente de Supabase (vFinal: Enriched) inicializado con éxito.")

    def save_article(self, article: Article) -> bool:
        """
        Guarda un artículo base en Supabase, evitando duplicados.
        Devuelve True si el artículo es nuevo, False si ya existía.
        """
        article_url_str = str(article.url)

        # 1. Verificar en el cache en memoria primero
        if article_url_str in self._url_cache:
            logging.info(f"El artículo con URL '{article_url_str}' ya existe en cache. Se omitirá.")
            return False

        try:
            # Pydantic v2 usa model_dump() y lo pasamos a JSON para asegurar compatibilidad con tipos complejos
            article_data = article.model_dump(mode='json')

            # 2. Verificar en la base de datos
            response = self.client.table("articles").select("url").eq("url", article_data['url']).execute()

            if response.data:
                logging.info(f"El artículo con URL '{article_url_str}' ya existe en DB. Se omitirá.")
                self._url_cache.add(article_url_str) # Añadir al cache si se encuentra en DB
                return False

            # 3. Insertar nuevo artículo
            logging.info(f"Insertando nuevo artículo: '{article_data['title']}'")
            insert_response = self.client.table("articles").insert(article_data).execute()

            if insert_response.data:
                logging.info("¡ÉXITO! Artículo nuevo insertado correctamente.")
                self._url_cache.add(article_url_str) # Añadir al cache si la inserción es exitosa
                return True
            else:
                logging.error(f"La inserción del artículo falló. Respuesta: {insert_response}")
                return False

        except Exception as e:
            logging.error(f"Error inesperado al guardar el artículo: {e}")
            return False

    def update_article(self, url: str, update_data: Dict[str, Any]) -> None:
        """
        Actualiza un artículo existente en la base de datos usando su URL única.
        """
        logging.info(f"Intentando actualizar el artículo con URL: {url}")
        try:
            response = self.client.table("articles").update(update_data).eq("url", url).execute()
            if response.data:
                logging.info(f"¡ÉXITO! Artículo actualizado correctamente con datos enriquecidos.")
            else:
                # Esto puede pasar si el artículo se borró entre la inserción y la actualización
                logging.warning(f"No se encontró o no se pudo actualizar el artículo con URL {url}.")
        except Exception as e:
            logging.error(f"Error inesperado al actualizar el artículo: {e}")

    def check_existing_articles_batch(self, urls: List[str]) -> set[str]:
        """
        Verifica la existencia de múltiples URLs en la base de datos en una sola consulta.

        Args:
            urls (List[str]): Una lista de URLs a verificar.

        Returns:
            set[str]: Un conjunto de URLs que ya existen en la base de datos.
        """
        if not urls:
            return set()

        try:
            # Realizar una sola consulta usando el operador 'in'
            response = self.client.table("articles").select("url").in_("url", urls).execute()

            existing_urls = {item["url"] for item in response.data}
            logging.info(f"Verificación por lotes: {len(existing_urls)} de {len(urls)} URLs ya existen.")
            return existing_urls
        except Exception as e:
            logging.error(f"Error al verificar URLs por lotes en Supabase: {e}")
            return set()

    def save_articles_batch(self, articles: List[Article]) -> List[Article]:
        """
        Inserta múltiples artículos en Supabase en una sola operación por lotes.

        Args:
            articles (List[Article]): Una lista de objetos Article a insertar.

        Returns:
            List[Article]: Una lista de los objetos Article que fueron insertados exitosamente.
        """
        if not articles:
            return []

        articles_data = []
        for article in articles:
            data = article.model_dump(mode='json')
            # Explicitly remove fields that might not exist in the DB table
            data.pop('generation_time', None)
            data.pop('quality_score', None)
            data.pop('ai_provider', None)
            articles_data.append(data)

        try:
            logging.info(f"Intentando insertar {len(articles_data)} artículos por lotes.")
            insert_response = self.client.table("articles").insert(articles_data).execute()

            if insert_response.data:
                inserted_urls = {item["url"] for item in insert_response.data}
                successfully_inserted_articles = [
                    article for article in articles if str(article.url) in inserted_urls
                ]
                logging.info(f"¡ÉXITO! Se insertaron {len(successfully_inserted_articles)} artículos por lotes.")
                return successfully_inserted_articles
            else:
                logging.error(f"La inserción por lotes de artículos falló. Respuesta: {insert_response}")
                return []
        except Exception as e:
            logging.error(f"Error inesperado al guardar artículos por lotes: {e}")
            return []

    def get_all_articles(self) -> List[Article]:
        """
        Obtiene todos los artículos de la base de datos.
        """
        try:
            response = self.client.table("articles").select("*").execute()
            articles = [Article(**item) for item in response.data]
            logging.info(f"Se recuperaron {len(articles)} artículos de la base de datos.")
            return articles
        except Exception as e:
            logging.error(f"Error al obtener todos los artículos de Supabase: {e}")
            return []

# --- Ejemplo de Uso ---
if __name__ == "__main__":
    def run_demo():
        logging.info("Iniciando DEMO FINAL del SupabaseClient (vFinal: Enriched)...")

        try:
            supabase_client = SupabaseClient()

            # 1. Simular la llegada de un artículo scrapeado
            base_article = Article(
                title="Review Final del Gadget del Año",
                url="https://example.com/gadget-review-2025",
                content="Resumen inicial...",
                source="The Verge"
            )

            logging.info(f"\n--- PASO 1: Guardando el artículo base ---")
            is_new = supabase_client.save_article(base_article)

            # 2. Simular el enriquecimiento por la IA (solo si es nuevo)
            if is_new:
                logging.info(f"\n--- PASO 2: El artículo es nuevo. Simulando enriquecimiento por IA... ---")

                # Datos que nuestra IA habría generado
                enriched_data = {
                    "content": "Este es el análisis completo en INGLÉS generado por 8 IAs...",
                    "title_es": "Análisis Final del Dispositivo del Año",
                    "content_es": "Este es el análisis completo en ESPAÑOL generado por 8 IAs...",
                    "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8",
                    "related_products": [
                        {"type": "product_amazon", "name": "Gadget del Año", "affiliate_link": "https://amazon.com/..."}
                    ],
                    "processed_by_ai": True
                }

                supabase_client.update_article(str(base_article.url), enriched_data)

            # 3. Probar la lógica de duplicados
            logging.info(f"\n--- PASO 3: Intentando guardar el artículo de nuevo ---")
            supabase_client.save_article(base_article)

        except ValueError as e:
            logging.critical(e)
        except Exception as e:
            logging.error(f"Ocurrió un error durante la demostración: {e}")

        logging.info("\n--- Demostración finalizada ---")

    run_demo()
