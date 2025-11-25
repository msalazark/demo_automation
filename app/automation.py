from datetime import datetime, timedelta
from .models import Lead, AutomationStep, AdsEvent


def classify_temperature(lead: Lead) -> str:
    # Regla de juguete: según source
    if lead.source == "ads":
        return "caliente"
    if lead.source == "organic":
        return "tibio"
    return "frio"



def build_onboarding_flow(lead: Lead):
    # Flujo mínimo: 3 pasos
    now = datetime.utcnow()

    steps = [
        AutomationStep(
            lead_id=lead.id,
            flow_name="onboarding_lead_web",
            step_order=1,
            action_type="email_bienvenida",
            scheduled_at=now,
        ),
        AutomationStep(
            lead_id=lead.id,
            flow_name="onboarding_lead_web",
            step_order=2,
            action_type="email_contenido_modelo",
            scheduled_at=now + timedelta(days=2),
        ),
        AutomationStep(
            lead_id=lead.id,
            flow_name="onboarding_lead_web",
            step_order=3,
            action_type="notificacion_vendedor",
            scheduled_at=now + timedelta(days=3),
        ),
    ]

    return steps

def register_capi_event(db, lead: Lead, provider: str = "meta"):
    """
    Simula un envío CAPI: en lugar de llamar la API real,
    registramos el evento en la tabla ads_events.
    """
    ads_event = AdsEvent(
        lead_id=lead.id,
        provider=provider,
        event_name="lead"  # en real sería 'Lead' o similar
    )
    db.add(ads_event)
    db.commit()
    db.refresh(ads_event)
    return ads_event