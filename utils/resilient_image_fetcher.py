import os
import logging
from typing import Optional, List
import uuid
from datetime import datetime
from dotenv import load_dotenv
import asyncio
import aiohttp

load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ResilientImageFetcher:
    def __init__(self):
        self.unsplash_access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.huggingface_api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0" # Asumiendo este modelo

        self.sources = [
            self._try_unsplash,
            self._try_pexels,
            self._try_huggingface_sd,
            self._get_local_fallback
        ]

    def _generate_image_queries(self, article_topic: str) -> List[str]:
        """Genera consultas de búsqueda para imágenes"""
        return [
            f"{article_topic} technology",
            "artificial intelligence concept",
            "future technology background",
            "digital transformation innovation",
            f"{article_topic} innovation"
        ]

    async def get_image_for_article(self, article_topic: str) -> Optional[str]:
        """Obtiene imagen para un artículo, intentando múltiples fuentes"""
        queries = self._generate_image_queries(article_topic)

        for query in queries:
            for source in self.sources:
                try:
                    image_url = await source(query)
                    if image_url:
                        logging.info(f"Imagen encontrada para '{query}' de la fuente {source.__name__}")
                        return image_url
                except Exception as e:
                    logging.warning(f"Fuente {source.__name__} falló para '{query}': {e}")
                    continue

        logging.error("Todas las fuentes de imágenes fallaron")
        return None

    async def _try_unsplash(self, query: str) -> Optional[str]:
        """Intenta Unsplash primero"""
        if not self.unsplash_access_key:
            raise ValueError("UNSPLASH_ACCESS_KEY no configurado.")

        url = f"https://api.unsplash.com/search/photos?query={query}&per_page=1"
        headers = {"Authorization": f"Client-ID {self.unsplash_access_key}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                if data and data["results"]:
                    return data["results"][0]["urls"]["regular"]
        return None

    async def _try_pexels(self, query: str) -> Optional[str]:
        """Fallback: Pexels API"""
        if not self.pexels_api_key:
            raise ValueError("PEXELS_API_KEY no configurado.")

        url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
        headers = {"Authorization": self.pexels_api_key}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                if data and data["photos"]:
                    return data["photos"][0]["src"]["large"]
        return None

    async def _try_huggingface_sd(self, query: str) -> Optional[str]:
        """Fallback: Generar imagen con Stable Diffusion"""
        if not self.huggingface_api_key or not self.huggingface_api_url:
            raise ValueError("HUGGINGFACE_API_KEY o HUGGINGFACE_API_URL no configurado.")

        headers = {"Authorization": f"Bearer {self.huggingface_api_key}"}
        payload = {"inputs": query}

        async with aiohttp.ClientSession() as session:
            async with session.post(self.huggingface_api_url, headers=headers, json=payload) as response:
                response.raise_for_status()
                # Asumiendo que la API devuelve la imagen directamente o un enlace a ella
                # Para Stable Diffusion, a menudo devuelve bytes de imagen que necesitarían ser guardados
                # o subidos a un CDN. Para simplificar, asumiremos que devuelve una URL temporal o base64.
                # En un caso real, esto sería más complejo.
                # Por ahora, devolveremos una URL de placeholder si la generación es "exitosa"
                logging.warning("La generación de imágenes con HuggingFace Stable Diffusion es una simulación. No se genera una imagen real.")
                return "https://via.placeholder.com/800x450.png?text=Generated+by+Stable+Diffusion" # Placeholder
        return None

    def _get_local_fallback(self, query: str) -> str:
        """Último fallback: imagen local genérica"""
        logging.info(f"Usando imagen de fallback local para '{query}'.")
        return "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=800"

# Ejemplo de uso (para pruebas)
async def demo_resilient_fetcher():
    fetcher = ResilientImageFetcher()
    topic = "Inteligencia Artificial en la medicina"
    image = await fetcher.get_image_for_article(topic)
    if image:
        logging.info(f"Imagen final obtenida: {image}")
    else:
        logging.error("No se pudo obtener ninguna imagen.")

if __name__ == "__main__":
    asyncio.run(demo_resilient_fetcher())
