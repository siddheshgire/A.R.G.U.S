"""
A.R.G.U.S. — Deep Autoencoder Anomaly Detection Architecture (PyTorch)
Deep neural network trained on legitimate transactions to identify anomalies
via feature reconstruction loss (Mean Squared Error).
"""

from pathlib import Path
from typing import Optional, Union, Dict, Any, Tuple
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader


class AutoencoderDataset(Dataset):
    """PyTorch Dataset wrapping tabular feature matrices."""

    def __init__(self, X: pd.DataFrame | np.ndarray):
        if isinstance(X, pd.DataFrame):
            arr = np.array(X.to_numpy(dtype=np.float32), copy=True)
        else:
            arr = np.array(X, copy=True, dtype=np.float32)
        self.tensors = torch.from_numpy(arr)

    def __len__(self) -> int:
        return len(self.tensors)

    def __getitem__(self, idx: int) -> torch.Tensor:
        return self.tensors[idx]


class DeepAutoencoder(nn.Module):
    """
    Symmetric bottleneck Deep Autoencoder network:
    Input(18) -> Dense(64) -> Dense(32) -> Latent(16) -> Dense(32) -> Dense(64) -> Output(18)
    """

    def __init__(self, input_dim: int = 18, latent_dim: int = 16):
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim

        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(0.1),
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.LeakyReLU(0.1),
            nn.Linear(32, latent_dim),
        )

        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.BatchNorm1d(32),
            nn.LeakyReLU(0.1),
            nn.Linear(32, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(0.1),
            nn.Linear(64, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        latent = self.encoder(x)
        reconstruction = self.decoder(latent)
        return reconstruction


class AutoencoderAnomalyDetector:
    """
    High-level wrapper for training and inference of the PyTorch Deep Autoencoder.
    Operates on scaled numerical features.
    Computes sample-wise MSE reconstruction error as an anomaly signal.
    """

    def __init__(
        self,
        input_dim: int = 18,
        latent_dim: int = 16,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-5,
        device: Optional[str] = None,
    ):
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))

        self.model = DeepAutoencoder(input_dim=self.input_dim, latent_dim=self.latent_dim).to(self.device)
        self.criterion = nn.MSELoss()
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay,
        )

        # Error normalization statistics learned from normal validation data
        self.error_mean_ = None
        self.error_std_ = None
        self.error_p95_ = None
        self.is_fitted = False

    def train_epoch(self, dataloader: DataLoader) -> float:
        """Trains autoencoder for one epoch on normal transactions."""
        self.model.train()
        total_loss = 0.0
        n_batches = 0

        for batch in dataloader:
            x = batch.to(self.device)
            self.optimizer.zero_grad()
            reconstructed = self.model(x)
            loss = self.criterion(reconstructed, x)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        return total_loss / max(n_batches, 1)

    def evaluate_loss(self, dataloader: DataLoader) -> float:
        """Computes average reconstruction loss on validation data."""
        self.model.eval()
        total_loss = 0.0
        n_batches = 0

        with torch.no_grad():
            for batch in dataloader:
                x = batch.to(self.device)
                reconstructed = self.model(x)
                loss = self.criterion(reconstructed, x)
                total_loss += loss.item()
                n_batches += 1

        return total_loss / max(n_batches, 1)

    def predict_reconstruction_error(
        self,
        X: pd.DataFrame | np.ndarray,
        batch_size: int = 4096,
    ) -> np.ndarray:
        """
        Computes per-sample Mean Squared Error (MSE) reconstruction loss:
        MSE_i = (1 / D) * sum_{j=1}^D (x_{i,j} - x_hat_{i,j})^2
        """
        self.model.eval()
        dataset = AutoencoderDataset(X)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

        errors = []
        with torch.no_grad():
            for batch in loader:
                x = batch.to(self.device)
                reconstructed = self.model(x)
                # Sample-wise MSE reduction across feature dimension (dim=1)
                sample_mse = torch.mean((x - reconstructed) ** 2, dim=1)
                errors.append(sample_mse.cpu().numpy())

        return np.concatenate(errors, axis=0)

    def calibrate_anomaly_scores(self, normal_val_errors: np.ndarray) -> None:
        """Learns distribution statistics from legitimate validation reconstruction errors."""
        self.error_mean_ = float(np.mean(normal_val_errors))
        self.error_std_ = float(np.std(normal_val_errors)) + 1e-8
        self.error_p95_ = float(np.percentile(normal_val_errors, 95))
        self.is_fitted = True

    def predict_anomaly_score(
        self,
        X: pd.DataFrame | np.ndarray,
        batch_size: int = 4096,
    ) -> np.ndarray:
        """
        Transforms reconstruction error into a bounded [0, 1] anomaly score
        using sigmoid scaling centered around the 95th percentile of normal errors.
        """
        raw_errors = self.predict_reconstruction_error(X, batch_size=batch_size)
        if self.error_p95_ is not None and self.error_std_ is not None:
            # Sigmoid activation centered at 95th percentile
            z = (raw_errors - self.error_p95_) / self.error_std_
            scores = 1.0 / (1.0 + np.exp(-z))
        else:
            # Fallback min-max
            e_min, e_max = np.min(raw_errors), np.max(raw_errors)
            denom = (e_max - e_min) if e_max > e_min else 1.0
            scores = np.clip((raw_errors - e_min) / denom, 0.0, 1.0)
        return scores

    def save(self, path: Union[str, Path]) -> None:
        """Serializes PyTorch model weights and calibration metadata."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "model_state_dict": self.model.state_dict(),
            "input_dim": self.input_dim,
            "latent_dim": self.latent_dim,
            "error_mean": self.error_mean_,
            "error_std": self.error_std_,
            "error_p95": self.error_p95_,
        }
        torch.save(checkpoint, p)

    @classmethod
    def load(cls, path: Union[str, Path], device: Optional[str] = None) -> "AutoencoderAnomalyDetector":
        """Loads PyTorch checkpoint and reconstructs anomaly detector."""
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"Checkpoint not found at: {p}")
        checkpoint = torch.load(p, map_location=device if device else "cpu")
        detector = cls(
            input_dim=checkpoint["input_dim"],
            latent_dim=checkpoint["latent_dim"],
            device=device,
        )
        detector.model.load_state_dict(checkpoint["model_state_dict"])
        detector.error_mean_ = checkpoint.get("error_mean")
        detector.error_std_ = checkpoint.get("error_std")
        detector.error_p95_ = checkpoint.get("error_p95")
        detector.is_fitted = True
        return detector
