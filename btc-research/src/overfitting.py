"""Backtest-overfitting controls.

* Deflated Sharpe Ratio — Bailey & López de Prado (2014), as presented in
  *Advances in Financial Machine Learning* §14.7.3 (quant-resources).
* Probability of Backtest Overfitting via Combinatorially Symmetric
  Cross-Validation (CSCV) — Bailey, Borwein, López de Prado & Zhu,
  "The Probability of Backtest Overfitting" (quant-resources).
* Carver's turnover "speed limit" (*Systematic Trading*, "Setting a speed limit").

Sharpe ratios here are PER-PERIOD (not annualised) unless stated.
"""
from itertools import combinations
import math
from statistics import NormalDist

import numpy as np

_N = NormalDist()
EULER_GAMMA = 0.5772156649015329


def sharpe(returns):
    r = np.asarray(returns, dtype=float)
    s = r.std(ddof=1)
    return float(r.mean() / s) if s > 0 else 0.0


def probabilistic_sharpe(returns, benchmark_sr=0.0):
    r = np.asarray(returns, dtype=float)
    t = len(r)
    if t < 3:
        raise ValueError("Need at least 3 observations")
    sr = sharpe(r)
    m, s = r.mean(), r.std(ddof=0)
    if s == 0:
        return 0.0
    z = (r - m) / s
    g3, g4 = float((z ** 3).mean()), float((z ** 4).mean())
    denom = 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2
    if denom <= 0:
        return 0.0
    return _N.cdf((sr - benchmark_sr) * math.sqrt(t - 1) / math.sqrt(denom))


def expected_max_sharpe(sr_variance, n_trials):
    """E[max SR] of n_trials independent zero-skill strategies (per-period)."""
    if n_trials < 2:
        return 0.0
    a = _N.inv_cdf(1 - 1 / n_trials)
    b = _N.inv_cdf(1 - 1 / (n_trials * math.e))
    return math.sqrt(max(sr_variance, 0.0)) * ((1 - EULER_GAMMA) * a + EULER_GAMMA * b)


def deflated_sharpe(returns, trial_sharpes):
    """PSR of the selected strategy against the expected max SR of all trials."""
    trial_sharpes = np.asarray(trial_sharpes, dtype=float)
    sr0 = expected_max_sharpe(trial_sharpes.var(ddof=1) if len(trial_sharpes) > 1 else 0.0,
                              len(trial_sharpes))
    return {"deflated_sharpe": probabilistic_sharpe(returns, sr0), "sr0_per_period": sr0,
            "n_trials": int(len(trial_sharpes))}


def pbo_cscv(matrix, n_splits=10):
    """matrix: T x N per-period returns, one column per tried variant."""
    m = np.asarray(matrix, dtype=float)
    t, n = m.shape
    if n < 2:
        raise ValueError("PBO needs at least two variants")
    if n_splits % 2 or n_splits < 4:
        raise ValueError("n_splits must be even and >= 4")
    t_use = (t // n_splits) * n_splits
    if t_use < n_splits * 2:
        raise ValueError("Not enough observations for CSCV")
    blocks = np.array_split(m[t - t_use:], n_splits)
    logits = []
    for is_idx in combinations(range(n_splits), n_splits // 2):
        oos_idx = [k for k in range(n_splits) if k not in is_idx]
        is_r = np.vstack([blocks[k] for k in is_idx])
        oos_r = np.vstack([blocks[k] for k in oos_idx])
        is_sr = np.array([sharpe(is_r[:, j]) for j in range(n)])
        oos_sr = np.array([sharpe(oos_r[:, j]) for j in range(n)])
        best = int(np.argmax(is_sr))
        rank = (oos_sr < oos_sr[best]).sum() + 0.5 * ((oos_sr == oos_sr[best]).sum() - 1) + 1
        w = rank / (n + 1)
        logits.append(math.log(w / (1 - w)))
    logits = np.array(logits)
    return {"pbo": float((logits <= 0).mean()), "combinations": int(len(logits)),
            "median_logit": float(np.median(logits)), "n_variants": int(n), "n_splits": n_splits}


def speed_limit(turnover_per_year, standardised_cost, max_cost_sr=0.13):
    """Carver: never spend more than ~1/3 of a realistic 0.4 SR on costs."""
    annual_cost = turnover_per_year * standardised_cost
    return {"annual_cost_sr": annual_cost, "max_cost_sr": max_cost_sr,
            "max_turnover": max_cost_sr / standardised_cost if standardised_cost > 0 else None,
            "passes": bool(annual_cost <= max_cost_sr)}
