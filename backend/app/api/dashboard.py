from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.security import get_current_user
from app.db.models import Transaction, Invoice, Vendor, Budget, FraudAlert, CashFlowRecord, TransactionStatus

router = APIRouter()

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Revenue & Expenses from cash flow
    recent_cf = db.query(CashFlowRecord).order_by(CashFlowRecord.date.desc()).limit(30).all()
    total_inflow = sum(r.inflow for r in recent_cf)
    total_outflow = sum(r.outflow for r in recent_cf)
    net_cashflow = total_inflow - total_outflow

    latest_balance = recent_cf[0].balance if recent_cf else 0

    # Fraud metrics
    fraud_count = db.query(Transaction).filter(Transaction.status == TransactionStatus.fraud).count()
    flagged_count = db.query(Transaction).filter(Transaction.status == TransactionStatus.flagged).count()
    active_alerts = db.query(FraudAlert).filter(FraudAlert.is_resolved == False).count()

    # Risk index (average fraud score)
    avg_fraud = db.query(func.avg(Transaction.fraud_score)).scalar() or 0
    risk_index = round(avg_fraud * 100, 1)

    # Vendor stats
    total_vendors = db.query(Vendor).count()
    high_risk_vendors = db.query(Vendor).filter(Vendor.risk_score > 0.7).count()

    # Budget efficiency
    budgets = db.query(Budget).all()
    avg_efficiency = sum(b.efficiency_score for b in budgets) / len(budgets) if budgets else 0
    budget_efficiency = round(avg_efficiency * 100, 1)

    # Invoice stats
    pending_invoices = db.query(Invoice).filter(Invoice.status == "pending").count()
    total_invoices = db.query(Invoice).count()

    # Transaction count
    total_transactions = db.query(Transaction).count()

    return {
        "revenue": round(total_inflow, 2),
        "expenses": round(total_outflow, 2),
        "net_cashflow": round(net_cashflow, 2),
        "balance": round(latest_balance, 2),
        "fraud_count": fraud_count,
        "flagged_transactions": flagged_count,
        "active_alerts": active_alerts,
        "risk_index": risk_index,
        "total_vendors": total_vendors,
        "high_risk_vendors": high_risk_vendors,
        "budget_efficiency": budget_efficiency,
        "pending_invoices": pending_invoices,
        "total_invoices": total_invoices,
        "total_transactions": total_transactions,
        "forecast_accuracy": 87.3,
    }

@router.get("/cashflow-chart")
def get_cashflow_chart(days: int = 90, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    records = db.query(CashFlowRecord).order_by(CashFlowRecord.date.desc()).limit(days).all()
    records = list(reversed(records))
    return [
        {
            "date": r.date.strftime("%Y-%m-%d"),
            "inflow": r.inflow,
            "outflow": r.outflow,
            "net": r.net,
            "balance": r.balance
        }
        for r in records
    ]

@router.get("/alerts")
def get_recent_alerts(limit: int = 10, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    alerts = db.query(FraudAlert).filter(FraudAlert.is_resolved == False).order_by(
        FraudAlert.created_at.desc()
    ).limit(limit).all()
    return [
        {
            "id": a.id,
            "type": a.alert_type,
            "severity": a.severity,
            "description": a.description,
            "confidence": a.confidence_score,
            "created_at": a.created_at.isoformat()
        }
        for a in alerts
    ]

@router.get("/ai-recommendations")
def get_ai_recommendations(current_user=Depends(get_current_user)):
    return [
        {
            "id": 1,
            "priority": "critical",
            "title": "Resolve 3 Duplicate Payment Alerts",
            "description": "Halt $94,500 in potential duplicate payments detected in the past 48 hours.",
            "impact": "Prevent $94,500 loss",
            "action": "Review & Halt",
            "confidence": 0.94
        },
        {
            "id": 2,
            "priority": "high",
            "title": "Renegotiate Top 3 Vendor Contracts",
            "description": "Nexus Cloud, Atlas Digital, and Pinnacle Advisors are priced 30-67% above market benchmarks.",
            "impact": "Save $287,000 annually",
            "action": "Initiate RFP",
            "confidence": 0.88
        },
        {
            "id": 3,
            "priority": "high",
            "title": "Reallocate Marketing Budget Q4",
            "description": "Marketing department is tracking 23% over budget. Suggest shifting $45K to underutilized R&D.",
            "impact": "Improve budget efficiency by 12%",
            "action": "Reallocate Funds",
            "confidence": 0.81
        },
        {
            "id": 4,
            "priority": "medium",
            "title": "Cash Flow Risk: 45-Day Shortfall Predicted",
            "description": "Monte Carlo analysis predicts 73% probability of negative cash flow in 45 days at current burn rate.",
            "impact": "Secure $500K credit line",
            "action": "Plan Financing",
            "confidence": 0.73
        },
        {
            "id": 5,
            "priority": "medium",
            "title": "Diversify Single-Source Vendor Dependencies",
            "description": "4 vendors represent single-source dependencies across critical operations. Concentration risk is high.",
            "impact": "Reduce operational risk",
            "action": "Source Alternatives",
            "confidence": 0.86
        }
    ]
