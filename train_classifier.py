"""
train_classifier.py

Phase 2, step 2: train a PyTorch LSTM classifier on your sequence landmark data
(gesture_data.csv from collect_data.py).

Trains a recurrent model to recognize both static and dynamic gestures.
Saves the trained model and class labels to gesture_model.pth.
"""

import os
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

CSV_PATH = "gesture_data.csv"
MODEL_OUT_PATH = "gesture_model.pth"
SEQ_LEN = 20
INPUT_SIZE = 63  # 21 landmarks * 3 coordinates


class GestureDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.long)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


class GestureLSTM(nn.Module):
    def __init__(self, input_size=63, hidden_size=64, num_classes=9, num_layers=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        # x shape: (batch_size, seq_len, input_size)
        out, _ = self.lstm(x)
        # Pass the output of the last time step through the linear layer
        out = self.fc(out[:, -1, :])
        return out


def load_data():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Dataset not found at {CSV_PATH}. Please run collect_data.py first.")

    df = pd.read_csv(CSV_PATH)
    if len(df) == 0:
        raise ValueError(f"Dataset at {CSV_PATH} is empty.")

    X_raw = df.drop(columns=["label"]).values  # Shape: (num_samples, 1260)
    y_raw = df["label"].values

    # Reshape X to (num_samples, seq_len, input_size)
    num_samples = X_raw.shape[0]
    X = X_raw.reshape(num_samples, SEQ_LEN, INPUT_SIZE)

    # Encode labels
    unique_labels = sorted(list(set(y_raw)))
    label_to_id = {label: idx for idx, label in enumerate(unique_labels)}
    id_to_label = {idx: label for idx, label in enumerate(unique_labels)}
    y = np.array([label_to_id[label] for label in y_raw])

    return X, y, label_to_id, id_to_label


def main():
    try:
        X, y, label_to_id, id_to_label = load_data()
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    num_classes = len(label_to_id)
    print(f"Loaded {len(X)} sequences across {num_classes} classes: {list(label_to_id.keys())}")

    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    train_dataset = GestureDataset(X_train, y_train)
    test_dataset = GestureDataset(X_test, y_test)

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

    # Initialize model
    model = GestureLSTM(input_size=INPUT_SIZE, hidden_size=64, num_classes=num_classes)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    # Train loop
    epochs = 40
    print("\n--- Training PyTorch LSTM Model ---")
    model.train()
    for epoch in range(epochs):
        epoch_loss = 0.0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * batch_x.size(0)

        epoch_loss /= len(train_loader.dataset)
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch {epoch+1}/{epochs} | Training Loss: {epoch_loss:.4f}")

    # Evaluate
    model.eval()
    all_preds = []
    all_targets = []
    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            outputs = model(batch_x)
            preds = torch.argmax(outputs, dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(batch_y.cpu().numpy())

    acc = accuracy_score(all_targets, all_preds)
    print(f"\nTest set accuracy: {acc:.4f}")
    
    labels = [id_to_label[i] for i in range(num_classes)]
    print("\nConfusion Matrix (rows=true, cols=pred):")
    print(confusion_matrix(all_targets, all_preds))
    print("\nClassification Report:")
    print(classification_report(all_targets, all_preds, target_names=labels))

    # Save model and mapping metadata
    print(f"Saving trained LSTM model to {MODEL_OUT_PATH}")
    torch.save({
        'model_state_dict': model.state_dict(),
        'label_to_id': label_to_id,
        'id_to_label': id_to_label,
        'hidden_size': 64,
        'num_layers': 1
    }, MODEL_OUT_PATH)
    print("Done!")


if __name__ == "__main__":
    main()
