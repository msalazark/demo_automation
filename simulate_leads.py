# simulate_leads.py
import requests
import random
import time

NAMES = ["Juan", "María", "Carlos", "Lucía", "Miguel", "Ana"]
PRODUCTS = ["SUV_X", "SUV_Y", "Sedan_A", "Hatchback_B"]
SOURCES = ["ads", "organic", "referral"]

URL = "http://127.0.0.1:8000/webhook/lead"

def random_email(name):
    base = name.lower()
    dom = random.choice(["example.com", "mail.com", "demo.com"])
    return f"{base}{random.randint(1,999)}@{dom}"

while True:
    name = random.choice(NAMES)
    email = random_email(name)
    product = random.choice(PRODUCTS)
    source = random.choice(SOURCES)

    payload = {
        "name": name,
        "email": email,
        "product_interest": product,
        "source": source,
    }

    try:
        r = requests.post(URL, json=payload)
        print("Enviado lead:", payload, "→ status", r.status_code)
    except Exception as e:
        print("Error enviando lead:", e)

    time.sleep(random.randint(2, 5))  # cada 2–5 segundos
