import logging
from typing import Dict, List, Any
import random

class PromptOptimizer:
    def __init__(self):
        self.prompt_variations = {
            'technical_analysis': [
                {
                    'name': 'technical_deep_dive',
                    'template': """
                    Como ingeniero senior de IA, analiza técnicamente: {topic}

                    PROFUNDIDAD TÉCNICA: Explica arquitecturas, algoritmos, implementación
                    ESTRUCTURA: Problema → Solución → Implementación → Resultados
                    LONGITUD: 800-1200 palabras
                    TONO: Técnico pero accesible
                    INCLUYE ESTAS PALABRAS CLAVE: artificial intelligence, machine learning, AI, technology, data, model
                    """,
                    'performance': {'success_rate': 0.0, 'avg_quality': 0.0}
                },
                {
                    'name': 'business_impact',
                    'template': """
                    Como estratega de tecnología, analiza: {topic}

                    ENFOQUE: Impacto empresarial, ROI, casos de uso reales
                    ESTRUCTURA: Oportunidad → Solución → Beneficios → Implementación
                    LONGITUD: 800-1200 palabras
                    TONO: Ejecutivo, orientado a negocio
                    INCLUYE ESTAS PALABRAS CLAVE: artificial intelligence, machine learning, AI, technology, data, model
                    """,
                    'performance': {'success_rate': 0.0, 'avg_quality': 0.0}
                }
            ],
            'tutorial': [
                {
                    'name': 'step_by_step',
                    'template': """
                    Crea un tutorial paso a paso sobre: {topic}

                    ESTRUCTURA: Introducción → Prerrequisitos → Pasos detallados → Ejemplos
                    INCLUYE: Código ejemplos, mejores prácticas, troubleshooting
                    LONGITUD: 800-1200 palabras
                    TONO: Instructivo, claro
                    INCLUYE ESTAS PALABRAS CLAVE: artificial intelligence, machine learning, AI, technology, data, model
                    """,
                    'performance': {'success_rate': 0.0, 'avg_quality': 0.0}
                }
            ]
        }

    def get_optimized_prompt(self, topic: str, content_type: str) -> str:
        """Selecciona la mejor variación de prompt basado en performance"""
        variations = self.prompt_variations.get(content_type, [])

        if not variations:
            return self._get_default_prompt(topic)

        # Por ahora selección aleatoria, luego basado en performance
        selected = random.choice(variations)
        logging.info(f"Usando prompt variation: {selected['name']}")

        return selected['template'].format(topic=topic)

    def update_performance(self, prompt_name: str, quality_score: float, success: bool):
        """Actualiza métricas de performance del prompt"""
        for category in self.prompt_variations.values():
            for prompt in category:
                if prompt['name'] == prompt_name:
                    prompt['performance']['success_rate'] = (
                        (prompt['performance']['success_rate'] + (1 if success else 0)) / 2
                    )
                    prompt['performance']['avg_quality'] = (
                        (prompt['performance']['avg_quality'] + quality_score) / 2
                    )
                    break

    def _get_default_prompt(self, topic: str) -> str:
        """Prompt por defecto si no hay variaciones"""
        return f"""
        Escribe un artículo completo de 800-1200 palabras sobre: {topic}

        ESTRUCTURA: Introducción → Desarrollo → Conclusión
        TONO: Profesional pero accesible
        INCLUYE: Ejemplos, datos, perspectivas futuras
        INCLUYE ESTAS PALABRAS CLAVE: artificial intelligence, machine learning, AI, technology, data, model
        """
