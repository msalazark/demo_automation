from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime

from .database import SessionLocal, engine, Base
from .models import Lead, AutomationStep, AdsEvent
from .automation import classify_temperature, build_onboarding_flow, register_capi_event

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Automation Demo Local")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LeadIn(BaseModel):
    name: str
    email: str
    product_interest: str
    source: str  # ads, organic, referral, etc


@app.post("/webhook/lead")
def receive_lead(lead_in: LeadIn, db: Session = Depends(get_db)):
    # 1. Guardar el lead
    lead = Lead(
        name=lead_in.name,
        email=lead_in.email,
        product_interest=lead_in.product_interest,
        source=lead_in.source,
        created_at=datetime.utcnow(),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # 2. Clasificar temperatura
    lead.temperature = classify_temperature(lead)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # 3. Crear pasos del flujo de onboarding
    steps = build_onboarding_flow(lead)
    for step in steps:
        db.add(step)
    db.commit()

    # 4. Simular envío CAPI → registrar evento en ads_events
    ads_event = register_capi_event(db, lead, provider="meta")

    return {
        "status": "ok",
        "lead_id": lead.id,
        "temperature": lead.temperature,
        "flow_steps": len(steps),
        "capi_event_id": ads_event.id,
        "capi_provider": ads_event.provider,
    }


@app.get("/leads")
def list_leads(db: Session = Depends(get_db)):
    leads = db.query(Lead).all()
    return [
        {
            "id": l.id,
            "name": l.name,
            "email": l.email,
            "product_interest": l.product_interest,
            "source": l.source,
            "temperature": l.temperature,
            "created_at": l.created_at,
        }
        for l in leads
    ]


@app.get("/automation/steps")
def list_steps(db: Session = Depends(get_db)):
    steps = db.query(AutomationStep).all()
    return [
        {
            "id": s.id,
            "lead_id": s.lead_id,
            "flow_name": s.flow_name,
            "step_order": s.step_order,
            "action_type": s.action_type,
            "status": s.status,
            "scheduled_at": s.scheduled_at,
            "executed_at": s.executed_at,
        }
        for s in steps
    ]


@app.get("/ads/events")
def list_ads_events(db: Session = Depends(get_db)):
    events = db.query(AdsEvent).all()
    return [
        {
            "id": e.id,
            "lead_id": e.lead_id,
            "provider": e.provider,
            "event_name": e.event_name,
            "sent_at": e.sent_at,
        }
        for e in events
    ]


@app.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db)):
    # Total de leads
    total_leads = db.query(func.count(Lead.id)).scalar() or 0

    # Leads por fuente (source)
    raw_by_source = (
        db.query(Lead.source, func.count(Lead.id))
        .group_by(Lead.source)
        .all()
    )
    leads_by_source = [
        {"source": src if src is not None else "unknown", "count": cnt}
        for src, cnt in raw_by_source
    ]

    # Leads por temperatura
    raw_by_temp = (
        db.query(Lead.temperature, func.count(Lead.id))
        .group_by(Lead.temperature)
        .all()
    )
    leads_by_temperature = [
        {"temperature": temp if temp is not None else "unknown", "count": cnt}
        for temp, cnt in raw_by_temp
    ]

    # Total de eventos "CAPI"
    total_ads_events = db.query(func.count(AdsEvent.id)).scalar() or 0

    return {
        "total_leads": total_leads,
        "leads_by_source": leads_by_source,
        "leads_by_temperature": leads_by_temperature,
        "total_ads_events": total_ads_events,
    }


