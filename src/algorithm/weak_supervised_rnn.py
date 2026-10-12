#!/usr/bin/env python3
"""Train an unordered-diploid weakly supervised raw-signal RNN.

Unlike the earlier weak-label prototypes, this experiment never trains on
tool-derived ``long_like``/``short_like`` read assignments. Each training bag
contains reads from one sample, and supervision consists only of that sample's
unordered pair of allele counts. A train-only duration calibration supplies a
monotonic physical baseline; the network learns a raw-signal residual and an
aleatoric variance per read. A latent two-component likelihood assigns reads
to alleles without external per-read labels.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch.nn.utils.rnn import pack_padded_sequence

try:
    from dataset import DEFAULT_HOLDOUT_SAMPLE, DEFAULT_INDEX, DEFAULT_SIGNAL_ARCHIVE, SignalDataset, load_signal_dataset
    from torch_rnn import choose_device
    from uncertainty_alleles import call_alleles_with_uncertainty
except ImportError:  # pragma: no cover - allows module execution with -m
    from .dataset import DEFAULT_HOLDOUT_SAMPLE, DEFAULT_INDEX, DEFAULT_SIGNAL_ARCHIVE, SignalDataset, load_signal_dataset
    from .torch_rnn import choose_device
    from .uncertainty_alleles import call_alleles_with_uncertainty


DEFAULT_PREDICTIONS = Path("ont-str-runner/work/analysis/weak_supervised_rnn_predictions.tsv")
DEFAULT_CALLS = Path("ont-str-runner/work/analysis/weak_supervised_rnn_allele_calls.tsv")
DEFAULT_SUMMARY = Path("ont-str-runner/work/analysis/weak_supervised_rnn_summary.tsv")
DEFAULT_CHECKPOINT = Path("ont-str-runner/work/analysis/weak_supervised_rnn.pt")

PREDICTION_FIELDS = [
    "sample",
    "read_id",
    "truth_long",
    "truth_short",
    "prediction",
    "raw_prediction_std",
    "prediction_std",
    "uncertainty_score",
    "split",
]
CALL_FIELDS = [
    "sample",
    "split_scope",
    "truth_long",
    "truth_short",
    "pred_long",
    "pred_short",
    "long_error",
    "short_error",
    "candidate_long",
    "candidate_short",
    "consensus",
    "resolved",
    "support_long",
    "support_short",
    "weight_long",
    "weight_short",
    "bic_one",
    "bic_two",
    "bic_gain",
    "separation",
    "mixture_confidence",
    "reason",
    "rows_used",
]
SUMMARY_FIELDS = ["metric", "value"]


class WeakRepeatCountRNN(nn.Module):
    """Conv-BiRNN encoder with an explicit raw-duration feature."""

    def __init__(
        self,
        hidden_dim: int,
        rnn_type: str,
        conv_channels: int,
        dropout: float,
        conv_stride1: int,
        conv_stride2: int,
        length_mean: float,
        length_std: float,
        duration_intercept: float,
        duration_slope: float,
    ) -> None:
        super().__init__()
        self.conv_stride1 = conv_stride1
        self.conv_stride2 = conv_stride2
        self.register_buffer("length_mean", torch.tensor(float(length_mean)))
        self.register_buffer("length_std", torch.tensor(max(float(length_std), 1.0)))
        self.register_buffer("duration_intercept", torch.tensor(float(duration_intercept)))
        self.register_buffer("duration_slope", torch.tensor(float(duration_slope)))
        self.conv1 = nn.Conv1d(1, conv_channels, kernel_size=9, stride=conv_stride1, padding=4)
        self.conv2 = nn.Conv1d(conv_channels, conv_channels, kernel_size=7, stride=conv_stride2, padding=3)
        self.activation = nn.ReLU()
        rnn_cls = nn.GRU if rnn_type == "gru" else nn.LSTM
        self.rnn = rnn_cls(
            input_size=conv_channels,
            hidden_size=hidden_dim,
            batch_first=True,
            bidirectional=True,
        )
        self.head = nn.Sequential(
            nn.LayerNorm(hidden_dim * 2 + 1),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2 + 1, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 2),
        )

    @staticmethod
    def conv_length(length: torch.Tensor, kernel_size: int, stride: int, padding: int) -> torch.Tensor:
        value = torch.div(
            length + 2 * padding - (kernel_size - 1) - 1,
            stride,
            rounding_mode="floor",
        ) + 1
        return torch.clamp(value, min=1)

    def encoded_lengths(self, length: torch.Tensor) -> torch.Tensor:
        length = self.conv_length(length, kernel_size=9, stride=self.conv_stride1, padding=4)
        return self.conv_length(length, kernel_size=7, stride=self.conv_stride2, padding=3)

    def forward(self, signal: torch.Tensor, length: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.activation(self.conv1(signal.unsqueeze(1)))
        x = self.activation(self.conv2(x)).transpose(1, 2)
        encoded_length = self.encoded_lengths(length.cpu())
        packed = pack_padded_sequence(x, encoded_length, batch_first=True, enforce_sorted=False)
        _, state = self.rnn(packed)
        if isinstance(state, tuple):
            state = state[0]
        recurrent = torch.cat([state[-2], state[-1]], dim=1)
        normalized_length = ((length.float() - self.length_mean) / self.length_std).unsqueeze(1)
        output = self.head(torch.cat([recurrent, normalized_length], dim=1))
        duration_baseline = self.duration_intercept + self.duration_slope * length.float()
        count = duration_baseline + output[:, 0]
        log_variance = torch.clamp(output[:, 1], min=-4.0, max=4.0)
        return count, log_variance


def to_float(value: str | None) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if np.isfinite(parsed) else None


def truth_pairs_from_metadata(metadata: list[dict[str, str]]) -> dict[str, tuple[float, float]]:
    """Return sorted diploid truths without consulting per-read group labels."""
    pairs: dict[str, tuple[float, float]] = {}
    for row in metadata:
        sample = row.get("sample", "")
        long_value = to_float(row.get("truth_long"))
        short_value = to_float(row.get("truth_short"))
        if not sample or long_value is None or short_value is None:
            continue
        pair = (min(short_value, long_value), max(short_value, long_value))
        if sample in pairs and pairs[sample] != pair:
            raise ValueError(f"inconsistent truth pair for sample {sample}")
        pairs[sample] = pair
    return pairs


def choose_sample_split(
    truth_pairs: dict[str, tuple[float, float]],
    holdout_sample: str,
    validation_sample: str,
) -> tuple[list[str], str | None, str]:
    if holdout_sample not in truth_pairs:
        raise ValueError(f"holdout sample {holdout_sample!r} has no diploid truth")
    candidates = sorted(sample for sample in truth_pairs if sample != holdout_sample)
    if len(candidates) < 2:
        raise ValueError("at least three labelled samples are required")
    if validation_sample == "auto":
        selected_validation: str | None = candidates[-1]
    elif validation_sample == "none":
        selected_validation = None
    else:
        if validation_sample == holdout_sample or validation_sample not in candidates:
            raise ValueError("validation sample must be labelled and distinct from holdout")
        selected_validation = validation_sample
    train_samples = [sample for sample in candidates if sample != selected_validation]
    return train_samples, selected_validation, holdout_sample


def gaussian_log_probability(
    prediction: torch.Tensor,
    log_variance: torch.Tensor,
    target: torch.Tensor,
    label_noise: float,
) -> torch.Tensor:
    variance = torch.exp(log_variance) + label_noise**2
    return -0.5 * (
        math.log(2.0 * math.pi) + torch.log(variance) + (prediction - target) ** 2 / variance
    )


def unordered_diploid_loss(
    prediction: torch.Tensor,
    log_variance: torch.Tensor,
    allele_a: float,
    allele_b: float,
    *,
    label_noise: float = 1.0,
    min_component_fraction: float = 0.10,
    coverage_weight: float = 10.0,
    entropy_weight: float = 0.05,
    assignment_mode: str = "constrained-hard",
    assignment_score: torch.Tensor | None = None,
    balance_components: bool = True,
    beta_nll: float = 0.5,
    mean_loss_weight: float = 0.5,
    mean_huber_delta: float = 5.0,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Permutation-invariant latent loss for a bag of reads from one sample.

    ``constrained-hard`` performs a generalized-EM assignment step using only
    current model likelihoods. It guarantees a minimum number of reads for
    each distinct allele, which prevents the stationary midpoint collapse of
    an unconstrained soft mixture. No external per-read labels are consulted.
    """
    short_allele = min(float(allele_a), float(allele_b))
    long_allele = max(float(allele_a), float(allele_b))
    target_a = torch.full_like(prediction, short_allele)
    target_b = torch.full_like(prediction, long_allele)
    log_components = torch.stack(
        [
            gaussian_log_probability(prediction, log_variance, target_a, label_noise),
            gaussian_log_probability(prediction, log_variance, target_b, label_noise),
        ],
        dim=1,
    ) - math.log(2.0)
    posterior = torch.softmax(log_components, dim=1)
    if not 0.0 <= beta_nll <= 1.0:
        raise ValueError("beta_nll must be in [0, 1]")
    beta_weight = (torch.exp(log_variance) + label_noise**2).detach().pow(beta_nll)
    beta_weight = beta_weight / torch.clamp(torch.mean(beta_weight), min=1e-8)
    mean_components = torch.stack(
        [
            F.smooth_l1_loss(prediction, target_a, reduction="none", beta=mean_huber_delta),
            F.smooth_l1_loss(prediction, target_b, reduction="none", beta=mean_huber_delta),
        ],
        dim=1,
    )

    if abs(short_allele - long_allele) < 1e-6:
        nll = -torch.mean(beta_weight * (log_components[:, 0] + math.log(2.0)))
        mean_loss = torch.mean(mean_components[:, 0])
        coverage = torch.zeros((), dtype=prediction.dtype, device=prediction.device)
        assignment_entropy = torch.zeros((), dtype=prediction.dtype, device=prediction.device)
    elif assignment_mode == "constrained-hard":
        component_costs = -log_components * beta_weight[:, None]
        minimum = max(1, int(math.ceil(min_component_fraction * prediction.shape[0])))
        maximum = prediction.shape[0] - minimum
        if maximum < minimum:
            raise ValueError("bag is too small for requested component fraction")
        delta = (component_costs[:, 1] - component_costs[:, 0]).detach()
        if assignment_score is None:
            order = torch.argsort(delta)
        else:
            if assignment_score.shape != prediction.shape:
                raise ValueError("assignment_score must match prediction shape")
            # Longer raw windows are the weak monotonic prior for the long allele.
            order = torch.argsort(assignment_score.detach(), descending=True)
        ordered_delta = delta[order]
        cumulative = torch.cumsum(ordered_delta, dim=0)
        candidate_counts = torch.arange(
            minimum,
            maximum + 1,
            dtype=torch.long,
            device=prediction.device,
        )
        candidate_costs = cumulative[candidate_counts - 1]
        count_b = int(candidate_counts[torch.argmin(candidate_costs)].item())
        assigned_b = torch.zeros(prediction.shape[0], dtype=torch.bool, device=prediction.device)
        assigned_b[order[:count_b]] = True
        short_cost = component_costs[~assigned_b, 0]
        long_cost = component_costs[assigned_b, 1]
        if balance_components:
            nll = 0.5 * (torch.mean(short_cost) + torch.mean(long_cost))
            mean_loss = 0.5 * (
                torch.mean(mean_components[~assigned_b, 0])
                + torch.mean(mean_components[assigned_b, 1])
            )
        else:
            selected_cost = torch.where(
                assigned_b,
                component_costs[:, 1],
                component_costs[:, 0],
            )
            nll = torch.mean(selected_cost)
            mean_loss = torch.mean(
                torch.where(assigned_b, mean_components[:, 1], mean_components[:, 0])
            )
        posterior = torch.stack([(~assigned_b).float(), assigned_b.float()], dim=1)
        coverage = torch.zeros((), dtype=prediction.dtype, device=prediction.device)
        assignment_entropy = torch.zeros((), dtype=prediction.dtype, device=prediction.device)
    elif assignment_mode == "soft":
        log_mixture = torch.logsumexp(log_components, dim=1)
        nll = -torch.mean(beta_weight * log_mixture)
        mean_loss = torch.mean(torch.sum(posterior.detach() * mean_components, dim=1))
        fractions = torch.mean(posterior, dim=0)
        coverage = torch.sum(torch.relu(min_component_fraction - fractions) ** 2)
        assignment_entropy = torch.mean(
            -torch.sum(posterior * torch.log(torch.clamp(posterior, min=1e-8)), dim=1)
        )
    else:
        raise ValueError(f"unknown assignment mode: {assignment_mode}")
    total = (
        nll
        + mean_loss_weight * mean_loss
        + coverage_weight * coverage
        + entropy_weight * assignment_entropy
    )
    return total, {
        "nll": nll,
        "mean_loss": mean_loss,
        "coverage": coverage,
        "assignment_entropy": assignment_entropy,
        "posterior": posterior,
    }


