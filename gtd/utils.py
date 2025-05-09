

import time
import json 


class ExponentialBackoff:
    """
    A class to implement exponential backoff for retrying operations.
    """

    def __init__(self, base_delay=1, max_delay=60, max_retries=5):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries

    def get_delay(self, attempt):
        """
        Calculate the delay for the given attempt.
        """
        max_attempt = min(attempt, self.max_retries)
        delay = min(self.base_delay * (2 ** max_attempt), self.max_delay)
        return delay
    def wait(self, attempt):
        """
        Wait for the calculated delay before retrying.
        """
        delay = self.get_delay(attempt)
        time.sleep(delay)
    def retry(self, func, *args, **kwargs):
        """
        Retry the given function with exponential backoff.
        """
        attempt = 0
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                self.wait(attempt)
                attempt += 1
                if attempt >= self.max_retries:
                    print("Max retries reached. Giving up.")
                    raise
                print(f"Retrying in {self.get_delay(attempt)} seconds...")
                continue
    def __call__(self, func):
        """
        Decorator to apply exponential backoff to a function.
        """
        def wrapper(*args, **kwargs):
            return self.retry(func, *args, **kwargs)
        return wrapper
    


