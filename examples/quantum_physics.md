---
template: equation
title: Quantum Entanglement
tags: [physics, quantum]
---

## Bell's Theorem

The Bell inequality violation:

$$|\langle AB \rangle - \langle AC \rangle| \leq 2\sqrt{m(1-m)}$$

### CHSH Inequality

$$\langle S \rangle = \langle A_1B_1 \rangle + \langle A_1B_2 \rangle + \langle A_2B_1 \rangle - \langle A_2B_2 \rangle$$

Maximum violation for maximally entangled qubits:

$$|\langle S \rangle| \leq 2\sqrt{2}$$

### Density Matrix Representation

$$\rho = \frac{1}{2}\begin{pmatrix} 1+p_z & p_x-ip_y \\ p_x+ip_y & 1-p_z \end{pmatrix}$$

### Von Neumann Entropy

$$S(\rho) = -\text{Tr}(\rho \log_2 \rho) = -\sum_i \lambda_i \log_2 \lambda_i$$