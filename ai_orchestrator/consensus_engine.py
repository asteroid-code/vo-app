import asyncio
import httpx
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cargar variables de entorno
load_dotenv()

class CircuitBreaker:
    """
    Implementa el patrón Circuit Breaker para gestionar la resiliencia de las APIs.

    Estados:
    - CLOSED: Las llamadas pasan normalmente. Si hay fallos, se incrementa el contador.
              Si los fallos superan un umbral, pasa a OPEN.
    - OPEN: Las llamadas son bloqueadas inmediatamente. Después de un tiempo de espera,
            pasa a HALF-OPEN.
    - HALF_OPEN: Se permite una única llamada de prueba. Si tiene éxito, pasa a CLOSED.
                 Si falla, vuelve a OPEN.
    """

    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout: int = 60, reset_timeout: int = 300):
        """
        Inicializa un Circuit Breaker.

        Args:
            name (str): Nombre del servicio al que protege el Circuit Breaker.
            failure_threshold (int): Número de fallos consecutivos para abrir el circuito.
            recovery_timeout (int): Tiempo en segundos que el circuito permanece en estado OPEN.
            reset_timeout (int): Tiempo en segundos para resetear el contador de fallos si hay éxito.
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.reset_timeout = reset_timeout

        self._state = "CLOSED"
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._last_success_time = 0.0

        logging.info(f"Circuit Breaker '{self.name}' inicializado en estado CLOSED.")

    def _set_state(self, state: str):
        """Cambia el estado del Circuit Breaker y registra el cambio."""
        if self._state != state:
            logging.warning(f"Circuit Breaker '{self.name}' cambia de estado: {self._state} -> {state}")
            self._state = state

    def is_open(self) -> bool:
        """Verifica si el Circuit Breaker está en estado OPEN."""
        return self._state == "OPEN"

    def is_half_open(self) -> bool:
        """Verifica si el Circuit Breaker está en estado HALF-OPEN."""
        return self._state == "HALF_OPEN"

    def before_request(self) -> bool:
        """
        Llamado antes de realizar una petición.
        Determina si la petición debe proceder o ser bloqueada.

        Returns:
            bool: True si la petición puede proceder, False si debe ser bloqueada.
        """
        if self._state == "OPEN":
            if time.time() - self._last_failure_time > self.recovery_timeout:
                self._set_state("HALF_OPEN")
                logging.info(f"Circuit Breaker '{self.name}' intentando recuperación (HALF-OPEN).")
                return True  # Permitir una prueba
            logging.warning(f"Circuit Breaker '{self.name}' está OPEN. Petición bloqueada.")
            return False
        elif self._state == "HALF_OPEN":
            # Solo una petición de prueba a la vez
            return True
        return True  # CLOSED

    def on_success(self):
        """Llamado cuando una petición es exitosa."""
        self._last_success_time = time.time()
        if self._state == "HALF_OPEN":
            self._set_state("CLOSED")
            self._failure_count = 0
            logging.info(f"Circuit Breaker '{self.name}' recuperado y en estado CLOSED.")
        elif self._state == "CLOSED":
            # Resetear el contador de fallos si ha pasado suficiente tiempo desde el último éxito
            if time.time() - self._last_failure_time > self.reset_timeout:
                self._failure_count = 0

    def on_failure(self):
        """Llamado cuando una petición falla."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        logging.error(f"Circuit Breaker '{self.name}' - Fallo detectado. Fallos consecutivos: {self._failure_count}")

        if self._state == "HALF_OPEN":
            self._set_state("OPEN")
            logging.error(f"Circuit Breaker '{self.name}' falló en HALF-OPEN, volviendo a OPEN.")
        elif self._state == "CLOSED" and self._failure_count >= self.failure_threshold:
            self._set_state("OPEN")
            logging.error(f"Circuit Breaker '{self.name}' abierto debido a {self._failure_count} fallos consecutivos.")

    def get_status(self) -> Dict[str, Any]:
        """Retorna el estado actual del Circuit Breaker."""
        return {
            "name": self.name,
            "state": self._state,
            "failure_count": self._failure_count,
            "last_failure_time": self._last_failure_time,
            "last_success_time": self._last_success_time,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }

class AIConfig(BaseModel):
    """Modelo Pydantic para la configuración de cada IA."""
    name: str
    url: str
    api_key_env: str  # Nombre de la variable de entorno para la clave API
    weight: float = 1.0
    tier: int = Field(..., ge=1, le=3) # Tier 1, 2 o 3

class OrchestratorConfig(BaseModel):
    """Modelo Pydantic para la configuración general del orquestador."""
    ai_services: List[AIConfig]
    timeout_per_ai: int = 30
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_recovery_timeout: int = 60
    circuit_breaker_reset_timeout: int = 300

