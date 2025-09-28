import os
import asyncio
from dotenv import load_dotenv
from pydantic import BaseModel, HttpUrl
from supabase import create_client, Client
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cargar variables de entorno desde .env
load_dotenv()

class Article(BaseModel):
    """Modelo de datos para un artículo, validado por Pydantic."""
    title: str
    url: HttpUrl
    content: str
    source: str

class SupabaseClient:
    """Cliente para interactuar con la base de datos Supabase de forma segura."""

    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("Faltan las credenciales de Supabase (URL y SERVICE_KEY) en la configuración.")

        self.client: Client = create_client(supabase_url, supabase_key)
        logging.info("Cliente de Supabase inicializado con éxito.")

    def save_article(self, article: Article) -> None:
        """
        Guarda un artículo en la tabla 'articles' de Supabase, evitando duplicados.
        """
        # --- SOLUCIÓN FINAL ---
        # 1. Usar model_dump() como recomienda la nueva versión de Pydantic.
        # 2. Convertir explícitamente la URL a un string simple ANTES de cualquier operación.
        article_data = article.model_dump()
        article_data['url'] = str(article_data['url'])

        try:
            # Verificar si el artículo ya existe usando la URL de texto simple
            response = self.client.table("articles").select("url").eq("url", article_data['url']).execute()

            if response.data:
                logging.info(f"El artículo con URL '{article_data['url']}' ya existe. Se omitirá.")
                return

            # Si no existe, insertar el diccionario con la URL ya convertida a texto
            logging.info(f"Insertando nuevo artículo: '{article_data['title']}'")
            insert_response = self.client.table("articles").insert(article_data).execute()

            if len(insert_response.data) > 0:
                logging.info("¡ÉXITO! Artículo insertado correctamente en Supabase.")
            else:
                logging.error(f"La inserción del artículo falló. Respuesta de Supabase: {insert_response}")

        except Exception as e:
            logging.error(f"Error inesperado al interactuar con Supabase: {e}")


# --- Ejemplo de Uso ---
if __name__ == "__main__":
    async def main():
        logging.info("Iniciando DEMO FINAL del SupabaseClient...")

        try:
            supabase_client = SupabaseClient()

            # --- URLs CORREGIDAS ---
            article1 = Article(
                title="Nuevo Avance en IA Cuántica",
                url="https://example.com/ia-cuantica-1",
                content="El contenido del artículo sobre IA cuántica...",
                source="TechCrunch"
            )
            article2 = Article(
                title="El Futuro de los Vehículos Autónomos",
                url="https://example.com/vehiculos-autonomos-futuro",
                content="Un análisis profundo sobre los coches que se conducen solos...",
                source="Wired"
            )

            logging.info(f"\n--- Intentando guardar Artículo 1: '{article1.title}' ---")
            supabase_client.save_article(article1)

            logging.info(f"\n--- Intentando guardar Artículo 2: '{article2.title}' ---")
            supabase_client.save_article(article2)

            logging.info(f"\n--- Intentando guardar Artículo 1 de nuevo (prueba de duplicados) ---")
            supabase_client.save_article(article1)

        except ValueError as e:
            logging.critical(e)
        except Exception as e:
            logging.error(f"Ocurrió un error durante la demostración: {e}")

        logging.info("\n--- Demostración finalizada ---")

    asyncio.run(main())
