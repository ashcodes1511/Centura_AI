import random
import json
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session
from app.db.models import (
    User, Transaction, Invoice, Vendor, Budget, FraudAlert, CashFlowRecord,
    TransactionStatus, InvoiceStatus, VendorRiskTier
)
from app.core.security import get_password_hash

fake = Faker()
random.seed(42)

CATEGORIES = ["Software", "Marketing", "Operations", "HR", "Legal", "Finance", "IT Infrastructure",
              "R&D", "Sales", "Customer Support", "Facilities", "Travel", "Training"]

DEPARTMENTS = ["Engineering", "Marketing", "Sales", "Finance", "HR", "Operations", "Legal", "Executive"]

VENDOR_NAMES = [
    "Nexus Cloud Solutions", "Apex Analytics Corp", "Vertex Systems Inc", "Meridian Software Ltd",
    "Catalyst Digital", "Summit Technologies", "Prism Data Services", "Orbit Consulting Group",
    "Fusion Payments", "Eclipse Software", "Zenith Logistics", "Momentum IT", "Pinnacle Advisors",
    "CoreSight Analytics", "TrueScale Infrastructure", "Blueprint Technologies", "Horizon Ventures",
    "Vector Intelligence", "Aurora Systems", "Skyline Networks", "Pacific Consulting", "Atlas Digital",
    "Keystone Software", "Sterling Solutions", "Valor Analytics", "Crest Financial Services",
    "Nova Payments Ltd", "Clarity Business Systems", "Spectrum Cloud", "Fortis Technologies"
]

VENDOR_CATEGORIES = ["Cloud Services", "Analytics", "Consulting", "Software License", "Infrastructure",
                      "Logistics", "Marketing Agency", "Legal Services", "HR Services", "Finance Services"]


