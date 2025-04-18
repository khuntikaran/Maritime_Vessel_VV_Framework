"""
Maritime Vessel Safety Systems - Common Features Tests
This module contains pytest test cases for verifying common system requirements,
such as operation on emergency power and alarm functionality under power failure conditions.
"""
import pytest
import time
import logging
import sys
from pathlib import Path

# Ensure Simulation_Models package is on path
sys.path.append(str(Path(__file__).parent.parent / "Simulation_Models"))

# Import simulation classes or mocks
try:
    from simulation_interface import FireDetectionSimulator, EmergencyShutdownSimulator, BilgeAlarmSimulator
except ImportError:
    from interface_tests import FireDetectionSimulator, EmergencyShutdownSimulator, BilgeAlarmSimulator

# Fixtures for subsystems
@pytest.fixture
def fire_detection_system():
    return FireDetectionSimulator()

@pytest.fixture
def bilge_alarm_system():
    return BilgeAlarmSimulator()

# (ESD not needed as separate fixture here since no direct power-failure test for ESD in this module)

@pytest.mark.common
class TestCommonSystemFeatures:
    """Test cases for common system-wide requirements (e.g., emergency power support)."""

    def test_fire_detection_emergency_power(self, fire_detection_system):
        """
        Test ID: TC-SYS-PWR-001
        Requirement: REQ-SYS-PWR-001 (Emergency Power Operation - Fire Detection)
        Description: Verify that the fire detection system continues to operate and alarm on emergency power.
        """
        test_id = "TC-SYS-PWR-001"
        req_id = "REQ-SYS-PWR-001"

        # Simulate loss of main power for fire detection system
        fire_detection_system.trigger_power_failure()
        # Simulate a fire condition after switching to emergency power
        fire_detection_system.set_sensor_value("sensor_5", "temp", 75.0)
        fire_detection_system.set_sensor_value("sensor_5", "smoke", 0.4)
        fire_detection_system.run_simulation(duration=1.0)
        alarm_status = fire_detection_system.get_alarm_status()
        alarms_triggered = alarm_status.get("visual") and alarm_status.get("audible")

        details = {
            "power_status": getattr(fire_detection_system, "power_status", None),
            "alarm_status": alarm_status
        }
        logging.info(f"{test_id} - Details: {details}")
        assert alarms_triggered, "Fire detection system failed to alarm under emergency power"

    def test_bilge_alarm_power_failure_notification(self, bilge_alarm_system):
        """
        Test ID: TC-SYS-PWR-002
        Requirement: REQ-SYS-PWR-002 (Power Failure Notification - Bilge System)
        Description: Verify that the bilge alarm system provides a timely notification upon power failure.
        """
        test_id = "TC-SYS-PWR-002"
        req_id = "REQ-SYS-PWR-002"

        # Simulate power failure on the bilge alarm system
        result = bilge_alarm_system.simulate_power_failure()
        notification_sent = result.get("notification_sent", False)
        delay = result.get("time_delay", None)

        # Check that a notification is sent and within acceptable time (e.g., under 5 seconds)
        requirement_met = notification_sent and (delay is not None and delay <= 5.0)
        details = {"notification_sent": notification_sent, "time_delay_sec": delay}
        logging.info(f"{test_id} - Details: {details}")
        assert requirement_met, f"Bilge system power-failure notification delay too long or not sent (delay={delay})"

    def test_bilge_alarm_emergency_power_operation(self, bilge_alarm_system):
        """
        Test ID: TC-SYS-PWR-003
        Requirement: REQ-SYS-PWR-003 (Emergency Power Operation - Bilge Alarm)
        Description: Verify that the bilge alarm system continues to monitor and alarm under emergency power conditions.
        """
        test_id = "TC-SYS-PWR-003"
        req_id = "REQ-SYS-PWR-003"

        # Simulate main power failure for bilge system
        bilge_alarm_system.simulate_power_failure()
        # Introduce high water level condition after power failure
        compartment_id = next(iter(bilge_alarm_system.compartments))
        bilge_alarm_system.set_water_level(compartment_id, bilge_alarm_system.compartments[compartment_id]["alarm_threshold"] + 5.0)
        bilge_alarm_system.run_simulation(duration=1.0)
        alarm_status = bilge_alarm_system.get_alarm_status()
        alarms_triggered = alarm_status.get("visual") and alarm_status.get("audible")

        details = {
            "power_status": getattr(bilge_alarm_system, "power_status", None),
            "alarm_status": alarm_status
        }
        logging.info(f"{test_id} - Details: {details}")
        assert alarms_triggered, "Bilge alarm system did not trigger under emergency power conditions"
