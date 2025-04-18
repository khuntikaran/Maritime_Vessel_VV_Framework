"""
Maritime Vessel Safety Systems - Interface Integration Tests
This module contains pytest test cases for verifying system interface requirements,
such as the central alarm interface that aggregates alarms from all subsystems.
"""
import pytest
import time
import logging
import sys
from pathlib import Path

# Ensure Simulation_Models package is on path
sys.path.append(str(Path(__file__).parent.parent / "Simulation_Models"))

# Try to import real simulation interfaces; use mock simulators if not available
try:
    from simulation_interface import FireDetectionSimulator, EmergencyShutdownSimulator, BilgeAlarmSimulator
    SIMULATION_AVAILABLE = True
except ImportError:
    SIMULATION_AVAILABLE = False
    logging.warning("simulation_interface not available; using mock simulators for tests.")

    # Define mock simulator classes (as in automated-testing-framework) for fallback
    class FireDetectionSimulator:
        def __init__(self):
            self.sensors = {f"sensor_{i}": {"temp": 25.0, "smoke": 0.0} for i in range(1, 11)}
            self.alarms = {"visual": False, "audible": False}
            self.power_status = "main"
        def set_sensor_value(self, sensor_id, parameter, value):
            if sensor_id in self.sensors and parameter in self.sensors[sensor_id]:
                self.sensors[sensor_id][parameter] = value
                return True
            return False
        def get_alarm_status(self):
            return self.alarms
        def trigger_power_failure(self):
            self.power_status = "emergency"
            return True
        def run_simulation(self, duration):
            time.sleep(0.1)
            for sensor in self.sensors.values():
                if sensor.get("temp", 0) > 50 or sensor.get("smoke", 0) > 0.3:
                    self.alarms["visual"] = True
                    self.alarms["audible"] = True
                    break

    class EmergencyShutdownSimulator:
        def __init__(self):
            self.fuel_valves = {"main": "open", "auxiliary": "open"}
            self.activation_points = {"bridge": False, "engine_room": False}
            self.alarm_interface = {"connected": True, "signal_sent": False}
        def activate_shutdown(self, activation_point):
            if activation_point in self.activation_points:
                self.activation_points[activation_point] = True
                time_start = time.time()
                # Simulate shutting fuel valves and sending alarm signal
                time.sleep(0.05)
                self.fuel_valves["main"] = "closed"
                time.sleep(0.03)
                self.fuel_valves["auxiliary"] = "closed"
                self.alarm_interface["signal_sent"] = True
                return time.time() - time_start
            return None
        def get_valve_status(self):
            return self.fuel_valves

    class BilgeAlarmSimulator:
        def __init__(self):
            self.compartments = {f"compartment_{i}": {"water_level": 0.0, "alarm_threshold": 150.0} for i in range(1, 6)}
            self.alarms = {"visual": False, "audible": False}
            self.power_status = "normal"
        def set_water_level(self, compartment_id, level):
            if compartment_id in self.compartments:
                self.compartments[compartment_id]["water_level"] = level
                return True
            return False
        def get_alarm_status(self):
            return self.alarms
        def simulate_power_failure(self):
            self.power_status = "failed"
            return {"notification_sent": True, "time_delay": 2.3}
        def run_simulation(self, duration):
            time.sleep(0.1)
            for comp in self.compartments.values():
                if comp["water_level"] >= comp["alarm_threshold"]:
                    self.alarms["visual"] = True
                    self.alarms["audible"] = True
                    break

# Import simulator enhancement modules
from central_alarm_interface import CentralAlarmInterface
from diagnostic_simulation import DiagnosticsSimulator

# Fixtures for subsystems (yield fresh instance per test)
@pytest.fixture
def fire_detection_system():
    return FireDetectionSimulator()

@pytest.fixture
def emergency_shutdown_system():
    return EmergencyShutdownSimulator()

@pytest.fixture
def bilge_alarm_system():
    return BilgeAlarmSimulator()