class ConsensusEngine:
    """
    Motor de consenso que combina las respuestas de múltiples IAs.
    """
    def __init__(self, ai_configs: List[AIConfig]):
        """
        Inicializa el motor de consenso con las configuraciones de las IAs.

        Args:
            ai_configs (List[AIConfig]): Lista de configuraciones de las IAs, incluyendo sus pesos.
        """
        self.ai_weights = {config.name: config.weight for config in ai_configs}
        logging.info("Consensus Engine inicializado con pesos de IA.")

    def get_consensus(self, responses: List[Tuple[str, Any]]) -> Optional[str]:
        """
        Combina las respuestas de las IAs utilizando un algoritmo de votación ponderada.

        Args:
            responses (List[Tuple[str, Any]]): Lista de tuplas (nombre_ia, respuesta_ia).
                                                Las respuestas pueden ser de cualquier tipo,
                                                pero se espera que sean strings para el consenso.

        Returns:
            Optional[str]: El resultado del consenso como string, o None si no hay respuestas válidas.
        """
        if not responses:
            logging.warning("No hay respuestas para generar consenso.")
            return None

        # Para simplificar, asumimos que las respuestas son strings y las concatenamos
        # En un caso real, se necesitaría una lógica más sofisticada (ej. sumar scores,
        # votar por la mejor respuesta, resumir, etc.)

        weighted_responses = []
        for ai_name, response_content in responses:
            weight = self.ai_weights.get(ai_name, 1.0) # Usar peso configurado, default 1.0
            if isinstance(response_content, str):
                weighted_responses.extend([response_content] * int(weight * 10)) # Multiplicar por 10 para tener más "votos"
            else:
                logging.warning(f"Respuesta de '{ai_name}' no es string, no se incluye en el consenso simple.")

        if not weighted_responses:
            logging.warning("No hay respuestas válidas para el consenso ponderado.")
            return None

        # Un enfoque simple: unir las respuestas ponderadas
        final_consensus = " ".join(weighted_responses)
        logging.info(f"Consenso generado a partir de {len(responses)} respuestas.")
        return final_consensus.strip()

