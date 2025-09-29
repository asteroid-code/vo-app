import time
import logging

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False
        logging.info(f"Circuit Breaker '{self.name}' initialized with threshold={failure_threshold}, timeout={recovery_timeout}")

    def _open(self):
        self.is_open = True
        self.last_failure_time = time.time()
        logging.warning(f"Circuit Breaker '{self.name}' OPENED due to {self.failures} failures.")

    def _close(self):
        self.is_open = False
        self.failures = 0
        self.last_failure_time = None
        logging.info(f"Circuit Breaker '{self.name}' CLOSED. Resetting failure count.")

    def record_failure(self):
        self.failures += 1
        logging.warning(f"Circuit Breaker '{self.name}' recorded failure. Total failures: {self.failures}")
        if self.failures >= self.failure_threshold and not self.is_open:
            self._open()

    def record_success(self):
        if self.is_open:
            # If in open state, a success means it's recovering
            logging.info(f"Circuit Breaker '{self.name}' recorded success during open state. Attempting to close.")
            self._close()
        elif self.failures > 0:
            # If in closed state but had failures, reset them on success
            self.failures = 0
            logging.info(f"Circuit Breaker '{self.name}' recorded success. Resetting failure count.")

    def allow_request(self) -> bool:
        if not self.is_open:
            return True

        # If open, check if recovery timeout has passed
        if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
            logging.info(f"Circuit Breaker '{self.name}' in half-open state. Allowing a single request for testing.")
            # Allow one request to try and close the circuit
            return True

        logging.warning(f"Circuit Breaker '{self.name}' is OPEN. Request blocked.")
        return False

    def reset(self):
        """Manually resets the circuit breaker to a closed state."""
        if self.is_open:
            self._close()
            logging.info(f"Circuit Breaker '{self.name}' manually reset to CLOSED.")
        else:
            logging.info(f"Circuit Breaker '{self.name}' was already CLOSED. No action needed.")
