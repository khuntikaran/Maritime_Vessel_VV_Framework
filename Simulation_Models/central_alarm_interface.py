"""
Maritime Vessel Safety Systems - Central Alarm Interface Simulation
Provides a central alarm system interface that aggregates alarms from all subsystem simulators.
Allows checking overall alarm status and handling maintenance mode suppression.
"""
import logging

class CentralAlarmInterface:
    def __init__(self, systems):
        """
        Initialize central alarm interface with subsystem simulators.
        :param systems: dict mapping subsystem name to simulator instance 
                        (e.g., {"fire": FireDetectionSimulator(), ...})
        """
        self.systems = systems
        # Track maintenance mode status for each subsystem (True if in maintenance, meaning alarm should be suppressed)
        self.maintenance_mode = {name: False for name in systems}
        logging.info(f"CentralAlarmInterface initialized for systems: {list(systems.keys())}")

    def set_maintenance_mode(self, system_name, mode=True):
        """
        Set or clear maintenance mode for a given subsystem.
        When maintenance mode is True, alarms from that subsystem will be suppressed (not trigger overall alarm).
        """
        if system_name in self.maintenance_mode:
            self.maintenance_mode[system_name] = mode
            status = "ON" if mode else "OFF"
            logging.info(f"Maintenance mode {status} for subsystem '{system_name}'")
            return True
        logging.error(f"Subsystem '{system_name}' not found in CentralAlarmInterface")
        return False

    def check_alarms(self):
        """
        Check all subsystems for alarm conditions and determine the overall alarm status.
        Returns a dictionary with overall alarm flag and details of triggered/suppressed alarms.
        """
        overall_alarm = False
        triggered_systems = []
        suppressed_systems = []
        # Iterate through each registered subsystem
        for name, system in self.systems.items():
            # Determine if subsystem has an active alarm condition
            alarm_active = False
            if hasattr(system, "get_alarm_status"):
                status = system.get_alarm_status()
                # If either visual or audible alarm is True, consider it active
                alarm_active = bool(status.get("visual") or status.get("audible"))
            elif hasattr(system, "alarm_interface"):
                # For ESD, use the alarm_interface signal as indication
                alarm_active = bool(system.alarm_interface.get("signal_sent"))
            # Determine if alarm should trigger overall alarm or be suppressed
            if alarm_active:
                if self.maintenance_mode.get(name, False):
                    suppressed_systems.append(name)
                    logging.info(f"Alarm from '{name}' suppressed due to maintenance mode")
                else:
                    triggered_systems.append(name)
                    overall_alarm = True
                    logging.info(f"Alarm from '{name}' contributing to overall alarm")
        result = {
            "overall_alarm": overall_alarm,
            "triggered_systems": triggered_systems,
            "suppressed_alarms": suppressed_systems
        }
        return result

    def reset_all(self):
        """
        (Optional) Reset/clear all alarm states in the central interface and subsystems.
        This would typically acknowledge and clear alarms after they have been handled.
        """
        for name, system in self.systems.items():
            # If subsystems have specific reset methods, they would be called here.
            if hasattr(system, "alarms"):
                try:
                    system.alarms = {"visual": False, "audible": False}
                except Exception:
                    pass
            if hasattr(system, "alarm_interface"):
                system.alarm_interface["signal_sent"] = False
            # Note: In real system, more complex reset logic might be needed.
        logging.info("CentralAlarmInterface: All subsystem alarms have been reset.")
