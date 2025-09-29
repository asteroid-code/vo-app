import logging
from typing import Dict, Any, Tuple

class QualityController:
    def __init__(self):
        self.min_word_count = 600
        self.max_word_count = 1500
        self.min_sentence_count = 15
        self.required_keywords = ['artificial intelligence', 'machine learning', 'technology', 'AI', 'intelligence', 'learning', 'model', 'data']

    def analyze_content_quality(self, content: str, title: str) -> Tuple[bool, Dict[str, Any]]:
        """Analiza la calidad del contenido y retorna si pasa + métricas"""
        metrics = {
            'word_count': len(content.split()),
            'sentence_count': content.count('.') + content.count('!') + content.count('?'),
            'paragraph_count': content.count('\n\n') + 1,
            'keyword_density': self._calculate_keyword_density(content),
            'readability_score': self._calculate_readability(content)
        }

        # Verificar criterios de calidad
        passes_quality = (
            metrics['word_count'] >= self.min_word_count and
            metrics['word_count'] <= self.max_word_count and
            metrics['sentence_count'] >= self.min_sentence_count and
            metrics['keyword_density'] >= 0.02  # Al menos 2% de keywords relevantes
        )

        quality_report = {
            'passes_quality': passes_quality,
            'metrics': metrics,
            'issues': self._identify_issues(metrics) if not passes_quality else []
        }

        return passes_quality, quality_report

    def _calculate_keyword_density(self, content: str) -> float:
        """Calcula densidad de keywords relevantes"""
        content_lower = content.lower()
        total_words = len(content.split())
        if total_words == 0:
            return 0

        keyword_count = sum(content_lower.count(keyword) for keyword in self.required_keywords)
        return keyword_count / total_words

    def _calculate_readability(self, content: str) -> float:
        """Calcula score de legibilidad simplificado"""
        sentences = content.count('.') + content.count('!') + content.count('?')
        words = len(content.split())

        if sentences == 0 or words == 0:
            return 0

        avg_sentence_length = words / sentences
        # Score más alto = más legible (oraciones más cortas)
        return max(0, 20 - (avg_sentence_length / 5))

    def _identify_issues(self, metrics: Dict[str, Any]) -> list:
        """Identifica problemas específicos en el contenido"""
        issues = []

        if metrics['word_count'] < self.min_word_count:
            issues.append(f"Contenido muy corto: {metrics['word_count']} palabras")
        if metrics['word_count'] > self.max_word_count:
            issues.append(f"Contenido muy largo: {metrics['word_count']} palabras")
        if metrics['sentence_count'] < self.min_sentence_count:
            issues.append(f"Muy pocas oraciones: {metrics['sentence_count']}")
        if metrics['keyword_density'] < 0.02:
            issues.append(f"Baja densidad de keywords: {metrics['keyword_density']:.2%}")

        return issues
