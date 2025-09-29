from pytrends.request import TrendReq
import logging
from typing import List, Optional

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TrendsAnalyzer:
    """
    Clase para interactuar con Google Trends y obtener temas populares de IA y tecnología.
    """
    def __init__(self):
        """
        Inicializa la conexión con Google Trends.
        """
        self.pytrends = TrendReq(hl='es-AR', tz=360) # hl: host language, tz: timezone (Argentina)
        self.ai_keywords = ["AI", "Inteligencia Artificial", "Machine Learning", "Deep Learning", "ChatGPT", "Generative AI", "Modelos de Lenguaje", "Robótica", "Automatización", "Visión por Computadora"]
        self.fallback_topics = [
            "Inteligencia Artificial",
            "ChatGPT",
            "Machine Learning",
            "Innovación Tecnológica",
            "Futuro de la IA"
        ]
        logging.info("TrendsAnalyzer inicializado con pytrends.")

    def get_ai_trending_topics(self) -> List[str]:
        """
        Obtiene temas trending relacionados con IA/tecnología, los filtra
        y retorna una lista de 3-5 temas más relevantes.

        Returns:
            List[str]: Una lista de temas trending de IA/tecnología.
        """
        logging.info("Intentando obtener temas trending de Google Trends...")
        try:
            # Obtener búsquedas diarias trending
            # geo='AR' para Argentina, pero se puede omitir para tendencias globales
            # hl='es' para idioma español
            trending_searches_df = self.pytrends.trending_searches(pn='argentina') # pn: property name (country)

            if trending_searches_df.empty:
                logging.warning("No se encontraron búsquedas trending diarias. Usando temas de fallback.")
                return self.fallback_topics

            trending_topics = trending_searches_df[0].tolist()
            logging.info(f"Temas trending encontrados: {trending_topics}")

            # Filtrar temas relevantes de IA/tecnología
            relevant_topics = []
            for topic in trending_topics:
                # Convertir a minúsculas para una comparación sin distinción de mayúsculas y minúsculas
                lower_topic = topic.lower()
                if any(keyword.lower() in lower_topic for keyword in self.ai_keywords):
                    relevant_topics.append(topic)

            # Si no se encuentran temas relevantes, intentar con sugerencias de palabras clave
            if not relevant_topics:
                logging.info("No se encontraron temas trending directamente relacionados con IA. Buscando sugerencias...")
                for keyword in self.ai_keywords[:3]: # Probar con las primeras 3 palabras clave
                    suggestions = self.pytrends.suggestions(keyword=keyword)
                    if suggestions:
                        for suggestion in suggestions:
                            if suggestion and suggestion['title'] and suggestion['title'].lower() not in [t.lower() for t in relevant_topics]:
                                relevant_topics.append(suggestion['title'])
                                if len(relevant_topics) >= 5: # Limitar a 5 sugerencias
                                    break
                    if len(relevant_topics) >= 5:
                        break

            if not relevant_topics:
                logging.warning("No se encontraron temas relevantes de IA/tecnología. Usando temas de fallback.")
                return self.fallback_topics

            # Retornar los 3-5 temas más relevantes (o menos si no hay suficientes)
            return relevant_topics[:5]

        except Exception as e:
            logging.error(f"Error al obtener temas trending de Google Trends: {e}. Usando temas de fallback.")
            return self.fallback_topics

# --- Ejemplo de Uso ---
if __name__ == "__main__":
    logging.info("Iniciando demostración de TrendsAnalyzer...")
    analyzer = TrendsAnalyzer()
    trending_ai_topics = analyzer.get_ai_trending_topics()
    logging.info(f"Temas trending de IA/tecnología: {trending_ai_topics}")
    logging.info("Demostración de TrendsAnalyzer finalizada.")
