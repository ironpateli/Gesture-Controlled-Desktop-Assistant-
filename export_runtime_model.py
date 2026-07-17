"""Export gesture_model.pth to the lightweight NumPy inference format."""

import csv
import os

import numpy as np
import torch
import torch.nn as nn

from runtime_model import NumpyGestureLSTM

CHECKPOINT_PATH = "gesture_model.pth"
RUNTIME_MODEL_PATH = "gesture_model_runtime.npz"
CSV_PATH = "gesture_data.csv"
SEQ_LEN = 20
INPUT_SIZE = 63


class GestureLSTM(nn.Module):
    def __init__(self, hidden_size: int, num_classes: int, num_layers: int):
        super().__init__()
        self.lstm = nn.LSTM(INPUT_SIZE, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, values):
        output, _ = self.lstm(values)
        return self.fc(output[:, -1, :])


def _load_torch_model(checkpoint):
    labels_by_id = checkpoint["id_to_label"]
    labels = [labels_by_id[index] for index in range(len(labels_by_id))]
    model = GestureLSTM(
        hidden_size=checkpoint.get("hidden_size", 64),
        num_classes=len(labels),
        num_layers=checkpoint.get("num_layers", 1),
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, labels


def _sample_sequences(limit: int = 25) -> np.ndarray:
    samples = []
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, newline="") as file:
            reader = csv.reader(file)
            next(reader, None)
            for row in reader:
                samples.append(np.asarray(row[1:], dtype=np.float32).reshape(SEQ_LEN, INPUT_SIZE))
                if len(samples) >= limit:
                    break
    if not samples:
        rng = np.random.default_rng(42)
        samples = list(rng.normal(size=(limit, SEQ_LEN, INPUT_SIZE)).astype(np.float32))
    return np.asarray(samples, dtype=np.float32)


def main():
    checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    torch_model, labels = _load_torch_model(checkpoint)
    state = checkpoint["model_state_dict"]

    np.savez_compressed(
        RUNTIME_MODEL_PATH,
        weight_ih=state["lstm.weight_ih_l0"].cpu().numpy(),
        weight_hh=state["lstm.weight_hh_l0"].cpu().numpy(),
        bias_ih=state["lstm.bias_ih_l0"].cpu().numpy(),
        bias_hh=state["lstm.bias_hh_l0"].cpu().numpy(),
        fc_weight=state["fc.weight"].cpu().numpy(),
        fc_bias=state["fc.bias"].cpu().numpy(),
        labels=np.asarray(labels),
    )

    runtime_model = NumpyGestureLSTM(RUNTIME_MODEL_PATH)
    samples = _sample_sequences()
    with torch.no_grad():
        torch_logits = torch_model(torch.from_numpy(samples)).cpu().numpy()
    numpy_logits = np.asarray([runtime_model.predict_logits(sample) for sample in samples])

    max_error = float(np.max(np.abs(torch_logits - numpy_logits)))
    predictions_match = np.array_equal(
        np.argmax(torch_logits, axis=1),
        np.argmax(numpy_logits, axis=1),
    )
    if max_error > 1e-4 or not predictions_match:
        raise RuntimeError(
            f"Runtime parity failed: max_error={max_error:.8f}, "
            f"predictions_match={predictions_match}"
        )

    print(f"Exported {RUNTIME_MODEL_PATH}")
    print(f"Verified {len(samples)} sequences; max logit error: {max_error:.8f}")


if __name__ == "__main__":
    main()