# ======================
# Demo HTML
# ======================
@app.get("/demo", response_class=HTMLResponse)
def demo_form():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8" />
        <title>Demo Automation Lead</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 30px auto;
            }
            label {
                display: block;
                margin-top: 10px;
                font-weight: bold;
            }
            input, select {
                width: 100%;
                padding: 6px;
                margin-top: 4px;
            }
            button {
                margin-top: 15px;
                padding: 10px 15px;
                cursor: pointer;
            }
            #result {
                margin-top: 20px;
                padding: 10px;
                border: 1px solid #ddd;
                background-color: #f9f9f9;
                white-space: pre-wrap;
                font-family: Consolas, monospace;
            }
        </style>
    </head>
    <body>
        <h1>Demo 2 · Envío de Lead</h1>
        <p>Este formulario envía un lead al endpoint <code>/webhook/lead</code> usando <code>fetch</code>.</p>

        <form id="leadForm">
            <label for="name">Nombre</label>
            <input type="text" id="name" name="name" value="Juan Perez" required />

            <label for="email">Email</label>
            <input type="email" id="email" name="email" value="juan@example.com" required />

            <label for="product_interest">Producto de interés</label>
            <input type="text" id="product_interest" name="product_interest" value="SUV_X" required />

            <label for="source">Fuente</label>
            <select id="source" name="source">
                <option value="ads">Ads</option>
                <option value="organic">Organic</option>
                <option value="referral">Referral</option>
            </select>

            <button type="submit">Enviar Lead</button>
        </form>

        <div id="result"></div>

        <script>
            const form = document.getElementById("leadForm");
            const resultDiv = document.getElementById("result");

            form.addEventListener("submit", async (e) => {
                e.preventDefault();

                const payload = {
                    name: document.getElementById("name").value,
                    email: document.getElementById("email").value,
                    product_interest: document.getElementById("product_interest").value,
                    source: document.getElementById("source").value
                };

                resultDiv.textContent = "Enviando...";

                try {
                    const response = await fetch("/webhook/lead", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify(payload)
                    });

                    const data = await response.json();
                    resultDiv.textContent = JSON.stringify(data, null, 2);
                } catch (err) {
                    resultDiv.textContent = "Error: " + err;
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8" />
        <title>Dashboard Automation</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 30px auto;
            }
            h1, h2 {
                margin-bottom: 5px;
            }
            .card {
                border: 1px solid #ddd;
                padding: 15px;
                margin-top: 15px;
                border-radius: 4px;
                background-color: #f9f9f9;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 6px;
                text-align: left;
            }
            th {
                background-color: #eee;
            }
            #lastUpdated {
                font-size: 0.9em;
                color: #555;
            }
        </style>
    </head>
    <body>
        <h1>Dashboard · Automation Demo</h1>
        <p id="lastUpdated">Última actualización: -</p>

        <div class="card">
            <h2>Resumen</h2>
            <p><strong>Total leads:</strong> <span id="totalLeads">0</span></p>
            <p><strong>Total eventos Ads (CAPI):</strong> <span id="totalAds">0</span></p>
        </div>

        <div class="card">
            <h2>Leads por fuente</h2>
            <table>
                <thead>
                    <tr>
                        <th>Fuente</th>
                        <th>Cantidad</th>
                    </tr>
                </thead>
                <tbody id="tableSource">
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>Leads por temperatura</h2>
            <table>
                <thead>
                    <tr>
                        <th>Temperatura</th>
                        <th>Cantidad</th>
                    </tr>
                </thead>
                <tbody id="tableTemp">
                </tbody>
            </table>
        </div>

        <script>
            async function fetchSummary() {
                try {
                    const response = await fetch("/analytics/summary");
                    const data = await response.json();

                    document.getElementById("totalLeads").textContent = data.total_leads;
                    document.getElementById("totalAds").textContent = data.total_ads_events;

                    // Leads por fuente
                    const tbodySource = document.getElementById("tableSource");
                    tbodySource.innerHTML = "";
                    (data.leads_by_source || []).forEach(item => {
                        const tr = document.createElement("tr");
                        const tdSource = document.createElement("td");
                        const tdCount = document.createElement("td");
                        tdSource.textContent = item.source;
                        tdCount.textContent = item.count;
                        tr.appendChild(tdSource);
                        tr.appendChild(tdCount);
                        tbodySource.appendChild(tr);
                    });

                    // Leads por temperatura
                    const tbodyTemp = document.getElementById("tableTemp");
                    tbodyTemp.innerHTML = "";
                    (data.leads_by_temperature || []).forEach(item => {
                        const tr = document.createElement("tr");
                        const tdTemp = document.createElement("td");
                        const tdCount = document.createElement("td");
                        tdTemp.textContent = item.temperature;
                        tdCount.textContent = item.count;
                        tr.appendChild(tdTemp);
                        tr.appendChild(tdCount);
                        tbodyTemp.appendChild(tr);
                    });

                    const now = new Date();
                    document.getElementById("lastUpdated").textContent =
                        "Última actualización: " + now.toLocaleTimeString();
                } catch (err) {
                    console.error("Error obteniendo summary:", err);
                }
            }

            // Primera carga
            fetchSummary();
            // Refrescar cada 3 segundos
            setInterval(fetchSummary, 3000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