class AIOrchestrator:
    """
    Orquestador principal que gestiona las llamadas a múltiples APIs de IA,
    Circuit Breakers y el motor de consenso.
    """
    def __init__(self, config: OrchestratorConfig):
        """
        Inicializa el orquestador con la configuración proporcionada.

        Args:
            config (OrchestratorConfig): Objeto de configuración del orquestador.
        """
        self.config = config
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(config.timeout_per_ai))
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.ai_api_keys: Dict[str, str] = {}

        for ai_config in config.ai_services:
            self.circuit_breakers[ai_config.name] = CircuitBreaker(
                name=ai_config.name,
                failure_threshold=config.circuit_breaker_failure_threshold,
                recovery_timeout=config.circuit_breaker_recovery_timeout,
                reset_timeout=config.circuit_breaker_reset_timeout
            )
            api_key = os.getenv(ai_config.api_key_env)
            if not api_key:
                logging.error(f"API Key para {ai_config.name} ({ai_config.api_key_env}) no encontrada en .env")
                # Considerar abrir el circuit breaker si la clave no está presente
                self.circuit_breakers[ai_config.name].on_failure()
            self.ai_api_keys[ai_config.name] = api_key or "DUMMY_KEY" # Usar dummy para pruebas si no existe

        self.consensus_engine = ConsensusEngine(config.ai_services)
        logging.info("AIOrchestrator inicializado.")

    async def _call_ai_service(self, ai_config: AIConfig, prompt: str) -> Optional[Any]:
        """
        Realiza una llamada asíncrona a una API de IA, gestionando Circuit Breakers y timeouts.

        Args:
            ai_config (AIConfig): Configuración de la IA a llamar.
            prompt (str): El prompt a enviar a la IA.

        Returns:
            Optional[Any]: La respuesta de la IA si es exitosa, None en caso de fallo.
        """
        cb = self.circuit_breakers[ai_config.name]

        if not cb.before_request():
            logging.info(f"Petición a '{ai_config.name}' bloqueada por Circuit Breaker (OPEN).")
            return None

        try:
            # Simulación de llamada a API. En un caso real, aquí iría la lógica específica
            # para cada API (headers, body, endpoint, etc.).
            # Para este ejemplo, solo simulamos una respuesta.
            logging.info(f"Llamando a '{ai_config.name}' (Tier {ai_config.tier})...")

            # Simular un fallo aleatorio para probar el Circuit Breaker
            if ai_config.name == "Groq" and time.time() % 5 < 2: # Groq falla 40% de las veces
                raise httpx.RequestError("Simulated network error for Groq")
            if ai_config.name == "OpenAI" and time.time() % 7 < 1: # OpenAI falla ~14% de las veces
                raise httpx.TimeoutException("Simulated timeout for OpenAI")

            await asyncio.sleep(0.5 + (ai_config.tier * 0.2)) # Simular latencia

            response_data = {"content": f"Respuesta de {ai_config.name} para: '{prompt}'"}

            cb.on_success()
            logging.info(f"'{ai_config.name}' respondió con éxito.")
            return response_data["content"] # Retornar solo el contenido para el consenso

        except httpx.TimeoutException:
            logging.error(f"Timeout al llamar a '{ai_config.name}'.")
            cb.on_failure()
        except httpx.RequestError as e:
            logging.error(f"Error de red/petición al llamar a '{ai_config.name}': {e}")
            cb.on_failure()
        except Exception as e:
            logging.error(f"Error inesperado al llamar a '{ai_config.name}': {e}")
            cb.on_failure()

        return None

    async def get_consensus(self, prompt: str) -> Optional[str]:
        """
        Orquesta las llamadas a todas las APIs de IA y genera un consenso.

        Args:
            prompt (str): El prompt a enviar a todas las IAs.

        Returns:
            Optional[str]: El resultado del consenso, o None si no se pudo generar.
        """
        tasks = []
        active_ai_configs = []

        for ai_config in self.config.ai_services:
            cb = self.circuit_breakers[ai_config.name]
            if not cb.is_open(): # Solo considerar IAs que no estén en estado OPEN
                tasks.append(self._call_ai_service(ai_config, prompt))
                active_ai_configs.append(ai_config)
            else:
                logging.info(f"'{ai_config.name}' está en estado OPEN, no se realizará la llamada.")

        if not tasks:
            logging.error("No hay APIs de IA disponibles para procesar la petición.")
            return None

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_responses: List[Tuple[str, Any]] = []
        for i, result in enumerate(results):
            ai_name = active_ai_configs[i].name
            if not isinstance(result, Exception) and result is not None:
                successful_responses.append((ai_name, result))
            else:
                logging.error(f"'{ai_name}' falló o no retornó una respuesta válida en la orquestación.")

        if not successful_responses:
            logging.error("Ninguna IA respondió con éxito. No se puede generar consenso.")
            return None

        logging.info(f"Respuestas exitosas recibidas de {len(successful_responses)} IAs.")
        final_consensus = self.consensus_engine.get_consensus(successful_responses)

        if final_consensus:
            logging.info("Consenso generado con éxito.")
        else:
            logging.warning("No se pudo generar un consenso significativo.")

        return final_consensus

    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Retorna el estado actual de todos los Circuit Breakers."""
        return {name: cb.get_status() for name, cb in self.circuit_breakers.items()}

# --- Ejemplo de Configuración SIMPLIFICADO PARA PRUEBAS ---
EXAMPLE_CONFIG_DICT = {
    "ai_services": [
        {"name": "Groq", "url": "https://api.groq.com/v1/chat/completions", "api_key_env": "GROQ_API_KEY", "weight": 1.0, "tier": 1},
        {"name": "OpenAI", "url": "https://api.openai.com/v1/chat/completions", "api_key_env": "OPENAI_API_KEY", "weight": 2.0, "tier": 3},
    ],
    "timeout_per_ai": 30,
    "circuit_breaker_failure_threshold": 2,
    "circuit_breaker_recovery_timeout": 60,
    "circuit_breaker_reset_timeout": 300
}

# --- Ejemplo de Uso ---
if __name__ == "__main__":
    async def main():
        logging.info("Iniciando demostración del AIOrchestrator...")

        # Crear una instancia del orquestador
        config = OrchestratorConfig(**EXAMPLE_CONFIG_DICT)
        orchestrator = AIOrchestrator(config)

        test_prompt = "¿Cuál es la capital de Francia?"

        # Simular múltiples llamadas para probar Circuit Breakers y consenso
        logging.info("\n--- Primera ronda de llamadas (esperando algunos fallos) ---")
        for _ in range(5):
            consensus_result = await orchestrator.get_consensus(test_prompt)
            if consensus_result:
                logging.info(f"Resultado del consenso: {consensus_result[:100]}...")
            else:
                logging.warning("No se obtuvo consenso en esta ronda.")

            status = orchestrator.get_orchestrator_status()
            for ai_name, cb_status in status.items():
                logging.info(f"  CB '{ai_name}' estado: {cb_status['state']}, fallos: {cb_status['failure_count']}")
            await asyncio.sleep(1) # Pequeña pausa entre rondas

        logging.info("\n--- Esperando recuperación de Circuit Breakers (recovery_timeout) ---")
        await asyncio.sleep(orchestrator.config.circuit_breaker_recovery_timeout + 5) # Esperar más allá del timeout

        logging.info("\n--- Segunda ronda de llamadas (esperando recuperación) ---")
        for _ in range(3):
            consensus_result = await orchestrator.get_consensus(test_prompt)
            if consensus_result:
                logging.info(f"Resultado del consenso: {consensus_result[:100]}...")
            else:
                logging.warning("No se obtuvo consenso en esta ronda.")

            status = orchestrator.get_orchestrator_status()
            for ai_name, cb_status in status.items():
                logging.info(f"  CB '{ai_name}' estado: {cb_status['state']}, fallos: {cb_status['failure_count']}")
            await asyncio.sleep(1)

        logging.info("\n--- Demostración finalizada ---")

    asyncio.run(main())
