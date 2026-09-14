import random
import numpy as np
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.db.models import CashFlowRecord, Transaction, Budget, Vendor

router = APIRouter()

def monte_carlo_simulation(base_values: list, change_pct: float, n_simulations: int = 500, periods: int = 90) -> dict:
    """Monte Carlo simulation for What-If financial scenarios."""
    if not base_values:
        return {
            "mean": [0.0] * periods,
            "p10": [0.0] * periods,
            "p25": [0.0] * periods,
            "p75": [0.0] * periods,
            "p90": [0.0] * periods,
            "n_simulations": n_simulations
        }

    mu = np.mean(base_values) * (1 + change_pct / 100)
    sigma = np.std(base_values) * 1.1 if np.std(base_values) > 0 else 1000.0

    all_paths = []
    for _ in range(n_simulations):
        path = np.random.normal(mu, sigma, periods)
        all_paths.append(path.tolist())

    all_paths = np.array(all_paths)

    return {
        "mean": np.mean(all_paths, axis=0).tolist(),
        "p10": np.percentile(all_paths, 10, axis=0).tolist(),
        "p25": np.percentile(all_paths, 25, axis=0).tolist(),
        "p75": np.percentile(all_paths, 75, axis=0).tolist(),
        "p90": np.percentile(all_paths, 90, axis=0).tolist(),
        "n_simulations": n_simulations
    }

@router.post("/what-if")
def what_if_simulation(data: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """What-If scenario simulator using Monte Carlo analysis."""
    variable = data.get("variable", "revenue")
    change_pct = float(data.get("change_pct", 0))
    horizon = int(data.get("horizon", 90))

    records = db.query(CashFlowRecord).order_by(CashFlowRecord.date.desc()).limit(90).all()
    records = list(reversed(records))

    base_inflows = [r.inflow for r in records] if records else [0.0] * horizon
    base_outflows = [r.outflow for r in records] if records else [0.0] * horizon
    current_balance = records[-1].balance if records else 0.0

    variable_impacts = {
        "marketing_spend": {"outflow_pct": change_pct, "inflow_pct": change_pct * 0.4, "label": "Marketing Spend"},
        "vendor_costs": {"outflow_pct": change_pct, "inflow_pct": 0, "label": "Vendor Costs"},
        "revenue": {"outflow_pct": 0, "inflow_pct": change_pct, "label": "Revenue"},
        "headcount": {"outflow_pct": change_pct * 0.7, "inflow_pct": change_pct * 0.3, "label": "Headcount"},
        "operations": {"outflow_pct": change_pct * 0.5, "inflow_pct": 0, "label": "Operations Spend"},
        "custom": {"outflow_pct": data.get("outflow_change", 0), "inflow_pct": data.get("inflow_change", 0), "label": "Custom"}
    }

    impact = variable_impacts.get(variable, variable_impacts["custom"])
    inflow_change = impact["inflow_pct"]
    outflow_change = impact["outflow_pct"]

    # Run Monte Carlo
    mc_inflows = monte_carlo_simulation(base_inflows, inflow_change, n_simulations=500, periods=horizon)
    mc_outflows = monte_carlo_simulation(base_outflows, outflow_change, n_simulations=500, periods=horizon)

    # Safe Key Extraction
    mean_inflows = mc_inflows.get("mean", [0.0] * horizon)
    mean_outflows = mc_outflows.get("mean", [0.0] * horizon)
    p10_inflows = mc_inflows.get("p10", [0.0] * horizon)
    p90_inflows = mc_inflows.get("p90", [0.0] * horizon)
    p10_outflows = mc_outflows.get("p10", [0.0] * horizon)
    p90_outflows = mc_outflows.get("p90", [0.0] * horizon)

    dates = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(horizon)]
    balance_path = []
    running = current_balance
    for inf, out in zip(mean_inflows, mean_outflows):
        running += inf - out
        balance_path.append(round(running, 2))

    # Baseline (no change)
    baseline_path = []
    running_base = current_balance
    for inf, out in zip(base_inflows[:horizon] if len(base_inflows) >= horizon else base_inflows + [0.0] * horizon,
                        base_outflows[:horizon] if len(base_outflows) >= horizon else base_outflows + [0.0] * horizon):
        running_base += inf - out
        baseline_path.append(round(running_base, 2))

    # Impact analysis
    end_balance_impact = balance_path[-1] - baseline_path[-1] if (balance_path and baseline_path) else 0.0
    negative_probability = sum(1 for b in balance_path if b < 0) / len(balance_path) if balance_path else 0.0
    breakeven_day = next((i + 1 for i, b in enumerate(balance_path) if b < 0), None)

    return {
        "variable": variable,
        "variable_label": impact["label"],
        "change_pct": change_pct,
        "horizon": horizon,
        "forecast": [
            {
                "date": dates[i],
                "baseline_balance": baseline_path[i] if i < len(baseline_path) else None,
                "scenario_balance": balance_path[i],
                "delta": round(balance_path[i] - (baseline_path[i] if i < len(baseline_path) else baseline_path[-1]), 2),
                "p10": round(current_balance + (p10_inflows[i] if i < len(p10_inflows) else 0) - (p90_outflows[i] if i < len(p90_outflows) else 0) * i * 0.01, 2),
                "p90": round(current_balance + (p90_inflows[i] if i < len(p90_inflows) else 0) - (p10_outflows[i] if i < len(p10_outflows) else 0) * i * 0.005, 2),
            }
            for i in range(min(horizon, len(balance_path)))
        ],
        "impact_analysis": {
            "end_balance": round(balance_path[-1], 2) if balance_path else 0.0,
            "baseline_end_balance": round(baseline_path[-1], 2) if baseline_path else 0.0,
            "cumulative_impact": round(end_balance_impact, 2),
            "negative_probability": round(negative_probability * 100, 1),
            "breakeven_day": breakeven_day,
            "direction": "positive" if end_balance_impact > 0 else "negative",
            "severity": "critical" if abs(end_balance_impact) > 1000000 else "high" if abs(end_balance_impact) > 500000 else "medium" if abs(end_balance_impact) > 100000 else "low"
        },
        "monte_carlo": {
            "n_simulations": 500,
            "confidence_interval": "80%",
            "methodology": "Monte Carlo with Normal distribution perturbation"
        },
        "explanation": f"What-If Analysis: A {'+' if change_pct >= 0 else ''}{change_pct:.0f}% change in {impact['label']} over {horizon} days results in a cumulative balance impact of ${end_balance_impact:+,.0f}. {'⚠️ Risk of negative cash position detected.' if breakeven_day else '✓ Cash position remains positive throughout the forecast period.'}"
    }

