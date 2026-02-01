import pandas as pd
df = pd.read_csv("hand_features.csv")

# eliminar columnas de mano izquierda
df = df.loc[:, ~df.columns.str.startswith("left_")]

# eliminar filas sin mano derecha
right_cols = [c for c in df.columns if c.startswith("right_")]
df = df[(df[right_cols] != 0).any(axis=1)]

df.to_csv("hand_data_right_only.csv", index=False)

print("Dataset limpio: solo mano derecha")