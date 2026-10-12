#!/usr/bin/env python3
"""Uncertainty-aware one-versus-two allele inference.

The caller consumes a repeat-count mean and variance for every read. It fits
heteroscedastic Gaussian models, compares one- and two-allele explanations by
BIC, and returns an unresolved consensus instead of forcing two alleles when
the evidence is weak.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AlleleCall:
    pred_long: float
    pred_short: float
    candidate_long: float
    candidate_short: float
    consensus: float
    resolved: bool
    support_long: int
    support_short: int
    weight_long: float
    weight_short: float
    bic_one: float
    bic_two: float
    bic_gain: float
    separation: float
    confidence: str
    reason: str


def _logsumexp(values: np.ndarray, axis: int) -> np.ndarray:
    maximum = np.max(values, axis=axis, keepdims=True)
    return np.squeeze(maximum, axis=axis) + np.log(
        np.sum(np.exp(values - maximum), axis=axis)
    )


def _normal_logpdf(values: np.ndarray, means: np.ndarray, variances: np.ndarray) -> np.ndarray:
    return -0.5 * (
        np.log(2.0 * np.pi * variances) + (values - means) ** 2 / variances
    )


def _validate_inputs(values: np.ndarray, variances: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    variances = np.asarray(variances, dtype=np.float64).reshape(-1)
    if values.size != variances.size:
        raise ValueError("values and variances must have the same length")
    if values.size < 2:
        raise ValueError("at least two read predictions are required")
    usable = np.isfinite(values) & np.isfinite(variances) & (variances >= 0.0)
    values = values[usable]
    variances = variances[usable]
    if values.size < 2:
        raise ValueError("at least two finite read predictions are required")
    return values, variances


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    ordered_values = values[order]
    ordered_weights = np.maximum(weights[order], 0.0)
    total = float(ordered_weights.sum())
    if total <= 0.0:
        return float(np.median(ordered_values))
    cutoff = 0.5 * total
    position = int(np.searchsorted(np.cumsum(ordered_weights), cutoff, side="left"))
    return float(ordered_values[min(position, ordered_values.size - 1)])


def _fit_one(
    values: np.ndarray,
    read_variances: np.ndarray,
    variance_floor: float,
) -> tuple[float, float, float]:
    initial_precision = 1.0 / (read_variances + variance_floor)
    initial_center = float(np.sum(initial_precision * values) / np.sum(initial_precision))
    residual_excess = np.maximum((values - initial_center) ** 2 - read_variances, 0.0)
    intrinsic = _weighted_median(residual_excess, initial_precision)
    total_variance = read_variances + intrinsic + variance_floor
    precision = 1.0 / total_variance
    center = float(np.sum(precision * values) / np.sum(precision))
    residual_excess = np.maximum((values - center) ** 2 - read_variances, 0.0)
    intrinsic = _weighted_median(residual_excess, precision)
    total_variance = read_variances + intrinsic + variance_floor
    log_likelihood = float(
        np.sum(_normal_logpdf(values, center, total_variance))
    )
    return center, intrinsic, log_likelihood


def _fit_two(
    values: np.ndarray,
    read_variances: np.ndarray,
    variance_floor: float,
    max_iterations: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    centers = np.asarray(
        [np.quantile(values, 0.25), np.quantile(values, 0.75)],
        dtype=np.float64,
    )
    if abs(float(centers[1] - centers[0])) < 1e-6:
        centers = np.asarray([float(values.min()), float(values.max())])
    intrinsic = np.full(2, max(float(np.var(values)) * 0.10, 0.0), dtype=np.float64)
    weights = np.asarray([0.5, 0.5], dtype=np.float64)
    responsibilities = np.full((values.size, 2), 0.5, dtype=np.float64)

    previous_likelihood = -np.inf
    for _ in range(max_iterations):
        total_variance = (
            read_variances[:, None] + intrinsic[None, :] + variance_floor
        )
        log_components = (
            np.log(np.clip(weights, 1e-8, 1.0))[None, :]
            + _normal_logpdf(
                values[:, None], centers[None, :], total_variance
            )
        )
        log_mixture = _logsumexp(log_components, axis=1)
        likelihood = float(np.sum(log_mixture))
        responsibilities = np.exp(log_components - log_mixture[:, None])

        mass = np.maximum(responsibilities.sum(axis=0), 1e-8)
        weights = mass / values.size
        for component in (0, 1):
            precision_weight = responsibilities[:, component] / total_variance[:, component]
            denominator = float(precision_weight.sum())
            if denominator <= 1e-8:
                continue
            centers[component] = float(np.sum(precision_weight * values) / denominator)
            residual_excess = np.maximum(
                (values - centers[component]) ** 2 - read_variances,
                0.0,
            )
            intrinsic[component] = _weighted_median(
                residual_excess,
                precision_weight,
            )

        if abs(likelihood - previous_likelihood) < 1e-6:
            break
        previous_likelihood = likelihood

    total_variance = read_variances[:, None] + intrinsic[None, :] + variance_floor
    log_components = (
        np.log(np.clip(weights, 1e-8, 1.0))[None, :]
        + _normal_logpdf(values[:, None], centers[None, :], total_variance)
    )
    log_mixture = _logsumexp(log_components, axis=1)
    responsibilities = np.exp(log_components - log_mixture[:, None])
    likelihood = float(np.sum(log_mixture))

    order = np.argsort(centers)
    return centers[order], weights[order], responsibilities[:, order], likelihood


def call_alleles_with_uncertainty(
    values: np.ndarray,
    variances: np.ndarray,
    *,
    min_separation: float = 3.0,
    min_component_fraction: float = 0.10,
    bic_margin: float = 6.0,
    variance_floor: float = 1.0,
    max_iterations: int = 100,
) -> AlleleCall:
    """Fit one/two heteroscedastic components and make an abstaining call."""
    values, variances = _validate_inputs(values, variances)
    consensus, _, log_likelihood_one = _fit_one(values, variances, variance_floor)
    centers, weights, responsibilities, log_likelihood_two = _fit_two(
        values, variances, variance_floor, max_iterations
    )

    sample_size = values.size
    bic_one = -2.0 * log_likelihood_one + 2.0 * np.log(sample_size)
    bic_two = -2.0 * log_likelihood_two + 5.0 * np.log(sample_size)
    bic_gain = float(bic_one - bic_two)
    separation = float(centers[1] - centers[0])
    assignments = np.argmax(responsibilities, axis=1)
    support_short = int(np.sum(assignments == 0))
    support_long = int(np.sum(assignments == 1))
    minor_weight = float(np.min(weights))

    reasons: list[str] = []
    if bic_gain < bic_margin:
        reasons.append("one_allele_model_preferred")
    if separation < min_separation:
        reasons.append("insufficient_separation")
    if minor_weight < min_component_fraction:
        reasons.append("low_minor_allele_support")
    resolved = not reasons

    if resolved:
        pred_short = float(centers[0])
        pred_long = float(centers[1])
        if bic_gain >= 20.0 and minor_weight >= 0.20:
            confidence = "high"
            reason = "two_allele_model_strong"
        else:
            confidence = "moderate"
            reason = "two_allele_model_supported"
    else:
        pred_short = consensus
        pred_long = consensus
        confidence = "low"
        reason = ";".join(reasons)

    return AlleleCall(
        pred_long=pred_long,
        pred_short=pred_short,
        candidate_long=float(centers[1]),
        candidate_short=float(centers[0]),
        consensus=consensus,
        resolved=resolved,
        support_long=support_long,
        support_short=support_short,
        weight_long=float(weights[1]),
        weight_short=float(weights[0]),
        bic_one=float(bic_one),
        bic_two=float(bic_two),
        bic_gain=bic_gain,
        separation=separation,
        confidence=confidence,
        reason=reason,
    )
