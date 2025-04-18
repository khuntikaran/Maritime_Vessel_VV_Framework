"""
Maritime Vessel Safety Systems - Maintenance & Diagnostics Tests
This module contains pytest test cases for verifying maintenance-related requirements,
such as built-in diagnostic self-tests for the safety systems.
"""
import pytest
import logging
import sys
from pathlib import Path

# Ensure Simulation_Models package is on path
sys.path.append(str(Path(__file__).parent.parent / "Simulation_Models"))

# Reuse simulation interface or fallback to mocks as in other test modules
try:
    from simulation_interface import FireDetectionSimulator, EmergencyShutdownSimulator, BilgeAlarmSimulator
except ImportError:
    # If needed, import the mock classes defined in interface-tests (assuming same test package)
    from interface_tests import FireDetectionSimulator, EmergencyShutdownSimulator, BilgeAlarmSimulator

from diagnostic_simulation import DiagnosticsSimulator

# Fixtures for subsystems (same as in interface tests)
@pytest.fixture
def fire_detection_system():
    return FireDetectionSimulator()

@pytest.fixture
def emergency_shutdown_system():
    return EmergencyShutdownSimulator()

@pytest.fixture
def bilge_alarm_system():
    return BilgeAlarmSimulator()

@pytest.mark.maintenance
class TestMaintenanceFeatures:
    """Test cases for maintenance and diagnostic requirements (built-in self-test, etc.)."""

    def test_built_in_diagnostics(self, fire_detection_system, emergency_shutdown_system, bilge_alarm_system):
        """
        Test ID: TC-SYS-MNT-001
        Requirement: REQ-SYS-MNT-001 (Automated Built-in Test Diagnostics)
        Description: Verify that the system's built-in diagnostic function can be executed 
                     and correctly report the status of all subsystems (fire detection, ESD, bilge alarm).
        """
        test_id = "TC-SYS-MNT-001"
        req_id = "REQ-SYS-MNT-001"

        # Run diagnostics across all subsystems
        diagnostics = DiagnosticsSimulator(fire_detection_system, emergency_shutdown_system, bilge_alarm_system)
        results = diagnostics.run_all_diagnostics()

        # Expect all subsystems to pass diagnostics (True)
        all_passed = results.get("fire") and results.get("esd") and results.get("bilge")
        details = {"diagnostic_results": results}
        logging.info(f"{test_id} - Details: {details}")
        assert all_passed, f"One or more subsystems failed diagnostics: {results}"
