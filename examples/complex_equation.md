---
template: equation
title: Neural Network Gradient Descent
tags: [ml, math, code]
---

## Gradient Descent Algorithm

The weight update rule:

```python
weights = weights - learning_rate * gradient
```

### Cost Function

$$J(\theta) = \frac{1}{2m} \sum_{i=1}^{m} (h_\theta(x^{(i)}) - y^{(i)})^2$$

### Partial Derivative

$$\frac{\partial J(\theta)}{\partial \theta_j} = \frac{1}{m} \sum_{i=1}^{m} (h_\theta(x^{(i)}) - y^{(i)}) \cdot x_j^{(i)}$$

### Matrix Form

$$\nabla_\theta J = \frac{2}{m} \cdot X^T \cdot (X \cdot \theta - \vec{y})$$