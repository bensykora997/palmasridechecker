"""Self-calibration for the Palmas ride prediction.

Pure-Python (stdlib only — requirements.txt is intentionally dependency-free).
Learns from the app's own logged track record (forecast features + observed
ground truth) and produces a "shadow" model that is *displayed* but never
overrides the hand-tuned decision (shadow mode).

The learner self-stages by data volume so it can't overfit on the small,
class-imbalanced dataset we currently have:

    Stage 0  threshold   >= 8 evaluated, >= 2 of each class
             Keep the hand-tuned score; tune the YES/NO cutoff (prod = 50).
    Stage 1  probability >= 20 evaluated, >= 4 rained
             Platt scaling P(rain) = sigmoid(a*score + b); decide on probability.
    Stage 2  weights     >= 40 featured, >= 8 rained
             L2-regularized logistic regression on the 4 z-scored features.

Honesty under imbalance: we report BOTH raw accuracy and balanced accuracy
(mean of per-class accuracy), and challenger accuracy is leave-one-out (LOO)
cross-validated while the baseline is the in-sample production behavior — a
deliberately conservative comparison that won't overstate the challenger.

The model targets P(rain in the 05:00-07:30 window). Shadow decision is
"NO" (don't ride) when P(rain) >= the decision threshold, else "YES".
"""

import math

import db  # for _ground_truth_rained (label source of truth)

# ---- Production baseline ----
BASELINE_THRESHOLD = 50          # analyze.py: decision = YES if score >= 50
RIDE_PROB_CUTOFF = 0.5           # Platt/weights: predict rain if P(rain) >= this

# ---- Stage unlock minimums ----
MIN_EVAL_THRESHOLD = 8
MIN_CLASS_THRESHOLD = 2          # >= this many of EACH class
MIN_EVAL_PROBABILITY = 20
MIN_RAINED_PROBABILITY = 4
MIN_FEAT_WEIGHTS = 40
MIN_RAINED_WEIGHTS = 8

FEATURE_KEYS = ["avg_precip_prob", "max_wind", "avg_humidity", "overnight_precip_mm"]

STAGE_ORDER = ["gathering", "threshold", "probability", "weights"]


# ====================================================================
# Data extraction
# ====================================================================

def entry_label(entry):
    """1 if it (ground-truth) rained, 0 if dry, None if no ground truth.

    Reuses db._ground_truth_rained so user overrides take priority over
    sensor-detected actuals — exactly the same truth the History verdict uses.
    """
    truth = db._ground_truth_rained(entry)
    if truth is None:
        return None
    return 1 if truth else 0


def entry_score(entry):
    # Always the canonical (night-before) score. The `morning` slot is a
    # pre-dawn re-score kept as observational data only and is deliberately
    # NOT used for calibration — we grade the actionable planning call.
    s = entry.get("score")
    return float(s) if isinstance(s, (int, float)) else None


def entry_features(entry):
    """Return [avg_precip_prob, max_wind, avg_humidity, overnight_precip_mm]
    or None if any are missing."""
    fc = entry.get("forecast") or {}
    vals = []
    for k in FEATURE_KEYS:
        v = fc.get(k)
        if v is None or not isinstance(v, (int, float)):
            return None
        vals.append(float(v))
    return vals


def _scored_dataset(entries):
    """[(score, label)] over entries that have both."""
    out = []
    for e in entries:
        s, y = entry_score(e), entry_label(e)
        if s is not None and y is not None:
            out.append((s, y))
    return out


def _featured_dataset(entries):
    """[(features, label)] over entries that have all 4 features + a label."""
    out = []
    for e in entries:
        x, y = entry_features(e), entry_label(e)
        if x is not None and y is not None:
            out.append((x, y))
    return out


# ====================================================================
# Math primitives
# ====================================================================

def _sigmoid(z):
    if z < -60:
        return 0.0
    if z > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def _standardize_cols(X):
    """Z-score each column. Returns (standardized_X, means, stds)."""
    n = len(X)
    d = len(X[0])
    means = [sum(row[j] for row in X) / n for j in range(d)]
    stds = []
    for j in range(d):
        var = sum((row[j] - means[j]) ** 2 for row in X) / n
        stds.append(math.sqrt(var) if var > 1e-12 else 1.0)
    Z = [[(row[j] - means[j]) / stds[j] for j in range(d)] for row in X]
    return Z, means, stds


