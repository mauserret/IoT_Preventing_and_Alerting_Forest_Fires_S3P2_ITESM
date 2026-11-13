import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import StandardScaler

# 1. Cargar datos
url = "https://archive.ics.uci.edu/ml/machine-learning-databases/forest-fires/forestfires.csv"
df = pd.read_csv(url)
df["incendio"] = (df["area"] > 0).astype(int)

# 2. Seleccionar TODAS las variables predictoras
features = ["temp", "RH", "wind", "rain", "FFMC", "DMC", "DC", "ISI"]
X = df[features]
y = df["incendio"]

# 3. División y Escalado
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 4. Entrenar Random Forest con más estimadores
rf_fuerte = RandomForestClassifier(n_estimators=300, max_depth=10, random_state=42, class_weight='balanced')
rf_fuerte.fit(X_train, y_train)

# 5. Evaluar
y_pred = rf_fuerte.predict(X_test)
print(f"Precisión (Accuracy): {accuracy_score(y_test, y_pred):.2f}")
print(classification_report(y_test, y_pred))

# 6. Guardar el modelo y el escalador para la Pi (o simulación)
joblib.dump(rf_fuerte, 'modelo_rf_fuerte.pkl')
joblib.dump(scaler, 'scaler_fuerte.pkl') # Guardamos el escalador por si acaso
print("Modelo fuerte guardado como 'modelo_rf_fuerte.pkl'")
