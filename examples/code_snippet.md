---
template: note
title: Python Snippet - Decorator
tags: [python, code]
---

## Decorator Pattern

```python
import functools
import time

def timer(func):
    """Time execution of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} took {end - start:.4f}s")
        return result
    return wrapper

@timer
def slow_function(n):
    """Simulate slow computation."""
    total = 0
    for i in range(n):
        total += i ** 2
    return total

result = slow_function(1000000)
```