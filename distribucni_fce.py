import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

# Nastavení vzhledu grafů
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# ---------------------------------------------------------
# 1. GRAF: Diskrétní náhodná veličina (Hod férovou kostkou)
# ---------------------------------------------------------
x_disc = np.array([0, 1, 2, 3, 4, 5, 6, 7])
# Kumulativní pravděpodobnosti pro hodnoty 0 až 7
y_disc = np.array([0, 1/6, 2/6, 3/6, 4/6, 5/6, 1.0, 1.0])

# Vykreslení "schodů"
ax1.step(x_disc, y_disc, where='post', color="#364652", linewidth=2.5, label='$F_X(t)$')

# Vykreslení plných a prázdných bodů pro znázornění spojitosti zprava
for i in range(1, 7):
    ax1.plot(x_disc[i], y_disc[i-1], 'o', color='#1f77b4', markerfacecolor='white', markersize=6) # Prázdný bod (zleva)
    ax1.plot(x_disc[i], y_disc[i], 'o', color='#1f77b4', markersize=6) # Plný bod (zprava)

ax1.set_title('Diskrétní veličina (Hod kostkou)', fontsize=14, fontweight='bold')
ax1.set_xlabel('Hodnota $t$', fontsize=12)
ax1.set_ylabel('$F_X(t) = P(X \leq t)$', fontsize=12)
ax1.set_xlim(-0.5, 7.5)
ax1.set_ylim(-0.05, 1.05)
ax1.set_yticks([0, 1/6, 2/6, 3/6, 4/6, 5/6, 1.0])
ax1.set_yticklabels(['0', '1/6', '2/6', '3/6', '4/6', '5/6', '1'])

# ---------------------------------------------------------
# 2. GRAF: Spojitá náhodná veličina (Normální rozdělení)
# ---------------------------------------------------------
# Generování dat pro Gaussovu křivku (střední hodnota = 0, směrná odchylka = 1)
x_cont = np.linspace(-3.5, 3.5, 500)
y_cont = norm.cdf(x_cont)

ax2.plot(x_cont, y_cont, color='#e377c2', linewidth=3, label='$F_X(t)$')

ax2.set_title('Spojitá veličina (Normální rozdělení)', fontsize=14, fontweight='bold')
ax2.set_xlabel('Hodnota $t$', fontsize=12)
ax2.set_ylabel('$F_X(t) = P(X \leq t)$', fontsize=12)
ax2.set_xlim(-3.5, 3.5)
ax2.set_ylim(-0.05, 1.05)

# Zvýraznění asymptot (0 a 1)
for ax in [ax1, ax2]:
    ax.axhline(0, color='black', linestyle='--', alpha=0.5)
    ax.axhline(1, color='black', linestyle='--', alpha=0.5)
    ax.legend(loc='lower right', fontsize=12)

plt.tight_layout()
plt.show()