def seed_data(db: Session):
    # Check if data already seeded
    if db.query(User).count() > 0:
        return

    print("[+] Seeding Aureon AI database...")

    # --- Create demo user ---
    demo_user = User(
        name="Alexandra Chen",
        email="cfo@aureon.ai",
        hashed_password=get_password_hash("Aureon2024!"),
        company="TechVentures Global Inc.",
        role="Chief Financial Officer"
    )
    db.add(demo_user)
    db.commit()

    # --- Create Vendors ---
    vendors = []
    for i, name in enumerate(VENDOR_NAMES):
        risk_score = random.uniform(0.05, 0.95)
        if risk_score < 0.3:
            tier = VendorRiskTier.low
        elif risk_score < 0.6:
            tier = VendorRiskTier.medium
        elif risk_score < 0.8:
            tier = VendorRiskTier.high
        else:
            tier = VendorRiskTier.critical

        vendor = Vendor(
            name=name,
            category=random.choice(VENDOR_CATEGORIES),
            country=random.choice(["United States", "United Kingdom", "Germany", "Canada", "India", "Singapore"]),
            risk_tier=tier,
            risk_score=round(risk_score, 3),
            payment_reliability=round(random.uniform(0.6, 1.0), 3),
            total_spend=round(random.uniform(50000, 2500000), 2),
            invoice_count=random.randint(5, 120),
            anomaly_flags=random.randint(0, 15) if risk_score > 0.5 else 0,
            is_single_source=random.random() < 0.15,
            contract_value=round(random.uniform(100000, 5000000), 2),
            onboarded_at=fake.date_time_between(start_date="-3y", end_date="-1y")
        )
        vendors.append(vendor)

    db.add_all(vendors)
    db.commit()
    for v in vendors:
        db.refresh(v)

    print(f"  ✓ Created {len(vendors)} vendors")

    # --- Create Transactions (10,000+) ---
    transactions = []
    start_date = datetime.now() - timedelta(days=730)  # 2 years back

    for i in range(10500):
        date = start_date + timedelta(days=random.uniform(0, 730))
        amount = random.choice([
            random.uniform(100, 5000),       # Normal small
            random.uniform(5000, 50000),     # Medium
            random.uniform(50000, 500000),   # Large
        ])
        # Inject fraud transactions ~3%
        is_fraud = random.random() < 0.03
        is_dup = random.random() < 0.01
        fraud_score = round(random.uniform(0.7, 0.99), 3) if is_fraud else round(random.uniform(0.0, 0.25), 3)
        anomaly_score = round(random.uniform(0.6, 0.99), 3) if is_fraud else round(random.uniform(0.0, 0.3), 3)

        if is_fraud:
            status = TransactionStatus.fraud
        elif is_dup:
            status = TransactionStatus.flagged
        elif fraud_score > 0.5:
            status = TransactionStatus.review
        else:
            status = TransactionStatus.normal

        t = Transaction(
            transaction_id=f"TXN-{str(i+1).zfill(6)}",
            date=date,
            amount=round(amount, 2),
            description=fake.bs().title(),
            category=random.choice(CATEGORIES),
            department=random.choice(DEPARTMENTS),
            vendor_id=random.choice(vendors).id,
            status=status,
            fraud_score=fraud_score,
            anomaly_score=anomaly_score,
            is_duplicate=is_dup,
        )
        transactions.append(t)

    db.add_all(transactions)
    db.commit()
    print(f"  ✓ Created {len(transactions)} transactions")

    # --- Create Invoices (500+) ---
    invoices = []
    invoice_numbers = set()
    for i in range(520):
        while True:
            inv_num = f"INV-{fake.numerify('####-####')}"
            if inv_num not in invoice_numbers:
                invoice_numbers.add(inv_num)
                break

        vendor = random.choice(vendors)
        inv_date = fake.date_time_between(start_date="-18m", end_date="now")
        is_dup = random.random() < 0.03
        status_val = InvoiceStatus.duplicate if is_dup else random.choice(
            [InvoiceStatus.pending, InvoiceStatus.validated, InvoiceStatus.validated, InvoiceStatus.validated, InvoiceStatus.rejected]
        )
        line_items = json.dumps([
            {"description": fake.catch_phrase(), "quantity": random.randint(1, 10), "unit_price": round(random.uniform(100, 5000), 2)}
            for _ in range(random.randint(1, 5))
        ])
        invoice = Invoice(
            invoice_number=inv_num,
            vendor_id=vendor.id,
            amount=round(random.uniform(500, 250000), 2),
            date=inv_date,
            due_date=inv_date + timedelta(days=random.choice([30, 45, 60, 90])),
            description=fake.sentence(),
            status=status_val,
            validation_score=round(random.uniform(0.6, 0.99), 3),
            ocr_confidence=round(random.uniform(0.75, 0.99), 3),
            duplicate_of=f"INV-{fake.numerify('####-####')}" if is_dup else None,
            line_items=line_items,
        )
        invoices.append(invoice)

    db.add_all(invoices)
    db.commit()
    print(f"  ✓ Created {len(invoices)} invoices")

    # --- Create Budgets ---
    periods = ["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"]
    budgets = []
    for period in periods:
        for dept in DEPARTMENTS:
            for cat in random.sample(CATEGORIES, 4):
                allocated = round(random.uniform(50000, 800000), 2)
                spent_pct = random.uniform(0.5, 1.3)
                spent = round(allocated * spent_pct, 2)
                variance = round(spent - allocated, 2)
                efficiency = max(0.0, min(1.0, round(1 - abs(variance) / allocated, 3)))
                b = Budget(
                    department=dept,
                    category=cat,
                    allocated=allocated,
                    spent=spent,
                    period=period,
                    variance=variance,
                    efficiency_score=efficiency,
                )
                budgets.append(b)

    db.add_all(budgets)
    db.commit()
    print(f"  ✓ Created {len(budgets)} budget entries")

    # --- Create Cash Flow Records (2 years daily) ---
    cf_records = []
    running_balance = 2_500_000.0
    for day_offset in range(730):
        date = start_date + timedelta(days=day_offset)
        inflow = round(random.uniform(50000, 350000), 2)
        outflow = round(random.uniform(40000, 320000), 2)
        net = inflow - outflow
        running_balance += net
        cf_records.append(CashFlowRecord(
            date=date,
            inflow=inflow,
            outflow=outflow,
            net=round(net, 2),
            balance=round(running_balance, 2),
            period_type="daily"
        ))

    db.add_all(cf_records)
    db.commit()
    print(f"  ✓ Created {len(cf_records)} cash flow records")

    # --- Create Fraud Alerts ---
    alert_types = [
        ("Duplicate Payment", "high", "Transaction TXN-004521 appears to be a duplicate of TXN-002341",
         "Same vendor, same amount ($47,250), same date range", 0.94,
         "Pattern: 99.3% amount match, same vendor ID, 2-day window overlap. Heuristic: duplicate_detector v2.1",
         "Immediately halt payment. Request confirmation from vendor. Flag for CFO review."),
        ("Unusual Vendor Activity", "critical", "Vendor 'Nexus Cloud Solutions' showing 340% spend increase",
         "Spend jumped from $12K/mo to $53K/mo in 30 days", 0.91,
         "Statistical outlier: 4.2σ above 90-day rolling average. Isolation Forest score: 0.87",
         "Request vendor invoice justification. Escalate to procurement. Freeze additional POs."),
        ("Round-Trip Transaction", "high", "Circular payment pattern detected between 3 entities",
         "TXN-007231 → TXN-007889 → TXN-008001 forming closed loop", 0.88,
         "Graph analysis: Funds return to originating account within 5 business days. Known fraud signature.",
         "Suspend all linked transactions. Initiate internal audit. Notify compliance team."),
        ("After-Hours Transaction", "medium", "Large transaction processed at 2:47 AM outside business hours",
         "TXN-009341: $128,500 processed on Sunday 02:47 UTC", 0.76,
         "Time-based anomaly: 98.2% of transactions occur 08:00-18:00 local time. Velocity: unusually high.",
         "Verify authorization chain. Check employee access logs. Consider setting time-based controls."),
        ("Vendor Price Inflation", "medium", "Unit price 67% above market rate for IT services",
         "Invoice INV-2341-8821: $4,250/hr vs market benchmark $2,545/hr", 0.82,
         "Market benchmark comparison: internal pricing database. Deviation: 1.67x standard rate.",
         "Renegotiate contract. Issue RFP to 3 comparable vendors. Flag for legal review."),
    ]

    fraud_alerts = []
    for alert_type, severity, desc, evidence, confidence, explanation, actions in alert_types:
        fa = FraudAlert(
            alert_type=alert_type,
            severity=severity,
            transaction_id=f"TXN-{random.randint(1000, 9999):06d}",
            description=desc,
            evidence=evidence,
            confidence_score=confidence,
            risk_explanation=explanation,
            recommended_actions=actions,
            is_resolved=random.random() < 0.2,
            created_at=fake.date_time_between(start_date="-30d", end_date="now")
        )
        fraud_alerts.append(fa)

    db.add_all(fraud_alerts)
    db.commit()
    print(f"  ✓ Created {len(fraud_alerts)} fraud alerts")
    print("✅ Database seeding complete!")
