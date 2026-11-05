import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ── Cargar datos ──────────────────────────────────────────────
url = "https://archive.ics.uci.edu/ml/machine-learning-databases/forest-fires/forestfires.csv"
df = pd.read_csv(url)

# ── Variable objetivo binaria ─────────────────────────────────
df["incendio"] = (df["area"] > 0).astype(int)

print("Distribución de clases:")
print(df["incendio"].value_counts(normalize=True))

# ── Estadísticas descriptivas de las variables clave ─────────
print(df[["temp", "RH", "wind", "rain", "FFMC", "DMC", "DC", "ISI"]].describe())

# ── Correlación con la variable objetivo ─────────────────────
correlaciones = df.corr(numeric_only=True)["incendio"].sort_values(ascending=False)
print(correlaciones)

# ── Visualización rápida ─────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
sns.boxplot(x="incendio", y="temp", data=df, ax=axes[0]).set_title("Temperatura vs incendio")
sns.boxplot(x="incendio", y="RH", data=df, ax=axes[1]).set_title("Humedad relativa vs incendio")
sns.boxplot(x="incendio", y="FFMC", data=df, ax=axes[2]).set_title("FFMC vs incendio")
plt.tight_layout()
plt.show()