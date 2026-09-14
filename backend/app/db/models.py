from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    company = Column(String, default="Aureon Corp")
    role = Column(String, default="CFO")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class TransactionStatus(str, enum.Enum):
    normal = "normal"
    flagged = "flagged"
    fraud = "fraud"
    review = "review"

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String)
    category = Column(String)
    department = Column(String)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.normal)
    fraud_score = Column(Float, default=0.0)
    anomaly_score = Column(Float, default=0.0)
    is_duplicate = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    vendor = relationship("Vendor", back_populates="transactions")

class InvoiceStatus(str, enum.Enum):
    pending = "pending"
    validated = "validated"
    rejected = "rejected"
    duplicate = "duplicate"

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    amount = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.pending)
    validation_score = Column(Float, default=0.0)
    ocr_confidence = Column(Float, default=0.0)
    duplicate_of = Column(String, nullable=True)
    line_items = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    vendor = relationship("Vendor", back_populates="invoices")

class VendorRiskTier(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String)
    country = Column(String, default="United States")
    risk_tier = Column(Enum(VendorRiskTier), default=VendorRiskTier.low)
    risk_score = Column(Float, default=0.0)
    payment_reliability = Column(Float, default=1.0)
    total_spend = Column(Float, default=0.0)
    invoice_count = Column(Integer, default=0)
    anomaly_flags = Column(Integer, default=0)
    is_single_source = Column(Boolean, default=False)
    contract_value = Column(Float, default=0.0)
    onboarded_at = Column(DateTime, default=datetime.utcnow)
    transactions = relationship("Transaction", back_populates="vendor")
    invoices = relationship("Invoice", back_populates="vendor")

class Budget(Base):
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True, index=True)
    department = Column(String, nullable=False)
    category = Column(String, nullable=False)
    allocated = Column(Float, nullable=False)
    spent = Column(Float, default=0.0)
    period = Column(String, default="2024-Q1")
    variance = Column(Float, default=0.0)
    efficiency_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class FraudAlert(Base):
    __tablename__ = "fraud_alerts"
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    transaction_id = Column(String, nullable=True)
    description = Column(Text)
    evidence = Column(Text)
    confidence_score = Column(Float, default=0.0)
    risk_explanation = Column(Text)
    recommended_actions = Column(Text)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class CashFlowRecord(Base):
    __tablename__ = "cash_flow_records"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    inflow = Column(Float, default=0.0)
    outflow = Column(Float, default=0.0)
    net = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)
    period_type = Column(String, default="daily")
    created_at = Column(DateTime, default=datetime.utcnow)
