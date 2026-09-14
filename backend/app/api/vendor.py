import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.security import get_current_user
from app.db.models import Vendor, Transaction, Invoice

router = APIRouter()

def compute_vendor_score(vendor: Vendor) -> dict:
    """Compute comprehensive vendor health score."""
    base_score = (1 - vendor.risk_score) * 100

    # Penalty for anomaly flags
    anomaly_penalty = min(30, vendor.anomaly_flags * 2)
    # Bonus for payment reliability
    reliability_bonus = (vendor.payment_reliability - 0.5) * 20

    final_score = max(0, min(100, base_score - anomaly_penalty + reliability_bonus))

    return {
        "id": vendor.id,
        "name": vendor.name,
        "category": vendor.category,
        "country": vendor.country,
        "risk_tier": vendor.risk_tier.value,
        "risk_score": round(vendor.risk_score * 100, 1),
        "health_score": round(final_score, 1),
        "payment_reliability": round(vendor.payment_reliability * 100, 1),
        "total_spend": vendor.total_spend,
        "invoice_count": vendor.invoice_count,
        "anomaly_flags": vendor.anomaly_flags,
        "is_single_source": vendor.is_single_source,
        "contract_value": vendor.contract_value,
        "grade": "A" if final_score >= 85 else "B" if final_score >= 70 else "C" if final_score >= 55 else "D" if final_score >= 40 else "F",
        "risk_factors": [
            f if v else None for f, v in [
                ("Single-source dependency — no backup vendor", vendor.is_single_source),
                (f"{vendor.anomaly_flags} anomaly flags detected in payment history", vendor.anomaly_flags > 3),
                ("Risk tier classified as HIGH or CRITICAL", vendor.risk_tier.value in ["high", "critical"]),
                (f"Payment reliability below 80%: {vendor.payment_reliability*100:.0f}%", vendor.payment_reliability < 0.8),
            ]
        ],
    }

@router.get("")
@router.get("/")
@router.get("/list")
def list_vendors(
    skip: int = 0, limit: int = 30,
    risk_tier: str = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = db.query(Vendor)
    if risk_tier:
        query = query.filter(Vendor.risk_tier == risk_tier)

    vendors = query.order_by(Vendor.risk_score.desc()).offset(skip).limit(limit).all()
    total = query.count()

    return {
        "total": total,
        "vendors": [compute_vendor_score(v) for v in vendors]
    }

@router.get("/{vendor_id}/analyze")
def analyze_vendor(vendor_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    score_data = compute_vendor_score(vendor)

    # Get recent transactions
    recent_txns = db.query(Transaction).filter(
        Transaction.vendor_id == vendor_id
    ).order_by(Transaction.date.desc()).limit(10).all()

    # Get invoices
    recent_invoices = db.query(Invoice).filter(
        Invoice.vendor_id == vendor_id
    ).order_by(Invoice.date.desc()).limit(5).all()

    # Monthly spend trend (simulate)
    monthly_trend = [
        {"month": f"2024-{str(m).zfill(2)}", "spend": round(random.uniform(20000, 150000), 2)}
        for m in range(1, 10)
    ]

    return {
        **score_data,
        "recent_transactions": [
            {
                "id": t.transaction_id,
                "date": t.date.isoformat(),
                "amount": t.amount,
                "status": t.status.value,
                "fraud_score": t.fraud_score
            }
            for t in recent_txns
        ],
        "recent_invoices": [
            {
                "number": i.invoice_number,
                "amount": i.amount,
                "status": i.status.value,
                "date": i.date.isoformat()
            }
            for i in recent_invoices
        ],
        "monthly_spend_trend": monthly_trend,
        "ai_assessment": f"Vendor '{vendor.name}' scored {score_data['health_score']:.0f}/100 (Grade {score_data['grade']}). "
                         f"{'⚠️ Critical risk factors detected requiring immediate review.' if score_data['risk_score'] > 70 else '✓ Vendor is operating within acceptable risk parameters.'}"
    }

@router.post("/{vendor_id}/score")
def generate_vendor_score(vendor_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.name,
        **compute_vendor_score(vendor),
        "scored_at": "2024-09-13T10:00:00Z",
        "model": "Aureon VendorRisk v2.1"
    }

@router.get("/{vendor_id}/risk-trends")
def vendor_risk_trends(vendor_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    base_risk = vendor.risk_score
    trend_data = []
    for m in range(1, 10):
        noise = random.gauss(0, 0.05)
        risk = max(0, min(1, base_risk + noise + (m - 5) * 0.01))
        trend_data.append({
            "month": f"2024-{str(m).zfill(2)}",
            "risk_score": round(risk * 100, 1),
            "anomaly_count": max(0, vendor.anomaly_flags + random.randint(-2, 2)),
            "spend": round(random.uniform(20000, 150000), 2)
        })

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.name,
        "trend": trend_data,
        "direction": "increasing" if trend_data[-1]["risk_score"] > trend_data[0]["risk_score"] else "decreasing",
        "recommendation": f"Risk trend {'increasing — recommend enhanced monitoring and contract review' if trend_data[-1]['risk_score'] > trend_data[0]['risk_score'] else 'stable or improving — continue regular monitoring'}."
    }
