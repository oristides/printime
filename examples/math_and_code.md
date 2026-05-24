---
template: note
title: Calculus Cheatsheet
tags: [math, calculus, equations]
---

## Derivatives

**Power Rule:** $\frac{d}{dx}[x^n] = nx^{n-1}$

**Product Rule:** $\frac{d}{dx}[f \cdot g] = f' \cdot g + f \cdot g'$

**Quotient Rule:** $\frac{d}{dx}\left[\frac{f}{g}\right] = \frac{f' \cdot g - f \cdot g'}{g^2}$

**Chain Rule:** $\frac{d}{dx}[f(g(x))] = f'(g(x)) \cdot g'(x)$

## Integrals

**Power Rule:** $\int x^n \, dx = \frac{x^{n+1}}{n+1} + C$

**Integration by Parts:** $\int u \, dv = uv - \int v \, du$

## Common Identities

**Euler's Formula:** $e^{i\theta} = \cos\theta + i\sin\theta$

**Taylor Series:** $f(x) = \sum_{n=0}^{\infty} \frac{f^{(n)}(a)}{n!}(x-a)^n$

## Example Code

```python
import sympy as sp

x = sp.Symbol('x')
f = x**3 + 2*x**2 - 5*x + 1

# First derivative
f_prime = sp.diff(f, x)
print(f"f'(x) = {f_prime}")

# Integral
F = sp.integrate(f, x)
print(f"∫f(x)dx = {F} + C")
```