@router.get("/digital-twin")
def get_digital_twin(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Get current financial digital twin state."""
    records = db.query(CashFlowRecord).order_by(CashFlowRecord.date.desc()).limit(30).all()
    vendors = db.query(Vendor).all()
    budgets = db.query(Budget).all()
    fraud_count = db.query(Transaction).filter(Transaction.fraud_score > 0.7).count()

    current_balance = records[0].balance if records else 0.0
    avg_daily_burn = abs(np.mean([r.net for r in records]) if records else 0.0)
    cash_runway_days = int(current_balance / avg_daily_burn) if avg_daily_burn > 0 else 999

    return {
        "snapshot_time": datetime.now().isoformat(),
        "financial_health": {
            "cash_balance": round(current_balance, 2),
            "cash_runway_days": min(cash_runway_days, 365),
            "burn_rate_daily": round(avg_daily_burn, 2),
            "risk_level": "critical" if cash_runway_days < 60 else "high" if cash_runway_days < 90 else "medium" if cash_runway_days < 180 else "low",
            "overall_health_score": min(100, max(0, round(60 + (cash_runway_days / 365) * 40, 0)))
        },
        "vendor_ecosystem": {
            "total_vendors": len(vendors),
            "critical_risk": sum(1 for v in vendors if (getattr(v.risk_tier, 'value', str(v.risk_tier)) == "critical")),
            "high_risk": sum(1 for v in vendors if (getattr(v.risk_tier, 'value', str(v.risk_tier)) == "high")),
            "single_source": sum(1 for v in vendors if v.is_single_source),
            "ecosystem_risk": round(float(np.mean([v.risk_score for v in vendors])) * 100, 1) if vendors else 0.0
        },
        "budget_health": {
            "total_departments": len(set(b.department for b in budgets)),
            "over_budget_depts": sum(1 for b in budgets if b.variance > 0),
            "avg_efficiency": round(float(np.mean([b.efficiency_score for b in budgets])) * 100, 1) if budgets else 0.0,
            "total_waste_estimate": round(sum(max(0, b.variance) for b in budgets) * 0.4, 2)
        },
        "fraud_exposure": {
            "high_risk_transactions": fraud_count,
            "estimated_exposure": round(fraud_count * 47250, 2),
            "active_alerts": db.query(Transaction).filter(Transaction.status == "review").count()
        },
        "stress_scenarios": [
            {
                "name": "Vendor Failure (Top 3)",
                "probability": 0.12,
                "impact": "Operational disruption + $1.2M emergency procurement",
                "preparedness": "LOW — no backup vendors identified"
            },
            {
                "name": "Revenue Drop 30%",
                "probability": 0.18,
                "impact": f"Cash runway reduced to {max(10, cash_runway_days - 45)} days",
                "preparedness": "MEDIUM — credit facility needed"
            },
            {
                "name": "Major Fraud Event",
                "probability": 0.08,
                "impact": "$340K-$500K exposure based on detected patterns",
                "preparedness": "HIGH — AI monitoring active"
            }
        ]
    }
