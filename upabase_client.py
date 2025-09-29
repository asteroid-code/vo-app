[1mdiff --git a/ai_orchestrator/consensus_engine.py b/ai_orchestrator/consensus_engine.py[m
[1mindex ef5920f..bb9a0bc 100644[m
[1m--- a/ai_orchestrator/consensus_engine.py[m
[1m+++ b/ai_orchestrator/consensus_engine.py[m
[36m@@ -150,42 +150,63 @@[m [mclass ConsensusEngine:[m
         self.ai_weights = {config.name: config.weight for config in ai_configs}[m
         logging.info("Consensus Engine inicializado con pesos de IA.")[m
 [m
[32m+[m[32m    def _calculate_response_score(self, response_content: str, ai_name: str) -> float:[m
[32m+[m[32m        """[m
[32m+[m[32m        Calcula un score para una respuesta basada en su longitud, calidad (número de oraciones)[m
[32m+[m[32m        y el peso configurado de la IA.[m
[32m+[m[32m        """[m
[32m+[m[32m        if not isinstance(response_content, str) or not response_content.strip():[m
[32m+[m[32m            return 0.0[m
[32m+[m
[32m+[m[32m        # Score basado en longitud: más largo es generalmente mejor, hasta cierto punto[m
[32m+[m[32m        length_score = len(response_content) / 100.0 # Normalizar por una base[m
[32m+[m
[32m+[m[32m        # Score basado en calidad (número de oraciones): usar puntuación para estimar[m
[32m+[m[32m        sentence_count = response_content.count('.') + response_content.count('!') + response_content.count('?')[m
[32m+[m[32m        quality_score = sentence_count * 0.5 # Cada oración contribuye a la calidad[m
[32m+[m
[32m+[m[32m        # Aplicar el peso de la IA[m
[32m+[m[32m        ai_weight = self.ai_weights.get(ai_name, 1.0)[m
[32m+[m
[32m+[m[32m        # Combinar scores y aplicar peso[m
[32m+[m[32m        total_score = (length_score + quality_score) * ai_weight[m
[32m+[m[32m        return total_score[m
[32m+[m
     def get_consensus(self, responses: List[Tuple[str, Any]]) -> Optional[str]:[m
         """[m
[31m-        Combina las respuestas de las IAs utilizando un algoritmo de votación ponderada.[m
[32m+[m[32m        Selecciona la "mejor" respuesta de las IAs utilizando un algoritmo de scoring ponderado.[m
 [m
         Args:[m
             responses (List[Tuple[str, Any]]): Lista de tuplas (nombre_ia, respuesta_ia).[m
[31m-                                                Las respuestas pueden ser de cualquier tipo,[m
[31m-                                                pero se espera que sean strings para el consenso.[m
[32m+[m[32m                                                Las respuestas deben ser strings para ser evaluadas.[m
 [m
         Returns:[m
[31m-            Optional[str]: El resultado del consenso como string, o None si no hay respuestas válidas.[m
[32m+[m[32m            Optional[str]: La respuesta con el score más alto, o None si no hay respuestas válidas.[m
         """[m
         if not responses:[m
             logging.warning("No hay respuestas para generar consenso.")[m
             return None[m
 [m
[31m-        # Para simplificar, asumimos que las respuestas son strings y las concatenamos[m
[31m-        # En un caso real, se necesitaría una lógica más sofisticada (ej. sumar scores,[m
[31m-        # votar por la mejor respuesta, resumir, etc.)[m
[32m+[m[32m        scored_responses: List[Tuple[float, str]] = [][m
 [m
[31m-        weighted_responses = [][m
         for ai_name, response_content in responses:[m
[31m-            weight = self.ai_weights.get(ai_name, 1.0) # Usar peso configurado, default 1.0[m
             if isinstance(response_content, str):[m
[31m-                weighted_responses.extend([response_content] * int(weight * 10)) # Multiplicar por 10 para tener más "votos"[m
[32m+[m[32m                score = self._calculate_response_score(response_content, ai_name)[m
[32m+[m[32m                if score > 0: # Solo considerar respuestas con score positivo[m
[32m+[m[32m                    scored_responses.append((score, response_content))[m
[32m+[m[32m                    logging.debug(f"Respuesta de '{ai_name}' obtuvo score: {score:.2f}")[m
             else:[m
[31m-                logging.warning(f"Respuesta de '{ai_name}' no es string, no se incluye en el consenso simple.")[m
[32m+[m[32m                logging.warning(f"Respuesta de '{ai_name}' no es string, no se incluye en la evaluación de consenso.")[m
 [m
[31m-        if not weighted_responses:[m
[31m-            logging.warning("No hay respuestas válidas para el consenso ponderado.")[m
[32m+[m[32m        if not scored_responses:[m
[32m+[m[32m            logging.warning("No hay respuestas válidas con score positivo para el consenso.")[m
             return None[m
 [m
[31m-        # Un enfoque simple: unir las respuestas ponderadas[m
[31m-        final_consensus = " ".join(weighted_responses)[m
[31m-        logging.info(f"Consenso generado a partir de {len(responses)} respuestas.")[m
[31m-        return final_consensus.strip()[m
[32m+[m[32m        # Seleccionar la respuesta con el score más alto[m
[32m+[m[32m        best_response_score, best_response_content = max(scored_responses, key=lambda item: item[0])[m
[32m+[m
[32m+[m[32m        logging.info(f"Consenso generado: seleccionada la mejor respuesta con score: {best_response_score:.2f}.")[m
[32m+[m[32m        return best_response_content.strip()[m
 [m
 class AIOrchestrator:[m
     """[m
[1mdiff --git a/main.py b/main.py[m
[1mindex b19fbc1..786fb99 100644[m
[1m--- a/main.py[m
[1m+++ b/main.py[m
[36m@@ -1,5 +1,6 @@[m
 import logging[m
 import asyncio[m
[32m+[m[32mimport time # Importar el módulo time[m
 from typing import List, Dict[m
 from pydantic import ValidationError[m
 from publishers.supabase_client import SupabaseClient, Article[m
[36m@@ -32,6 +33,11 @@[m [masync def main_workflow():[m
         logging.info(f"Se procesarán {len(CONTENT_SOURCES)} fuentes de contenido.")[m
 [m
         for source_info in CONTENT_SOURCES:[m
[32m+[m[32m            start_time = time.time() # Iniciar contador de tiempo por fuente[m
[32m+[m[32m            articles_found = 0[m
[32m+[m[32m            new_articles_count = 0[m
[32m+[m[32m            ai_processed_count = 0[m
[32m+[m
             source_name, feed_url = source_info["name"], source_info["url"][m
             logging.info(f"\n--- Procesando fuente: {source_name} ---")[m
 [m
[36m@@ -40,65 +46,116 @@[m [masync def main_workflow():[m
                 logging.warning(f"No se encontraron artículos en {source_name}. Saltando.")[m
                 continue[m
 [m
[31m-            logging.info(f"Se encontraron {len(feed_data.entries)} artículos. Validando y guardando...")[m
[32m+[m[32m            articles_found = len(feed_data.entries)[m
[32m+[m[32m            logging.info(f"Se encontraron {articles_found} artículos. Preparando para procesamiento por lotes...")[m
 [m
[32m+[m[32m            # 2. Recolectar todos los artículos potenciales y sus URLs[m
[32m+[m[32m            potential_articles: List[Article] = [][m
[32m+[m[32m            potential_urls: List[str] = [][m
             for entry in reversed(feed_data.entries):[m
                 try:[m
                     if hasattr(entry, 'link') and entry.link:[m
[31m-                        # 2. Guardar el artículo base para ver si es nuevo[m
                         article = Article([m
                             title=getattr(entry, 'title', 'Sin Título'),[m
                             url=entry.link,[m
                             content=getattr(entry, 'summary', 'Sin Resumen'),[m
                             source=source_name[m
                         )[m
[31m-                        is_new = supabase_client.save_article(article)[m
[31m-[m
[31m-                        # 3. SI Y SOLO SI el artículo es nuevo, lo procesamos con la IA[m
[31m-                        if is_new:[m
[31m-                            logging.info(f"Artículo nuevo: '{article.title}'. Obteniendo contenido completo para la IA...")[m
[31m-                            full_content = scraper.fetch_article_content(str(article.ur