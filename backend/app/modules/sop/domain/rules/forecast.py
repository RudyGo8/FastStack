"""Deterministic forecast checks. LLMs must never calculate these results."""

from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True)
class ForecastRuleConfig:
    version: str = "forecast-check.v0.1-draft"
    deviation_warning_ratio: float = 0.30
    deviation_high_ratio: float = 0.50
    trend_conflict_ratio: float = 0.10
    minimum_history_months: int = 3


def validate_forecast(
    forecast_qty: float | None,
    history: list[float],
    config: ForecastRuleConfig | None = None,
) -> dict:
    """Validate a submitted forecast against historical actuals.

    The default thresholds are explicitly marked as draft and must be approved by
    the business Owner before production use.
    """
    cfg = config or ForecastRuleConfig()
    clean_history = [float(value) for value in history if value is not None and value >= 0]
    findings: list[dict] = []

    if forecast_qty is None or forecast_qty < 0:
        return {
            "evaluable": False,
            "score": None,
            "level": "not_evaluable",
            "rule_version": cfg.version,
            "baseline_qty": None,
            "deviation_ratio": None,
            "findings": [
                {
                    "code": "FORECAST_MISSING_OR_INVALID",
                    "severity": "high",
                    "message": "预测数量缺失或小于零，不能进行校验。",
                }
            ],
        }

    if len(clean_history) < cfg.minimum_history_months:
        return {
            "evaluable": False,
            "score": None,
            "level": "not_evaluable",
            "rule_version": cfg.version,
            "baseline_qty": None,
            "deviation_ratio": None,
            "findings": [
                {
                    "code": "INSUFFICIENT_HISTORY",
                    "severity": "medium",
                    "message": f"历史数据不足 {cfg.minimum_history_months} 个月，不能形成可靠基线。",
                }
            ],
        }

    recent = clean_history[-6:]
    baseline = fmean(recent)
    score = 100
    deviation_ratio = None if baseline == 0 else (float(forecast_qty) - baseline) / baseline

    if baseline == 0:
        if forecast_qty > 0:
            score -= 35
            findings.append(
                {
                    "code": "ZERO_BASELINE_JUMP",
                    "severity": "high",
                    "message": "近月实际基线为零，但本期预测大于零，需要销售补充依据。",
                }
            )
    elif abs(deviation_ratio) >= cfg.deviation_high_ratio:
        score -= 35
        findings.append(
            {
                "code": "FORECAST_DEVIATION_HIGH",
                "severity": "high",
                "message": f"预测相对近月基线偏离 {abs(deviation_ratio):.1%}。",
            }
        )
    elif abs(deviation_ratio) >= cfg.deviation_warning_ratio:
        score -= 20
        findings.append(
            {
                "code": "FORECAST_DEVIATION_WARNING",
                "severity": "medium",
                "message": f"预测相对近月基线偏离 {abs(deviation_ratio):.1%}。",
            }
        )

    recent_three = clean_history[-3:]
    historical_direction = recent_three[-1] - recent_three[0]
    forecast_direction = float(forecast_qty) - baseline
    direction_threshold = abs(baseline) * cfg.trend_conflict_ratio
    if abs(forecast_direction) >= direction_threshold and historical_direction * forecast_direction < 0:
        score -= 20
        findings.append(
            {
                "code": "TREND_CONFLICT",
                "severity": "medium",
                "message": "预测变化方向与近三个月实际趋势相反，需要补充原因。",
            }
        )

    score = max(0, score)
    level = "low" if score >= 80 else "medium" if score >= 60 else "high"
    if not findings:
        findings.append(
            {
                "code": "NO_RULE_ANOMALY",
                "severity": "info",
                "message": "当前确定性规则未发现明显异常。",
            }
        )

    return {
        "evaluable": True,
        "score": score,
        "level": level,
        "rule_version": cfg.version,
        "baseline_qty": round(baseline, 4),
        "deviation_ratio": round(deviation_ratio, 6) if deviation_ratio is not None else None,
        "findings": findings,
    }
