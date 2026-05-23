#!/usr/bin/env python3
"""
SG90 Servo-Steuerung für Raspberry Pi 5 (mit pigpio)
Dreht den Servo kurz nach oben (Ausgabe-Mechanismus) und sofort zurück.

Benötigte Pakete:
  pip install flask flask-cors
  sudo apt install pigpio python3-pigpio
  sudo systemctl start pigpiod

Verdrahtung SG90:
  Braun/Schwarz  → GND (z.B. Pin 6)
  Rot            → 5V  (Pin 2 oder 4)
  Orange/Gelb    → GPIO 18 (Pin 12) ← PWM-fähiger Pin

Starten:
  python3 servo_server.py
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import threading
import time
import atexit
import os

app = Flask(__name__, static_folder=".")
CORS(app)

# ── Konfiguration ──────────────────────────────────────────────────────────────
SERVO_PIN       = 18      # BCM-GPIO-Pin
PWM_FREQUENCY   = 50      # Hz (Standard für Servos)

# SG90 Pulsdauern in Microsekunden (µs) bei 50 Hz:
#   1000 µs  = 0°   (ganz unten)
#   1500 µs  = 90°  (Mittelposition)
#   2000 µs  = 180° (ganz oben)
PULSE_NEUTRAL   = 1500    # 90° – Ruheposition
PULSE_UP        = 2000    # 180° – Ausgabe-Position
HOLD_SECONDS    = 0.4     # wie lange oben halten
RELAX_DELAY     = 0.3     # nach Rückkehr: kurz warten

servo_busy = False
servo_lock = threading.Lock()
pi = None  # pigpio-Objekt

# ── pigpio initialisieren ──────────────────────────────────────────────────────
try:
    import pigpio
    pi = pigpio.pi()
    if not pi.connected:
        raise RuntimeError("pigpiod daemon nicht erreichbar")
    pi.set_PWM_frequency(SERVO_PIN, PWM_FREQUENCY)
    pi.set_servo_pulsewidth(SERVO_PIN, PULSE_NEUTRAL)
    time.sleep(0.2)
    pi.set_servo_pulsewidth(SERVO_PIN, 0)  # Signal abschalten
    GPIO_AVAILABLE = True
    print(f"✅  pigpio initialisiert – Servo an GPIO {SERVO_PIN}")
except Exception as e:
    GPIO_AVAILABLE = False
    pi = None
    print(f"⚠️  pigpio nicht verfügbar – Simulationsmodus")
    print(f"    Fehler: {e}")
    print(f"    Lösung: sudo systemctl start pigpiod")


def move_servo():
    """Dreht den SG90 kurz nach oben und sofort zurück."""
    global servo_busy
    with servo_lock:
        servo_busy = True
    try:
        if GPIO_AVAILABLE and pi:
            pi.set_servo_pulsewidth(SERVO_PIN, PULSE_UP)      # → hoch (180°)
            time.sleep(HOLD_SECONDS)
            pi.set_servo_pulsewidth(SERVO_PIN, PULSE_NEUTRAL) # → neutral (90°)
            time.sleep(RELAX_DELAY)
            pi.set_servo_pulsewidth(SERVO_PIN, 0)             # Signal aus
        else:
            # Simulation
            print(f"[SIM] Servo → {PULSE_UP}µs (hoch)")
            time.sleep(HOLD_SECONDS)
            print(f"[SIM] Servo → {PULSE_NEUTRAL}µs (neutral)")
            time.sleep(RELAX_DELAY)
        print("✅  Servo-Bewegung abgeschlossen")
    finally:
        with servo_lock:
            servo_busy = False


def trigger_async():
    t = threading.Thread(target=move_servo, daemon=True)
    t.start()



# ── API ────────────────────────────────────────────────────────────────────────
@app.route("/dispense", methods=["POST"])
def dispense():
    with servo_lock:
        if servo_busy:
            return jsonify({"success": False, "error": "Servo ist noch aktiv."}), 409

    trigger_async()
    return jsonify({
        "success": True,
        "message": "Cola wird ausgegeben! 🥤",
        "pulse_up": PULSE_UP,
        "hold_seconds": HOLD_SECONDS,
    })


@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "gpio_available": GPIO_AVAILABLE,
        "servo_busy": servo_busy,
        "servo_pin": SERVO_PIN,
    })


@app.route("/", methods=["GET"])
@app.route("/<path:filename>", methods=["GET"])
def serve_static(filename="index.html"):
    return send_from_directory(".", filename)


# ── Cleanup ────────────────────────────────────────────────────────────────────
def cleanup():
    if GPIO_AVAILABLE and pi:
        pi.set_servo_pulsewidth(SERVO_PIN, 0)
        pi.stop()
        print("🔌  pigpio bereinigt")

atexit.register(cleanup)

if __name__ == "__main__":
    print("🚀  Servo-Server läuft auf http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
