"""
train_classifier.py

Phase 2, step 2: train a real classifier on YOUR collected landmark data
(gesture_data.csv from collect_data.py), instead of the rule-based logic
in gesture_detector.py.

Trains BOTH a Random Forest and an MLP, using GridSearchCV to pick
hyperparameters empirically (based on validation accuracy) rather than
guessing numbers. Compares both on a held-out test set neither model
has seen during training or tuning, then saves the better one to disk.

Run:
    python train_classifier.py
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

CSV_PATH = "gesture_data.csv"
MODEL_OUT_PATH = "gesture_model.pkl"


def load_data():
    df = pd.read_csv(CSV_PATH)
    X = df.drop(columns=["label"]).values          # 63 numeric feature columns
    y = df["label"].values                          # gesture name strings
    return X, y


def train_random_forest(X_train, y_train):
    """Small grid: n_estimators (more trees = more stable, diminishing
    returns past a point), max_depth (limits overfitting), min_samples_leaf
    (smooths out noisy splits). GridSearchCV tries every combination with
    cross-validation and picks the best by validation accuracy."""
    param_grid = {
        "n_estimators": [100, 200],
        "max_depth": [10, 20, None],
        "min_samples_leaf": [1, 3],
    }
    rf = RandomForestClassifier(random_state=42)
    grid = GridSearchCV(rf, param_grid, cv=5, n_jobs=-1, scoring="accuracy")
    grid.fit(X_train, y_train)
    print(f"[Random Forest] best params: {grid.best_params_}")
    print(f"[Random Forest] best CV accuracy: {grid.best_score_:.4f}")
    return grid.best_estimator_


def train_mlp(X_train, y_train):
    """Small grid: hidden_layer_sizes (network capacity — kept small since
    this is tabular data with ~63 inputs, not images), learning_rate_init
    (step size per update), alpha (L2 regularization strength, helps
    prevent overfitting on a modestly-sized dataset)."""
    param_grid = {
        "hidden_layer_sizes": [(32,), (64,), (64, 32)],
        "learning_rate_init": [0.001, 0.01],
        "alpha": [0.0001, 0.001],
    }
    mlp = MLPClassifier(max_iter=2000, random_state=42)
    grid = GridSearchCV(mlp, param_grid, cv=5, n_jobs=-1, scoring="accuracy")
    grid.fit(X_train, y_train)
    print(f"[MLP] best params: {grid.best_params_}")
    print(f"[MLP] best CV accuracy: {grid.best_score_:.4f}")
    return grid.best_estimator_


def evaluate(model, X_test, y_test, name):
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"\n=== {name} — TEST SET RESULTS (never seen during training/tuning) ===")
    print(f"Test accuracy: {acc:.4f}")
    print("\nConfusion matrix (rows=true label, columns=predicted label):")
    labels = sorted(set(y_test))
    cm = confusion_matrix(y_test, preds, labels=labels)
    print("Labels:", labels)
    print(cm)
    print("\nPer-class precision/recall/f1:")
    print(classification_report(y_test, preds, labels=labels))
    return acc


def main():
    X, y = load_data()
    print(f"Loaded {len(X)} samples across {len(set(y))} classes: {sorted(set(y))}")

    # 70% train (also used internally for cross-validation during grid search),
    # 30% held out purely for final, honest evaluation. stratify=y keeps class
    # proportions balanced across the split.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    rf_model = train_random_forest(X_train, y_train)
    mlp_model = train_mlp(X_train, y_train)

    rf_acc = evaluate(rf_model, X_test, y_test, "Random Forest")
    mlp_acc = evaluate(mlp_model, X_test, y_test, "MLP")

    best_model, best_name, best_acc = (
        (rf_model, "Random Forest", rf_acc) if rf_acc >= mlp_acc
        else (mlp_model, "MLP", mlp_acc)
    )

    print(f"\n>>> Best model: {best_name} (test accuracy {best_acc:.4f}) — saving to {MODEL_OUT_PATH}")
    joblib.dump(best_model, MODEL_OUT_PATH)


if __name__ == "__main__":
    main()
