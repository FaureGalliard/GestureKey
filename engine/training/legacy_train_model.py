import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# ========================
# Config
# ========================
CSV_PATH = "hand_features.csv"
MODEL_PATH = "hand_state_rf.pkl"
RANDOM_SEED = 42

# ========================
# Load dataset
# ========================
df = pd.read_csv(CSV_PATH)
print("Dataset cargado:", df.shape)
print("\nPrimeras filas:")
print(df.head())

# ========================
# Data exploration
# ========================
print("\nDistribución de estados:")
print(df["state"].value_counts())

print("\nValores nulos por columna:")
print(df.isnull().sum()[df.isnull().sum() > 0])

# ========================
# Features / Labels
# ========================
X = df.drop(columns=["frame", "time", "state"])
y = df["state"]

print(f"\nFeatures: {X.shape[1]}")
print(f"Total samples: {len(y)}")
print(f"Estados únicos: {y.unique()}")

# ========================
# Train / Test split
# ========================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=RANDOM_SEED,
    stratify=y
)

print(f"\nTrain: {X_train.shape}")
print(f"Test : {X_test.shape}")

# ========================
# Model
# ========================
model = RandomForestClassifier(
    n_estimators=150,
    max_depth=None,
    min_samples_leaf=3,
    random_state=RANDOM_SEED,
    n_jobs=-1,
    verbose=1  # Para ver progreso
)

# ========================
# Train
# ========================
print("\n" + "="*50)
print("Entrenando modelo...")
print("="*50)
model.fit(X_train, y_train)

# ========================
# Evaluate
# ========================
y_pred = model.predict(X_test)

print("\n" + "="*50)
print("RESULTADOS")
print("="*50)

print(f"\nAccuracy en Train: {model.score(X_train, y_train):.4f}")
print(f"Accuracy en Test:  {accuracy_score(y_test, y_pred):.4f}")

print("\n=== Classification Report ===")
print(classification_report(y_test, y_pred))

print("\n=== Confusion Matrix ===")
print(confusion_matrix(y_test, y_pred))

# ========================
# Feature Importance
# ========================
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\n=== Top 10 Características más Importantes ===")
print(feature_importance.head(10).to_string(index=False))

# ========================
# Save model
# ========================
joblib.dump(model, MODEL_PATH)
print(f"\n✓ Modelo guardado en: {MODEL_PATH}")

# Opcional: guardar también las métricas
metrics = {
    'train_accuracy': model.score(X_train, y_train),
    'test_accuracy': accuracy_score(y_test, y_pred),
    'feature_names': X.columns.tolist(),
    'classes': model.classes_.tolist()
}
joblib.dump(metrics, MODEL_PATH.replace('.pkl', '_metrics.pkl'))
print(f"✓ Métricas guardadas en: {MODEL_PATH.replace('.pkl', '_metrics.pkl')}")