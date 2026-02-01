import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

# ========================
# Cargar dataset
# ========================
df = pd.read_csv("hand_data_right_only.csv")

X = df.drop(columns=["frame", "time", "state"])
y = df["state"]

# ========================
# Split
# ========================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ========================
# Modelo
# ========================
model = RandomForestClassifier(
    n_estimators=500,
    max_depth=None,
    min_samples_leaf=3,
    class_weight="balanced",
    random_state=42
)

model.fit(X_train, y_train)

# ========================
# Evaluación
# ========================
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

# ========================
# Guardar modelo
# ========================
joblib.dump(model, "palm_fist_model.pkl")
print("Modelo guardado")