@pytest.mark.interface
class TestSystemInterfaces:
    """Test cases for system interface integration requirements (central alarm interface)."""

    def test_central_alarm_propagation(self, fire_detection_system, emergency_shutdown_system, bilge_alarm_system):
        """
        Test ID: TC-SYS-INTF-001
        Requirement: REQ-SYS-INTF-001 (Central Alarm Interface Integration)
        Description: Verify that the central alarm interface activates a general alarm 
                     when any subsystem (fire detection, ESD, or bilge alarm) triggers an alarm condition.
        """
        test_id = "TC-SYS-INTF-001"
        req_id = "REQ-SYS-INTF-001"

        # Initialize central alarm interface with all subsystems
        central_alarm = CentralAlarmInterface({
            "fire": fire_detection_system, 
            "esd": emergency_shutdown_system, 
            "bilge": bilge_alarm_system
        })

        # 1. Simulate a fire detection alarm condition
        fire_detection_system.set_sensor_value("sensor_1", "temp", 80.0)
        fire_detection_system.set_sensor_value("sensor_1", "smoke", 0.5)
        fire_detection_system.run_simulation(duration=1.0)
        status_fire = central_alarm.check_alarms()
        fire_overall = status_fire["overall_alarm"]
        fire_triggered = "fire" in status_fire["triggered_systems"]

        # Reset for next condition
        fire_detection_system.alarms = {"visual": False, "audible": False}

        # 2. Simulate an emergency shutdown alarm signal (ESD activation)
        emergency_shutdown_system.activate_shutdown("bridge")
        status_esd = central_alarm.check_alarms()
        esd_overall = status_esd["overall_alarm"]
        esd_triggered = "esd" in status_esd["triggered_systems"]

        # Reset for next condition
        emergency_shutdown_system.alarm_interface["signal_sent"] = False

        # 3. Simulate a bilge high-water alarm condition
        comp_id = next(iter(bilge_alarm_system.compartments))
        bilge_alarm_system.set_water_level(comp_id, bilge_alarm_system.compartments[comp_id]["alarm_threshold"])
        bilge_alarm_system.run_simulation(duration=1.0)
        status_bilge = central_alarm.check_alarms()
        bilge_overall = status_bilge["overall_alarm"]
        bilge_triggered = "bilge" in status_bilge["triggered_systems"]

        # All individual triggers should cause the central overall alarm to activate
        requirement_met = fire_overall and fire_triggered and esd_overall and esd_triggered and bilge_overall and bilge_triggered

        details = {
            "fire_alarm_triggered": fire_triggered,
            "esd_alarm_triggered": esd_triggered,
            "bilge_alarm_triggered": bilge_triggered,
            "overall_alarm_after_fire": fire_overall,
            "overall_alarm_after_esd": esd_overall,
            "overall_alarm_after_bilge": bilge_overall
        }
        logging.info(f"{test_id} - Details: {details}")
        assert requirement_met, "Central alarm interface failed to propagate alarms from all subsystems"

    def test_central_alarm_maintenance_mode(self, fire_detection_system, emergency_shutdown_system, bilge_alarm_system):
        """
        Test ID: TC-SYS-INTF-002
        Requirement: REQ-SYS-INTF-002 (Alarm Suppression in Maintenance Mode)
        Description: Verify that when a subsystem is in maintenance mode, its alarms are suppressed 
                     in the central alarm interface (no general alarm is activated for that subsystem).
        """
        test_id = "TC-SYS-INTF-002"
        req_id = "REQ-SYS-INTF-002"

        # Initialize central alarm interface and set one subsystem (fire) to maintenance mode
        central_alarm = CentralAlarmInterface({
            "fire": fire_detection_system, 
            "esd": emergency_shutdown_system, 
            "bilge": bilge_alarm_system
        })
        central_alarm.set_maintenance_mode("fire", True)

        # Simulate a fire alarm condition while fire system is under maintenance
        fire_detection_system.set_sensor_value("sensor_2", "temp", 80.0)
        fire_detection_system.set_sensor_value("sensor_2", "smoke", 0.4)
        fire_detection_system.run_simulation(duration=1.0)
        status = central_alarm.check_alarms()
        overall_alarm = status["overall_alarm"]
        suppressed = status["suppressed_alarms"]

        # The fire alarm should be suppressed (no overall alarm, fire listed in suppressed_alarms)
        requirement_met = (not overall_alarm) and ("fire" in suppressed)

        details = {
            "fire_alarm_triggered": fire_detection_system.get_alarm_status(),
            "overall_alarm": overall_alarm,
            "suppressed_alarms": suppressed
        }
        logging.info(f"{test_id} - Details: {details}")
        assert requirement_met, "Maintenance mode did not suppress the fire alarm in central interface"