def _apply_standardize(x, means, stds):
    return [(x[j] - means[j]) / stds[j] for j in range(len(x))]


def _fit_logistic(X, y, l2=1.0, iters=3000, lr=0.3):
    """Plain gradient-descent logistic regression with L2 on weights (not bias).

    X: list of feature rows (already standardized). y: list of 0/1.
    Class-weighted loss so the minority (rain) class isn't ignored under
    imbalance. Returns (weights, bias).
    """
    n = len(X)
    d = len(X[0])
    w = [0.0] * d
    b = 0.0

    n_pos = sum(y) or 1
    n_neg = (n - sum(y)) or 1
    # Balanced class weights: each class contributes equally in aggregate.
    wt_pos = n / (2.0 * n_pos)
    wt_neg = n / (2.0 * n_neg)

    for _ in range(iters):
        gw = [0.0] * d
        gb = 0.0
        for i in range(n):
            z = b + sum(w[j] * X[i][j] for j in range(d))
            p = _sigmoid(z)
            err = p - y[i]
            cw = wt_pos if y[i] == 1 else wt_neg
            err *= cw
            for j in range(d):
                gw[j] += err * X[i][j]
            gb += err
        for j in range(d):
            gw[j] = gw[j] / n + l2 * w[j] / n
            w[j] -= lr * gw[j]
        b -= lr * (gb / n)
    return w, b


# ====================================================================
# Metrics
# ====================================================================

def _accuracies(pred_rain, labels):
    """Return (raw_accuracy, balanced_accuracy) given predicted-rain booleans
    and 0/1 labels."""
    n = len(labels)
    if n == 0:
        return None, None
    correct = sum(1 for p, y in zip(pred_rain, labels) if int(p) == y)
    raw = correct / n
    # Balanced: mean of per-class recall
    pos = [i for i, y in enumerate(labels) if y == 1]
    neg = [i for i, y in enumerate(labels) if y == 0]
    parts = []
    if pos:
        parts.append(sum(1 for i in pos if int(pred_rain[i]) == 1) / len(pos))
    if neg:
        parts.append(sum(1 for i in neg if int(pred_rain[i]) == 0) / len(neg))
    balanced = sum(parts) / len(parts) if parts else None
    return round(raw, 4), (round(balanced, 4) if balanced is not None else None)


# ====================================================================
# Stage 0 — threshold tuning
# ====================================================================

def _best_threshold(scores, labels):
    """Pick the score cutoff that maximizes balanced accuracy. Predict rain
    when score < threshold (low score = bad weather = rain)."""
    candidates = sorted(set(scores)) + [min(scores) - 1, max(scores) + 1]
    best_thr, best_bal = BASELINE_THRESHOLD, -1.0
    for thr in candidates:
        pred_rain = [s < thr for s in scores]
        _, bal = _accuracies(pred_rain, labels)
        if bal is not None and bal > best_bal:
            best_bal, best_thr = bal, thr
    return best_thr


def _loo_threshold(data):
    """Leave-one-out: tune threshold on the rest, predict the held-out point."""
    n = len(data)
    preds, labels = [], []
    for i in range(n):
        rest = data[:i] + data[i + 1:]
        thr = _best_threshold([s for s, _ in rest], [y for _, y in rest])
        s_i, y_i = data[i]
        preds.append(s_i < thr)
        labels.append(y_i)
    return _accuracies(preds, labels)


# ====================================================================
# Platt scaling (score -> probability) — display + stage 1 decision
# ====================================================================

def _fit_platt(scores, labels):
    """Fit P(rain) = sigmoid(a*z + b) where z is the standardized score.
    Returns dict with a, b in *raw score* space plus the standardizer."""
    X = [[s] for s in scores]
    Z, means, stds = _standardize_cols(X)
    w, b = _fit_logistic(Z, labels, l2=0.5, iters=3000, lr=0.3)
    return {"a": w[0], "b": b, "mean": means[0], "std": stds[0]}


def _platt_prob(platt, score):
    z = (score - platt["mean"]) / platt["std"]
    return _sigmoid(platt["a"] * z + platt["b"])