def indices_by_sample(metadata: list[dict[str, str]]) -> dict[str, np.ndarray]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(metadata):
        grouped[row.get("sample", "")].append(idx)
    return {sample: np.asarray(indices, dtype=np.int64) for sample, indices in grouped.items()}


def cap_indices(indices: np.ndarray, maximum: int) -> np.ndarray:
    if maximum <= 0 or indices.size <= maximum:
        return indices
    positions = np.linspace(0, indices.size - 1, maximum, dtype=np.int64)
    return indices[positions]


def two_cluster_medians(values: np.ndarray) -> tuple[float, float]:
    """Find deterministic low/high duration centres without read labels."""
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size < 2:
        raise ValueError("at least two finite durations are required")
    low, high = np.quantile(finite, [0.25, 0.75]).tolist()
    if abs(high - low) < 1e-8:
        centre = float(np.median(finite))
        return centre, centre
    for _ in range(100):
        is_high = np.abs(finite - high) < np.abs(finite - low)
        if not np.any(is_high) or np.all(is_high):
            ordered = np.sort(finite)
            split = max(1, ordered.size // 2)
            new_low = float(np.median(ordered[:split]))
            new_high = float(np.median(ordered[split:]))
        else:
            new_low = float(np.median(finite[~is_high]))
            new_high = float(np.median(finite[is_high]))
        if max(abs(new_low - low), abs(new_high - high)) < 1e-8:
            low, high = new_low, new_high
            break
        low, high = new_low, new_high
    return (low, high) if low <= high else (high, low)


def fit_duration_prior(
    lengths_by_sample: dict[str, np.ndarray],
    truth_pairs: dict[str, tuple[float, float]],
    train_samples: list[str],
) -> tuple[float, float, dict[str, tuple[float, float]], float]:
    """Fit count = intercept + slope * duration using training samples only.

    Each sample contributes two unsupervised duration centres paired in sorted
    order with its unordered genotype. Validation/test samples are not read.
    """
    duration_points: list[float] = []
    count_points: list[float] = []
    centres: dict[str, tuple[float, float]] = {}
    for sample in train_samples:
        if sample not in lengths_by_sample or sample not in truth_pairs:
            raise ValueError(f"missing duration/truth data for training sample {sample}")
        low_duration, high_duration = two_cluster_medians(lengths_by_sample[sample])
        short_count, long_count = sorted(truth_pairs[sample])
        centres[sample] = (low_duration, high_duration)
        duration_points.extend([low_duration, high_duration])
        count_points.extend([short_count, long_count])
    if len(duration_points) < 4:
        raise ValueError("at least two training samples are required for duration calibration")
    design = np.column_stack(
        [np.ones(len(duration_points), dtype=np.float64), np.asarray(duration_points)]
    )
    targets = np.asarray(count_points, dtype=np.float64)
    intercept, slope = np.linalg.lstsq(design, targets, rcond=None)[0]
    if not np.isfinite(intercept) or not np.isfinite(slope) or slope <= 0.0:
        raise ValueError("training data did not produce a positive finite duration slope")
    residuals = targets - (intercept + slope * np.asarray(duration_points))
    rmse = float(np.sqrt(np.mean(residuals**2)))
    return float(intercept), float(slope), centres, rmse


def make_split_labels(
    metadata: list[dict[str, str]],
    train_samples: list[str],
    validation_sample: str | None,
    holdout_sample: str,
) -> np.ndarray:
    train_set = set(train_samples)
    labels = []
    for row in metadata:
        sample = row.get("sample", "")
        if sample in train_set:
            labels.append("train")
        elif sample == validation_sample:
            labels.append("validation")
        elif sample == holdout_sample:
            labels.append("test")
        else:
            labels.append("unlabeled")
    return np.asarray(labels)


def tensor_batch(dataset: SignalDataset, indices: np.ndarray, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    signal = torch.from_numpy(dataset.signal[indices]).to(device)
    lengths = torch.from_numpy(dataset.mask[indices].sum(axis=1).astype(np.int64)).to(device)
    return signal, torch.clamp(lengths, min=1)


def initialize_residual_head(model: WeakRepeatCountRNN) -> None:
    """Start exactly at the duration prior with a broad raw variance."""
    final_layer = model.head[-1]
    if not isinstance(final_layer, torch.nn.Linear):
        raise TypeError("unexpected WeakRepeatCountRNN head")
    with torch.no_grad():
        final_layer.weight.zero_()
        final_layer.bias[0] = 0.0
        final_layer.bias[1] = 2.0


def train_epoch(
    model: WeakRepeatCountRNN,
    optimizer: torch.optim.Optimizer,
    dataset: SignalDataset,
    grouped_indices: dict[str, np.ndarray],
    truth_pairs: dict[str, tuple[float, float]],
    train_samples: list[str],
    device: torch.device,
    rng: np.random.Generator,
    bag_size: int,
    bags_per_sample: int,
    label_noise: float,
    min_component_fraction: float,
    coverage_weight: float,
    entropy_weight: float,
    assignment_mode: str,
    balance_components: bool,
    beta_nll: float,
    mean_loss_weight: float,
    mean_huber_delta: float,
) -> tuple[float, float, float]:
    model.train()
    losses: list[float] = []
    nlls: list[float] = []
    coverages: list[float] = []
    order = list(train_samples)
    rng.shuffle(order)
    for sample in order:
        available = grouped_indices[sample]
        for _ in range(bags_per_sample):
            chosen = rng.choice(available, size=min(bag_size, available.size), replace=False)
            signal, length = tensor_batch(dataset, chosen, device)
            optimizer.zero_grad(set_to_none=True)
            prediction, log_variance = model(signal, length)
            short_truth, long_truth = truth_pairs[sample]
            loss, parts = unordered_diploid_loss(
                prediction,
                log_variance,
                short_truth,
                long_truth,
                label_noise=label_noise,
                min_component_fraction=min_component_fraction,
                coverage_weight=coverage_weight,
                entropy_weight=entropy_weight,
                assignment_mode=assignment_mode,
                assignment_score=length.float(),
                balance_components=balance_components,
                beta_nll=beta_nll,
                mean_loss_weight=mean_loss_weight,
                mean_huber_delta=mean_huber_delta,
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
            nlls.append(float(parts["nll"].detach().cpu()))
            coverages.append(float(parts["coverage"].detach().cpu()))
    return float(np.mean(losses)), float(np.mean(nlls)), float(np.mean(coverages))


@torch.no_grad()
def predict_indices(
    model: WeakRepeatCountRNN,
    dataset: SignalDataset,
    indices: np.ndarray,
    device: torch.device,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    predictions = np.full(dataset.signal.shape[0], np.nan, dtype=np.float32)
    variances = np.full(dataset.signal.shape[0], np.nan, dtype=np.float32)
    for start in range(0, indices.size, batch_size):
        batch_indices = indices[start : start + batch_size]
        signal, length = tensor_batch(dataset, batch_indices, device)
        count, log_variance = model(signal, length)
        predictions[batch_indices] = count.cpu().numpy().astype(np.float32)
        variances[batch_indices] = torch.exp(log_variance).cpu().numpy().astype(np.float32)
    return predictions, variances


def calibrate_variance_scale(
    predictions: np.ndarray,
    variances: np.ndarray,
    indices: np.ndarray,
    truth_pair: tuple[float, float],
    *,
    minimum_scale: float = 0.25,
    maximum_scale: float = 4.0,
) -> float:
    """Fit one global uncertainty scale on the disjoint validation sample."""
    short_truth, long_truth = truth_pair
    residual = np.minimum(
        np.abs(predictions[indices] - short_truth),
        np.abs(predictions[indices] - long_truth),
    )
    denominator = np.maximum(variances[indices], 1e-8)
    scale = float(np.sqrt(np.mean(residual**2 / denominator)))
    if not np.isfinite(scale):
        return 1.0
    return float(np.clip(scale, minimum_scale, maximum_scale))


@torch.no_grad()
def validation_loss(
    model: WeakRepeatCountRNN,
    dataset: SignalDataset,
    indices: np.ndarray,
    truth_pair: tuple[float, float],
    device: torch.device,
    label_noise: float,
    min_component_fraction: float,
    coverage_weight: float,
    entropy_weight: float,
    assignment_mode: str,
    balance_components: bool,
    beta_nll: float,
    mean_loss_weight: float,
    mean_huber_delta: float,
) -> float:
    model.eval()
    signal, length = tensor_batch(dataset, indices, device)
    prediction, log_variance = model(signal, length)
    loss, _ = unordered_diploid_loss(
        prediction,
        log_variance,
        truth_pair[0],
        truth_pair[1],
        label_noise=label_noise,
        min_component_fraction=min_component_fraction,
        coverage_weight=coverage_weight,
        entropy_weight=entropy_weight,
        assignment_mode=assignment_mode,
        assignment_score=length.float(),
        balance_components=balance_components,
        beta_nll=beta_nll,
        mean_loss_weight=mean_loss_weight,
        mean_huber_delta=mean_huber_delta,
    )
    return float(loss.cpu())


@torch.no_grad()
def validation_allele_mae(
    model: WeakRepeatCountRNN,
    dataset: SignalDataset,
    indices: np.ndarray,
    truth_pair: tuple[float, float],
    device: torch.device,
) -> float:
    """Robust sample-level validation metric aligned with genotype accuracy."""
    model.eval()
    signal, length = tensor_batch(dataset, indices, device)
    predictions, _ = model(signal, length)
    candidate_short, candidate_long = two_cluster_medians(predictions.cpu().numpy())
    truth_short, truth_long = sorted(truth_pair)
    return float(
        np.mean(
            [abs(candidate_short - truth_short), abs(candidate_long - truth_long)]
        )
    )


def write_predictions(
    path: Path,
    dataset: SignalDataset,
    predictions: np.ndarray,
    raw_variances: np.ndarray,
    calibrated_variances: np.ndarray,
    split_labels: np.ndarray,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PREDICTION_FIELDS, delimiter="\t")
        writer.writeheader()
        for idx, row in enumerate(dataset.metadata):
            if not np.isfinite(predictions[idx]):
                continue
            raw_variance = max(float(raw_variances[idx]), 1e-8)
            variance = max(float(calibrated_variances[idx]), 1e-8)
            standard_deviation = math.sqrt(variance)
            writer.writerow(
                {
                    "sample": row.get("sample", ""),
                    "read_id": row.get("read_id", ""),
                    "truth_long": row.get("truth_long", ""),
                    "truth_short": row.get("truth_short", ""),
                    "prediction": f"{predictions[idx]:.6f}",
                    "raw_prediction_std": f"{math.sqrt(raw_variance):.6f}",
                    "prediction_std": f"{standard_deviation:.6f}",
                    "uncertainty_score": f"{1.0 / (1.0 + standard_deviation):.6f}",
                    "split": split_labels[idx],
                }
            )


def call_samples(
    dataset: SignalDataset,
    predictions: np.ndarray,
    variances: np.ndarray,
    split_labels: np.ndarray,
    truth_pairs: dict[str, tuple[float, float]],
    min_rows: int,
    min_separation: float,
    min_component_fraction: float,
    bic_margin: float,
) -> list[dict[str, object]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(dataset.metadata):
        if np.isfinite(predictions[idx]):
            grouped[row.get("sample", "")].append(idx)

    calls: list[dict[str, object]] = []
    for sample in sorted(grouped):
        idx = np.asarray(grouped[sample], dtype=np.int64)
        if idx.size < min_rows:
            continue
        call = call_alleles_with_uncertainty(
            predictions[idx],
            variances[idx],
            min_separation=min_separation,
            min_component_fraction=min_component_fraction,
            bic_margin=bic_margin,
        )
        truth = truth_pairs.get(sample)
        truth_short = truth[0] if truth else None
        truth_long = truth[1] if truth else None
        calls.append(
            {
                "sample": sample,
                "split_scope": split_labels[idx[0]],
                "truth_long": "" if truth_long is None else int(round(truth_long)),
                "truth_short": "" if truth_short is None else int(round(truth_short)),
                "pred_long": int(round(call.pred_long)),
                "pred_short": int(round(call.pred_short)),
                "long_error": "" if truth_long is None else int(round(call.pred_long - truth_long)),
                "short_error": "" if truth_short is None else int(round(call.pred_short - truth_short)),
                "candidate_long": f"{call.candidate_long:.6f}",
                "candidate_short": f"{call.candidate_short:.6f}",
                "consensus": f"{call.consensus:.6f}",
                "resolved": str(call.resolved),
                "support_long": call.support_long,
                "support_short": call.support_short,
                "weight_long": f"{call.weight_long:.6f}",
                "weight_short": f"{call.weight_short:.6f}",
                "bic_one": f"{call.bic_one:.6f}",
                "bic_two": f"{call.bic_two:.6f}",
                "bic_gain": f"{call.bic_gain:.6f}",
                "separation": f"{call.separation:.6f}",
                "mixture_confidence": call.confidence,
                "reason": f"{call.reason};within_sample_mixture_only",
                "rows_used": idx.size,
            }
        )
    return calls


def write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train sample-level weakly supervised raw-signal RNN.")
    parser.add_argument("--signal-archive", type=Path, default=DEFAULT_SIGNAL_ARCHIVE)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--holdout-sample", default=DEFAULT_HOLDOUT_SAMPLE)
    parser.add_argument("--validation-sample", default="auto", help="Labelled sample, 'auto', or 'none'.")
    parser.add_argument(
        "--validation-selection",
        choices=("allele-mae", "loss"),
        default="allele-mae",
        help="Select epochs using genotype-level validation by default.",
    )
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--bag-size", type=int, default=64)
    parser.add_argument("--bags-per-sample", type=int, default=4)
    parser.add_argument("--prediction-batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--conv-channels", type=int, default=8)
    parser.add_argument("--conv-stride1", type=int, default=32)
    parser.add_argument("--conv-stride2", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--rnn-type", choices=("gru", "lstm"), default="gru")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--label-noise", type=float, default=1.0)
    parser.add_argument(
        "--beta-nll",
        type=float,
        default=0.5,
        help="Detached variance weighting in [0,1]; 0 is ordinary heteroscedastic NLL.",
    )
    parser.add_argument("--mean-loss-weight", type=float, default=0.5)
    parser.add_argument("--mean-huber-delta", type=float, default=5.0)
    parser.add_argument("--min-component-fraction", type=float, default=0.10)
    parser.add_argument("--coverage-weight", type=float, default=10.0)
    parser.add_argument("--entropy-weight", type=float, default=0.05)
    parser.add_argument(
        "--assignment-mode",
        choices=("constrained-hard", "soft"),
        default="constrained-hard",
    )
    parser.add_argument(
        "--no-component-balance",
        action="store_true",
        help="Weight latent reads rather than giving each allele equal loss weight.",
    )
    parser.add_argument("--min-separation", type=float, default=3.0)
    parser.add_argument("--caller-min-component-fraction", type=float, default=0.20)
    parser.add_argument("--bic-margin", type=float, default=6.0)
    parser.add_argument("--min-rows", type=int, default=20)
    parser.add_argument("--max-rows-per-sample", type=int, default=0, help="Deterministic smoke-test cap.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.epochs < 1 or args.bag_size < 2 or args.bags_per_sample < 1:
        raise SystemExit("epochs/bag parameters must be positive and bag-size must be at least 2")
    if not 0.0 <= args.min_component_fraction < 0.5:
        raise SystemExit("--min-component-fraction must be in [0, 0.5)")
    if not 0.0 <= args.caller_min_component_fraction < 0.5:
        raise SystemExit("--caller-min-component-fraction must be in [0, 0.5)")
    if not 0.0 <= args.beta_nll <= 1.0:
        raise SystemExit("--beta-nll must be in [0, 1]")
    if args.mean_loss_weight < 0.0 or args.mean_huber_delta <= 0.0:
        raise SystemExit("mean-loss-weight must be non-negative and mean-huber-delta positive")

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    rng = np.random.default_rng(args.seed)
    device = choose_device(args.device)

    dataset = load_signal_dataset(args.signal_archive, args.index)
    truth_pairs = truth_pairs_from_metadata(dataset.metadata)
    train_samples, validation_sample, holdout_sample = choose_sample_split(
        truth_pairs, args.holdout_sample, args.validation_sample
    )
    grouped = indices_by_sample(dataset.metadata)
    selected_grouped = {
        sample: cap_indices(indices, args.max_rows_per_sample)
        for sample, indices in grouped.items()
        if sample in truth_pairs
    }
    split_labels = make_split_labels(
        dataset.metadata, train_samples, validation_sample, holdout_sample
    )
    selected_indices = np.sort(np.concatenate(list(selected_grouped.values())))

    train_indices = np.concatenate([selected_grouped[sample] for sample in train_samples])
    train_lengths = dataset.mask[train_indices].sum(axis=1).astype(np.float64)
    lengths_by_sample = {
        sample: dataset.mask[selected_grouped[sample]].sum(axis=1).astype(np.float64)
        for sample in train_samples
    }
    duration_intercept, duration_slope, duration_centres, duration_prior_rmse = fit_duration_prior(
        lengths_by_sample, truth_pairs, train_samples
    )
    length_mean = float(np.mean(train_lengths))
    length_std = float(np.std(train_lengths))
    model = WeakRepeatCountRNN(
        args.hidden_dim,
        args.rnn_type,
        args.conv_channels,
        args.dropout,
        args.conv_stride1,
        args.conv_stride2,
        length_mean,
        length_std,
        duration_intercept,
        duration_slope,
    ).to(device)
    initialize_residual_head(model)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )

    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    best_epoch = 0
    if validation_sample is None:
        initial_validation_loss = math.inf
        initial_validation_allele_mae = math.inf
        best_validation_loss = math.inf
        best_validation_allele_mae = math.inf
        best_selection_value = math.inf
    else:
        initial_validation_loss = validation_loss(
            model,
            dataset,
            selected_grouped[validation_sample],
            truth_pairs[validation_sample],
            device,
            args.label_noise,
            args.min_component_fraction,
            args.coverage_weight,
            args.entropy_weight,
            args.assignment_mode,
            not args.no_component_balance,
            args.beta_nll,
            args.mean_loss_weight,
            args.mean_huber_delta,
        )
        initial_validation_allele_mae = validation_allele_mae(
            model,
            dataset,
            selected_grouped[validation_sample],
            truth_pairs[validation_sample],
            device,
        )
        best_validation_loss = initial_validation_loss
        best_validation_allele_mae = initial_validation_allele_mae
        best_selection_value = (
            initial_validation_allele_mae
            if args.validation_selection == "allele-mae"
            else initial_validation_loss
        )
        print(
            f"epoch=0 validation_loss={initial_validation_loss:.4f} "
            f"validation_allele_mae={initial_validation_allele_mae:.4f}",
            flush=True,
        )
    history: list[tuple[float, float, float, float, float]] = []
    for epoch in range(1, args.epochs + 1):
        train_loss, train_nll, train_coverage = train_epoch(
            model,
            optimizer,
            dataset,
            selected_grouped,
            truth_pairs,
            train_samples,
            device,
            rng,
            args.bag_size,
            args.bags_per_sample,
            args.label_noise,
            args.min_component_fraction,
            args.coverage_weight,
            args.entropy_weight,
            args.assignment_mode,
            not args.no_component_balance,
            args.beta_nll,
            args.mean_loss_weight,
            args.mean_huber_delta,
        )
        if validation_sample is None:
            current_validation_loss = train_loss
            current_validation_allele_mae = math.inf
            current_selection_value = train_loss
        else:
            current_validation_loss = validation_loss(
                model,
                dataset,
                selected_grouped[validation_sample],
                truth_pairs[validation_sample],
                device,
                args.label_noise,
                args.min_component_fraction,
                args.coverage_weight,
                args.entropy_weight,
                args.assignment_mode,
                not args.no_component_balance,
                args.beta_nll,
                args.mean_loss_weight,
                args.mean_huber_delta,
            )
            current_validation_allele_mae = validation_allele_mae(
                model,
                dataset,
                selected_grouped[validation_sample],
                truth_pairs[validation_sample],
                device,
            )
            current_selection_value = (
                current_validation_allele_mae
                if args.validation_selection == "allele-mae"
                else current_validation_loss
            )
        history.append(
            (
                train_loss,
                train_nll,
                train_coverage,
                current_validation_loss,
                current_validation_allele_mae,
            )
        )
        if current_selection_value < best_selection_value:
            best_selection_value = current_selection_value
            best_validation_loss = current_validation_loss
            best_validation_allele_mae = current_validation_allele_mae
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        print(
            f"epoch={epoch} train_loss={train_loss:.4f} train_nll={train_nll:.4f} "
            f"coverage={train_coverage:.6f} validation_loss={current_validation_loss:.4f} "
            f"validation_allele_mae={current_validation_allele_mae:.4f}",
            flush=True,
        )

    model.load_state_dict(best_state)
    predictions, raw_variances = predict_indices(
        model, dataset, selected_indices, device, args.prediction_batch_size
    )
    if validation_sample is None:
        uncertainty_scale = 1.0
    else:
        uncertainty_scale = calibrate_variance_scale(
            predictions,
            raw_variances,
            selected_grouped[validation_sample],
            truth_pairs[validation_sample],
        )
    variances = raw_variances * uncertainty_scale**2
    write_predictions(
        args.predictions,
        dataset,
        predictions,
        raw_variances,
        variances,
        split_labels,
    )
    calls = call_samples(
        dataset,
        predictions,
        variances,
        split_labels,
        truth_pairs,
        args.min_rows,
        args.min_separation,
        args.caller_min_component_fraction,
        args.bic_margin,
    )
    write_tsv(args.calls, calls, CALL_FIELDS)

    nearest_errors = []
    for sample, indices in selected_grouped.items():
        short_truth, long_truth = truth_pairs[sample]
        nearest_errors.extend(
            np.minimum(
                np.abs(predictions[indices] - short_truth),
                np.abs(predictions[indices] - long_truth),
            ).tolist()
        )
    test_calls = [row for row in calls if row["split_scope"] == "test"]
    test_allele_mae = ""
    test_candidate_allele_mae = ""
    if len(test_calls) == 1:
        test_candidate_allele_mae = f"{np.mean([abs(float(test_calls[0]['candidate_long']) - truth_pairs[holdout_sample][1]), abs(float(test_calls[0]['candidate_short']) - truth_pairs[holdout_sample][0])]):.3f}"
        if test_calls[0]["resolved"] == "True":
            test_allele_mae = f"{np.mean([abs(float(test_calls[0]['long_error'])), abs(float(test_calls[0]['short_error']))]):.3f}"

    metrics: dict[str, object] = {
        "supervision": "unordered_sample_diploid_genotype",
        "per_read_group_labels_used_for_training": "False",
        "sample_disjoint_test": "True",
        "sample_disjoint_validation": str(validation_sample is not None),
        "train_samples": ";".join(train_samples),
        "validation_sample": validation_sample or "",
        "validation_selection": args.validation_selection,
        "holdout_sample": holdout_sample,
        "rows_selected": selected_indices.size,
        "max_rows_per_sample": args.max_rows_per_sample,
        "device": str(device),
        "rnn_type": args.rnn_type,
        "assignment_mode": args.assignment_mode,
        "beta_nll": args.beta_nll,
        "mean_loss_weight": args.mean_loss_weight,
        "mean_huber_delta": args.mean_huber_delta,
        "balanced_latent_components": str(not args.no_component_balance),
        "raw_duration_feature": "True",
        "train_only_duration_prior": "True",
        "duration_prior_intercept": f"{duration_intercept:.9f}",
        "duration_prior_slope": f"{duration_slope:.9f}",
        "duration_prior_train_point_rmse": f"{duration_prior_rmse:.6f}",
        "duration_prior_centres": ";".join(
            f"{sample}:{centres[0]:.1f},{centres[1]:.1f}"
            for sample, centres in duration_centres.items()
        ),
        "train_length_mean": f"{length_mean:.6f}",
        "train_length_std": f"{length_std:.6f}",
        "training_min_component_fraction": args.min_component_fraction,
        "caller_min_component_fraction": args.caller_min_component_fraction,
        "validation_uncertainty_scale": f"{uncertainty_scale:.6f}",
        "epochs": args.epochs,
        "best_epoch": best_epoch,
        "initial_validation_loss": f"{initial_validation_loss:.6f}" if np.isfinite(initial_validation_loss) else "",
        "initial_validation_allele_mae": f"{initial_validation_allele_mae:.6f}" if np.isfinite(initial_validation_allele_mae) else "",
        "best_validation_loss": f"{best_validation_loss:.6f}",
        "best_validation_allele_mae": f"{best_validation_allele_mae:.6f}" if np.isfinite(best_validation_allele_mae) else "",
        "initial_train_loss": f"{history[0][0]:.6f}",
        "final_train_loss": f"{history[-1][0]:.6f}",
        "nearest_known_allele_read_mae": f"{float(np.mean(nearest_errors)):.3f}",
        "test_allele_mae": test_allele_mae,
        "test_candidate_allele_mae": test_candidate_allele_mae,
        "test_resolved": test_calls[0]["resolved"] if len(test_calls) == 1 else "",
        "note": "Experimental train-only duration prior plus Conv-BiRNN residual, latent unordered diploid supervision, and heteroscedastic abstaining inference. Mixture confidence measures within-sample separation only, not genotype accuracy.",
    }
    write_tsv(
        args.summary,
        [{"metric": key, "value": value} for key, value in metrics.items()],
        SUMMARY_FIELDS,
    )
    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "args": vars(args),
            "metrics": metrics,
            "truth_pairs": truth_pairs,
        },
        args.checkpoint,
    )
    print(f"Wrote predictions to {args.predictions}")
    print(f"Wrote allele calls to {args.calls}")
    print(f"Wrote summary to {args.summary}")
    print(f"Wrote checkpoint to {args.checkpoint}")


if __name__ == "__main__":
    main()
