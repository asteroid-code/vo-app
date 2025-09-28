import os
import asyncio
from dotenv import load_dotenv
from pydantic import BaseModel, HttpUrl, ValidationError
from supabase import create_client, Client
import logging
from typing import Optional, List, Dict, Any

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cargar variables de entorno desde .env
load_dotenv()

class Article(BaseModel):
    """
    Modelo de datos para un artículo, ahora con campos opcionales para enriquecimiento.
    """
    title: str
    url: HttpUrl
    content: Optional[str] = None
    source: str
    # Nuevos campos opcionales. Pueden ser nulos.
    image_url: Optional[HttpUrl] = None
    related_products: Optional[List[Dict[str, Any]]] = None

class SupabaseClient:
    """Cliente para interactuar con la base de datos Supabase de forma segura."""

    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("Faltan las credenciales de Supabase en la configuración.")

        self.client: Client = create_client(supabase_url, supabase_key)
        logging.info("Cliente de Supabase (v2: Enriched) inicializado con éxito.")

    def save_article(self, article: Article) -> bool:
        """
        Guarda un artículo en la tabla 'articles', evitando duplicados.
        Ahora devuelve True si el artículo es nuevo, False si ya existía.
        """
        try:
            # Pydantic v2 usa model_dump() y lo pasamos a JSON para asegurar compatibilidad
            article_data = article.model_dump(mode='json')

            # Verificar si el artículo ya existe
            response = self.client.table("articles").select("url").eq("url", article_data['url']).execute()

            if response.data:
                logging.info(f"El artículo con URL '{article_data['url']}' ya existe. Se omitirá.")
                return False

            # Si no existe, insertar
            logging.info(f"Insertando nuevo artículo: '{article_data['title']}'")
            insert_response = self.client.table("articles").insert(article_data).execute()

            if insert_response.data:
                logging.info("¡ÉXITO! Artículo nuevo insertado correctamente.")
                return True
            else:
                logging.error(f"La inserción del artículo falló. Respuesta: {insert_response}")
                return False

        except Exception as e:
            logging.error(f"Error inesperado al guardar el artículo: {e}")
            return False

    def update_article(self, url: str, update_data: Dict[str, Any]) -> None:
        """
        Actualiza un artículo existente en la base de datos usando su URL.
        """
        logging.info(f"Intentando actualizar el artículo con URL: {url}")
        try:
            response = self.client.table("articles").update(update_data).eq("url", url).execute()
            if response.data:
                logging.info(f"¡ÉXITO! Artículo actualizado correctamente.")
            else:
                logging.warning(f"No se encontró o no se pudo actualizar el artículo con URL {url}. Respuesta: {response}")
        except Exception as e:
            logging.error(f"Error inesperado al actualizar el artículo: {e}")

# --- Ejemplo de Uso ---
if __name__ == "__main__":
    def run_demo():
        logging.info("Iniciando DEMO del SupabaseClient (v2: Enriched)...")

        try:
            supabase_client = SupabaseClient()

            # 1. Crear un artículo base, como lo haría el scraper
            base_article = Article(
                title="Review del Nuevo Portátil XYZ",
                url="https://example.com/review-portatil-xyz",
                content="Este es el resumen inicial del artículo...",
                source="The Verge"
            )

            logging.info(f"\n--- Paso 1: Intentando guardar el artículo base ---")
            is_new = supabase_client.save_article(base_article)

            # 2. Simular el enriquecimiento por la IA (solo si es nuevo)
            if is_new:
                logging.info(f"\n--- Paso 2: El artículo es nuevo. Simulando enriquecimiento por IA... ---")

                # Datos que nuestra IA habría generado
                enriched_data = {
                    "content": "Este es el contenido COMPLETO y ENRIQUECIDO por 8 IAs...",
                    "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8",
                    "related_products": [
                        {"type": "product_amazon", "name": "Portátil XYZ", "affiliate_link": "https://amazon.com/..."}
                    ],
                    "processed_by_ai": True
                }

                supabase_client.update_article(str(base_article.url), enriched_data)

            # 3. Intentar guardar el mismo artículo de nuevo para probar duplicados
            logging.info(f"\n--- Paso 3: Intentando guardar el artículo base de nuevo (prueba de duplicados) ---")
            supabase_client.save_article(base_article)

        except ValueError as e:
            logging.critical(e)
        except Exception as e:
            logging.error(f"Ocurrió un error durante la demostración: {e}")

        logging.info("\n--- Demostración finalizada ---")

    run_demo()