def _loo_platt(data):
    n = len(data)
    preds, labels = [], []
    for i in range(n):
        rest = data[:i] + data[i + 1:]
        platt = _fit_platt([s for s, _ in rest], [y for _, y in rest])
        s_i, y_i = data[i]
        preds.append(_platt_prob(platt, s_i) >= RIDE_PROB_CUTOFF)
        labels.append(y_i)
    return _accuracies(preds, labels)


# ====================================================================
# Stage 2 — feature weights
# ====================================================================

def _loo_weights(data, l2):
    n = len(data)
    preds, labels = [], []
    for i in range(n):
        rest = data[:i] + data[i + 1:]
        X = [x for x, _ in rest]
        y = [yy for _, yy in rest]
        Z, means, stds = _standardize_cols(X)
        w, b = _fit_logistic(Z, y, l2=l2)
        x_i, y_i = data[i]
        z_i = _apply_standardize(x_i, means, stds)
        p = _sigmoid(b + sum(w[j] * z_i[j] for j in range(len(w))))
        preds.append(p >= RIDE_PROB_CUTOFF)
        labels.append(y_i)
    return _accuracies(preds, labels)


# ====================================================================
# Top-level training
# ====================================================================

def _baseline_accuracy(scored):
    """Production behavior: predict rain when score < 50 (in-sample)."""
    preds = [s < BASELINE_THRESHOLD for s, _ in scored]
    labels = [y for _, y in scored]
    return _accuracies(preds, labels)


def _gathering(reason, scored, featured):
    n_rain = sum(y for _, y in scored)
    return {
        "stage": "gathering",
        "stage_index": 0,
        "reason": reason,
        "n_evaluated": len(scored),
        "n_rained": n_rain,
        "n_dry": len(scored) - n_rain,
        "n_featured": len(featured),
        "next_unlock": {"stage": "threshold",
                        "at_evaluated": MIN_EVAL_THRESHOLD,
                        "needs_each_class": MIN_CLASS_THRESHOLD},
        "champion": "hand_tuned",
        "model_version": 1,
    }


def train_calibration(entries, trained_at=None):
    """Train the staged shadow model on the logged predictions. Returns the
    calibration state dict (JSON-serializable). Never raises on sparse/
    degenerate data — degrades to a 'gathering' state."""
    scored = _scored_dataset(entries)
    featured = _featured_dataset(entries)
    n = len(scored)
    n_rain = sum(y for _, y in scored)
    n_dry = n - n_rain

    base_raw, base_bal = _baseline_accuracy(scored) if scored else (None, None)

    # Below stage-0 minimums → gathering.
    if n < MIN_EVAL_THRESHOLD or n_rain < MIN_CLASS_THRESHOLD or n_dry < MIN_CLASS_THRESHOLD:
        need = []
        if n < MIN_EVAL_THRESHOLD:
            need.append(f"{MIN_EVAL_THRESHOLD - n} more evaluated day(s)")
        if n_rain < MIN_CLASS_THRESHOLD:
            need.append(f"{MIN_CLASS_THRESHOLD - n_rain} more rained day(s)")
        if n_dry < MIN_CLASS_THRESHOLD:
            need.append(f"{MIN_CLASS_THRESHOLD - n_dry} more dry day(s)")
        state = _gathering("Need " + ", ".join(need), scored, featured)
        state["baseline"] = {"threshold": BASELINE_THRESHOLD,
                             "accuracy": base_raw, "balanced_accuracy": base_bal}
        if trained_at:
            state["trained_at"] = trained_at
        return state

    # A Platt fit (full data) gives a displayable probability at every stage.
    platt_full = _fit_platt([s for s, _ in scored], [y for _, y in scored])

    # Decide the highest unlocked stage.
    can_weights = (len(featured) >= MIN_FEAT_WEIGHTS
                   and sum(y for _, y in featured) >= MIN_RAINED_WEIGHTS)
    can_prob = n >= MIN_EVAL_PROBABILITY and n_rain >= MIN_RAINED_PROBABILITY

    calibrated = {"platt": platt_full, "threshold": None,
                  "weights": None, "feature_means": None,
                  "feature_stds": None, "feature_keys": FEATURE_KEYS}

    if can_weights:
        stage, stage_index = "weights", 3
        X = [x for x, _ in featured]
        y = [yy for _, yy in featured]
        Z, means, stds = _standardize_cols(X)
        # Pick L2 by LOO balanced accuracy over a small grid.
        best = None
        for l2 in (0.1, 0.5, 1.0, 2.0, 5.0):
            raw, bal = _loo_weights(featured, l2)
            key = (bal if bal is not None else -1, raw if raw is not None else -1)
            if best is None or key > best[0]:
                best = (key, l2, raw, bal)
        _, l2_best, cal_raw, cal_bal = best
        w, b = _fit_logistic(Z, y, l2=l2_best)
        calibrated["weights"] = {"coef": w, "bias": b, "l2": l2_best}
        calibrated["feature_means"] = means
        calibrated["feature_stds"] = stds
        next_unlock = None
    elif can_prob:
        stage, stage_index = "probability", 2
        cal_raw, cal_bal = _loo_platt(scored)
        next_unlock = {"stage": "weights", "at_featured": MIN_FEAT_WEIGHTS,
                       "needs_rained": MIN_RAINED_WEIGHTS}
    else:
        stage, stage_index = "threshold", 1
        thr = _best_threshold([s for s, _ in scored], [y for _, y in scored])
        calibrated["threshold"] = thr
        cal_raw, cal_bal = _loo_threshold(scored)
        next_unlock = {"stage": "probability", "at_evaluated": MIN_EVAL_PROBABILITY,
                       "needs_rained": MIN_RAINED_PROBABILITY}

    calibrated["accuracy"] = cal_raw
    calibrated["balanced_accuracy"] = cal_bal

    state = {
        "stage": stage,
        "stage_index": stage_index,
        "n_evaluated": n,
        "n_rained": n_rain,
        "n_dry": n_dry,
        "n_featured": len(featured),
        "baseline": {"threshold": BASELINE_THRESHOLD,
                     "accuracy": base_raw, "balanced_accuracy": base_bal},
        "calibrated": calibrated,
        "next_unlock": next_unlock,
        "champion": "hand_tuned",   # shadow mode; future toggle flips to "calibrated"
        "model_version": 1,
    }
    if trained_at:
        state["trained_at"] = trained_at
    return state


