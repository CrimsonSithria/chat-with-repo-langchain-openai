def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.
    
    Args:
        n: The position in the Fibonacci sequence
        
    Returns:
        The nth Fibonacci number
    """
    if n <= 0:
        raise ValueError("n must be positive")
    elif n == 1 or n == 2:
        return 1
    
    a, b = 1, 1
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b

def is_prime(n: int) -> bool:
    """Check if a number is prime.
    
    Args:
        n: The number to check
        
    Returns:
        True if the number is prime, False otherwise
    """
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True

class MathUtils:
    """A collection of mathematical utility functions."""
    
    @staticmethod
    def factorial(n: int) -> int:
        """Calculate the factorial of n.
        
        Args:
            n: The number to calculate factorial for
            
        Returns:
            The factorial of n
        """
        if n < 0:
            raise ValueError("n must be non-negative")
        if n == 0:
            return 1
        return n * MathUtils.factorial(n - 1) 