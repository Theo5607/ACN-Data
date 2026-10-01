import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_evse_telemetry(
    n_sessions=60,
    interval_seconds=60,
    seed=42
):
    """
    Génère un flux de données de télémétrie conforme aux trames OCPP MeterValues
    avec injection d'anomalies réalistes.
    """
    np.random.seed(seed)
    records = []
    current_time = datetime(2026, 6, 1, 8, 0, 0)
    total_energy_kwh = 12500.0  # Index compteur initial

    for session_id in range(1, n_sessions + 1):
        # Durée de charge : 20 à 75 minutes
        session_duration_min = np.random.randint(20, 76)
        n_points = int((session_duration_min * 60) / interval_seconds)

        # Scénario de fonctionnement : 80% nominal, 20% anomalie
        scenario = np.random.choice(
            ["nominal", "thermal_runaway", "voltage_sag", "contact_wear"],
            p=[0.80, 0.10, 0.05, 0.05]
        )

        # Consignes nominales pour une borne AC triphasée 22 kW
        # Courant nominal : ~32 A par phase, tension ~230 V
        current_setpoint = 32.0 
        base_temp_ambient = 22.0 + np.random.normal(0, 3)
        temp_connector = base_temp_ambient

        for step in range(n_points):
            timestamp = current_time + timedelta(seconds=step * interval_seconds)

            # 1. Variables physiques de base
            voltage = 230.0 + np.random.normal(0, 1.5)
            current = current_setpoint + np.random.normal(0, 0.4)
            power_factor = 0.98 + np.random.normal(0, 0.01)

            # 2. Simulation de l'échauffement thermique (effet Joule standard)
            # T_eq = T_amb + R_th * I^2
            delta_t_nominal = (current / 32.0)**2 * 18.0
            target_temp = base_temp_ambient + delta_t_nominal
            temp_connector += (target_temp - temp_connector) * 0.05  # constante de temps thermique

            # 3. Injection d'anomalies selon le scénario
            status_code = "Charging"
            failure_label = 0  # 0 = Sain, 1 = Défaillance imminente/critique

            if scenario == "thermal_runaway" and step > (n_points * 0.4):
                # Dégradation de la résistance de contact -> emballement thermique
                temp_connector += (step * 0.45)
                failure_label = 1
                if temp_connector > 75.0:
                    status_code = "Faulted"
                    current = 0.0  # Coupure d'urgence par le contrôleur

            elif scenario == "voltage_sag" and (n_points * 0.3 < step < n_points * 0.6):
                # Chute brutale de tension réseau
                voltage -= 35.0
                failure_label = 1

            elif scenario == "contact_wear" and step > (n_points * 0.5):
                # Micro-coupures / instabilité du relais de contacteur
                current *= np.random.choice([1.0, 0.2, 0.0], p=[0.7, 0.2, 0.1])
                failure_label = 1

            # Calcul puissance active et intégration énergie
            power_kw = (3 * voltage * current * power_factor) / 1000.0
            total_energy_kwh += (power_kw * (interval_seconds / 3600.0))

            records.append({
                "timestamp": timestamp,
                "session_id": session_id,
                "voltage_v": round(voltage, 2),
                "current_a": round(current, 2),
                "power_kw": round(power_kw, 2),
                "power_factor": round(power_factor, 3),
                "energy_total_kwh": round(total_energy_kwh, 4),
                "temp_ambient_c": round(base_temp_ambient, 1),
                "temp_connector_c": round(temp_connector, 1),
                "ocpp_status": status_code,
                "anomaly_type": scenario if failure_label == 1 else "none",
                "failure_label": failure_label
            })

        # Avancement du temps entre sessions (temps d'inactivité de 10 à 60 min)
        idle_minutes = np.random.randint(10, 61)
        current_time = timestamp + timedelta(minutes=idle_minutes)

    return pd.DataFrame(records)

# Exécution et export
if __name__ == "__main__":
    df = generate_evse_telemetry(n_sessions=50, interval_seconds=30)
    df.to_csv("evse_predictive_maintenance_dataset.csv", index=False)
    
    print(f"Dataset généré : {df.shape[0]} lignes.")
    print("Distribution des statuts :")
    print(df["anomaly_type"].value_counts())
    print("\nAperçu des 5 premières lignes :")
    print(df.head())