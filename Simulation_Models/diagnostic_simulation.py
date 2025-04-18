"""
Maritime Vessel Safety Systems - Diagnostics Simulation
Provides a diagnostic tool to simulate built-in self-test of all safety subsystems.
This can be used in maintenance routines to verify that each subsystem is functional.
"""
import logging
import datetime

class DiagnosticsSimulator:
    def __init__(self, fire_system, esd_system, bilge_system):
        """
        Initialize the diagnostics simulator with subsystem instances.
        """
        self.fire_system = fire_system
        self.esd_system = esd_system
        self.bilge_system = bilge_system
        self.last_run = None  # timestamp of last diagnostics run
        logging.info("DiagnosticsSimulator initialized for fire, ESD, and bilge systems")

    def run_all_diagnostics(self):
        """
        Run diagnostic self-tests on all subsystems.
        Returns a dict with boolean pass/fail for each subsystem: {"fire": bool, "esd": bool, "bilge": bool}
        """
        results = {"fire": False, "esd": False, "bilge": False}
        # 1. Fire Detection System diagnostic: simulate a test alarm condition
        try:
            # Reset any existing alarms
            if hasattr(self.fire_system, "alarms"):
                self.fire_system.alarms = {"visual": False, "audible": False}
            # Trigger a test condition (e.g., high temperature and smoke on one detector)
            if hasattr(self.fire_system, "set_sensor_value") and hasattr(self.fire_system, "run_simulation"):
                self.fire_system.set_sensor_value("sensor_1", "temp", 60.0)
                self.fire_system.set_sensor_value("sensor_1", "smoke", 0.5)
                self.fire_system.run_simulation(duration=1.0)
                status = self.fire_system.get_alarm_status() if hasattr(self.fire_system, "get_alarm_status") else {}
                # Pass if both alarms triggered
                if status.get("visual") and status.get("audible"):
                    results["fire"] = True
                    logging.info("Fire system diagnostic PASS")
                else:
                    logging.error("Fire system diagnostic FAIL (alarms not triggered as expected)")
        except Exception as e:
            logging.error(f"Fire system diagnostic exception: {e}")

        # 2. Emergency Shutdown System diagnostic: simulate an emergency shutdown activation
        try:
            # Reset ESD state (re-initialize or manually reset fields if possible)
            if hasattr(self.esd_system, "fuel_valves"):
                # Re-open valves and reset alarm signal for test
                self.esd_system.fuel_valves.update({"main": "open", "auxiliary": "open"})
            if hasattr(self.esd_system, "alarm_interface"):
                self.esd_system.alarm_interface["signal_sent"] = False
            # Activate shutdown from a control point (e.g., bridge)
            if hasattr(self.esd_system, "activate_shutdown"):
                shutdown_time = self.esd_system.activate_shutdown("bridge")
                valves_closed = True
                if hasattr(self.esd_system, "get_valve_status"):
                    valve_status = self.esd_system.get_valve_status()
                    valves_closed = all(v == "closed" for v in valve_status.values())
                signal_sent = False
                if hasattr(self.esd_system, "alarm_interface"):
                    signal_sent = self.esd_system.alarm_interface.get("signal_sent", False)
                # Pass if shutdown executed (valves closed) and alarm signal sent
                if shutdown_time is not None and valves_closed and signal_sent:
                    results["esd"] = True
                    logging.info("ESD system diagnostic PASS")
                else:
                    logging.error("ESD system diagnostic FAIL (shutdown or alarm signal not as expected)")
        except Exception as e:
            logging.error(f"ESD system diagnostic exception: {e}")

        # 3. Bilge Alarm System diagnostic: simulate a high water alarm condition
        try:
            # Reset bilge alarms
            if hasattr(self.bilge_system, "alarms"):
                self.bilge_system.alarms = {"visual": False, "audible": False}
            # Identify a compartment and raise water level to trigger alarm
            comp_id = None
            if hasattr(self.bilge_system, "compartments"):
                # get one compartment ID
                comp_id = next(iter(self.bilge_system.compartments)) if self.bilge_system.compartments else None
            if comp_id and hasattr(self.bilge_system, "set_water_level") and hasattr(self.bilge_system, "run_simulation"):
                threshold = self.bilge_system.compartments[comp_id].get("alarm_threshold", 150.0)
                self.bilge_system.set_water_level(comp_id, threshold + 1.0)  # just above threshold
                self.bilge_system.run_simulation(duration=1.0)
                status = self.bilge_system.get_alarm_status() if hasattr(self.bilge_system, "get_alarm_status") else {}
                # Pass if both visual and audible alarms triggered
                if status.get("visual") and status.get("audible"):
                    results["bilge"] = True
                    logging.info("Bilge system diagnostic PASS")
                else:
                    logging.error("Bilge system diagnostic FAIL (alarms not triggered as expected)")
        except Exception as e:
            logging.error(f"Bilge system diagnostic exception: {e}")

        # Record timestamp of this diagnostics run
        self.last_run = datetime.datetime.now()
        logging.info(f"Diagnostics completed at {self.last_run} with results: {results}")
        return results
