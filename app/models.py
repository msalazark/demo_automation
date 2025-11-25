from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, index=True)
    product_interest = Column(String, index=True)
    source = Column(String, index=True)
    temperature = Column(String, index=True)  # frio, tibio, caliente
    created_at = Column(DateTime, default=datetime.utcnow)

    steps = relationship("AutomationStep", back_populates="lead")


class AutomationStep(Base):
    __tablename__ = "automation_steps"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    flow_name = Column(String, index=True)
    step_order = Column(Integer)
    action_type = Column(String)
    status = Column(String, default="pending")  # pending, executed
    scheduled_at = Column(DateTime)
    executed_at = Column(DateTime, nullable=True)

    lead = relationship("Lead", back_populates="steps")


class AdsEvent(Base):
    __tablename__ = "ads_events"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    provider = Column(String, index=True)      # meta, google, etc.
    event_name = Column(String, index=True)    # lead, purchase, etc.
    sent_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead")