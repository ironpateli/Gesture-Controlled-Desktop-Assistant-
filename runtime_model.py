"""Small NumPy inference runtime for the trained one-layer gesture LSTM."""

import numpy as np


def _sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-values))


class NumpyGestureLSTM:
    def __init__(self, model_path: str):
        with np.load(model_path, allow_pickle=False) as data:
            self.weight_ih = data["weight_ih"].astype(np.float32)
            self.weight_hh = data["weight_hh"].astype(np.float32)
            self.bias_ih = data["bias_ih"].astype(np.float32)
            self.bias_hh = data["bias_hh"].astype(np.float32)
            self.fc_weight = data["fc_weight"].astype(np.float32)
            self.fc_bias = data["fc_bias"].astype(np.float32)
            self.labels = [str(label) for label in data["labels"]]

        self.hidden_size = self.weight_hh.shape[1]

    def predict_logits(self, sequence) -> np.ndarray:
        """Return class logits for one sequence shaped (frames, features)."""
        inputs = np.asarray(sequence, dtype=np.float32)
        hidden = np.zeros(self.hidden_size, dtype=np.float32)
        cell = np.zeros(self.hidden_size, dtype=np.float32)

        for frame in inputs:
            gates = (
                self.weight_ih @ frame
                + self.bias_ih
                + self.weight_hh @ hidden
                + self.bias_hh
            )
            input_gate, forget_gate, candidate, output_gate = np.split(gates, 4)
            input_gate = _sigmoid(input_gate)
            forget_gate = _sigmoid(forget_gate)
            candidate = np.tanh(candidate)
            output_gate = _sigmoid(output_gate)
            cell = forget_gate * cell + input_gate * candidate
            hidden = output_gate * np.tanh(cell)

        return self.fc_weight @ hidden + self.fc_bias

    def predict(self, sequence) -> tuple[str, float]:
        logits = self.predict_logits(sequence)
        shifted = logits - np.max(logits)
        probabilities = np.exp(shifted)
        probabilities /= np.sum(probabilities)
        class_id = int(np.argmax(probabilities))
        return self.labels[class_id], float(probabilities[class_id])