# ====================================================================
# Inference — what would the shadow model say for the current prediction?
# ====================================================================

def apply_calibration(cal_state, score, features):
    """Given the trained calibration state, the current hand-tuned score, and
    the current feature vector (or None), return the shadow prediction:

        {shadow_decision: "YES"|"NO", shadow_prob_rain: float|None,
         shadow_basis: str, stage: str}

    Returns None if there's no usable model yet (gathering)."""
    if not cal_state or cal_state.get("stage") == "gathering":
        return None

    cal = cal_state.get("calibrated") or {}
    stage = cal_state.get("stage")
    platt = cal.get("platt")

    prob = None
    if stage == "weights" and cal.get("weights") and features is not None:
        means = cal["feature_means"]
        stds = cal["feature_stds"]
        w = cal["weights"]["coef"]
        b = cal["weights"]["bias"]
        z = _apply_standardize(features, means, stds)
        prob = _sigmoid(b + sum(w[j] * z[j] for j in range(len(w))))
        rain = prob >= RIDE_PROB_CUTOFF
        basis = "feature weights"
    elif platt and score is not None and stage in ("probability", "weights"):
        # Stage 1+ always carries a Platt fit. Use it for the probability
        # stage, and as the weights-stage fallback when *this* call has no
        # feature vector (e.g. the forecast was missing a field) — otherwise
        # we'd fall through to the threshold branch where `threshold` is None.
        prob = _platt_prob(platt, score)
        rain = prob >= RIDE_PROB_CUTOFF
        basis = "calibrated probability"
    else:  # threshold stage
        # No probability here on purpose: a Platt fit on a handful of rainy
        # days isn't a trustworthy probability, so we show the decision and
        # the tuned cutoff only. A real probability appears from stage 1 on.
        # `threshold` is stored as None outside the threshold stage, so guard
        # against it rather than comparing `score < None` (a TypeError).
        thr = cal.get("threshold")
        if thr is None:
            thr = BASELINE_THRESHOLD
        rain = (score is not None and score < thr)
        basis = f"tuned threshold ({thr})"

    return {
        "shadow_decision": "NO" if rain else "YES",
        "shadow_prob_rain": round(prob, 4) if prob is not None else None,
        "shadow_basis": basis,
        "stage": stage,
    }
