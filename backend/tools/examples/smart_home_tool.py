"""
Example: Smart Home Control Tool (Physical World Bridge)
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from ..base import PhysicalTool, ToolSchema, ToolParameter, ToolCategory, ToolRiskLevel


class SmartHomeTool(PhysicalTool):
    """Tool for controlling smart home devices"""

    def __init__(self, config: Dict[str, Any]):
        schema = ToolSchema(
            name="smart_home",
            description="Control smart home devices (lights, thermostats, locks, etc.)",
            category=ToolCategory.SMART_HOME,
            risk_level=ToolRiskLevel.HIGH,
            parameters=[
                ToolParameter(
                    name="device_type",
                    type="string",
                    description="Type of device: light, thermostat, lock, switch, camera",
                    required=True
                ),
                ToolParameter(
                    name="device_id",
                    type="string",
                    description="Unique identifier for the device",
                    required=True
                ),
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform: on, off, set_temperature, lock, unlock, etc.",
                    required=True
                ),
                ToolParameter(
                    name="value",
                    type="object",
                    description="Additional parameters for the action",
                    required=False
                )
            ],
            returns={"type": "object", "properties": {"success": {"type": "boolean"}, "state": {"type": "object"}}},
            examples=[
                {"device_type": "light", "device_id": "living_room", "action": "on", "value": {"brightness": 75}},
                {"device_type": "thermostat", "device_id": "main", "action": "set_temperature", "value": {"temperature": 72}},
                {"device_type": "lock", "device_id": "front_door", "action": "lock"}
            ],
            requires_confirmation=True,  # Always confirm physical actions
            requires_hardware=True,
            max_calls_per_minute=10  # Limit physical actions
        )

        # Device configuration (Home Assistant, SmartThings, etc.)
        device_config = {
            "platform": config.get("platform", "homeassistant"),
            "api_url": config.get("api_url", "http://homeassistant.local:8123"),
            "api_token": config.get("api_token", ""),
            "device_map": config.get("device_map", {})
        }

        super().__init__(schema, device_config)

        # Add critical device safety checks
        self.critical_devices = ["lock", "garage_door", "security_system"]

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute smart home control with safety checks"""

        device_type = kwargs.get("device_type")
        device_id = kwargs.get("device_id")
        action = kwargs.get("action")
        value = kwargs.get("value", {})

        # Safety verification
        if not await self.verify_safety(device_type=device_type, action=action):
            return {"success": False, "error": "Safety check failed"}

        # Additional confirmation for critical devices
        if device_type in self.critical_devices:
            if not await self._get_user_confirmation(device_type, action):
                return {"success": False, "error": "User confirmation required"}

        # Execute based on platform
        platform = self.device_config["platform"]

        if platform == "homeassistant":
            return await self._control_homeassistant(device_type, device_id, action, value)
        elif platform == "smartthings":
            return await self._control_smartthings(device_type, device_id, action, value)
        elif platform == "alexa":
            return await self._control_alexa(device_type, device_id, action, value)
        else:
            return {"success": False, "error": f"Unsupported platform: {platform}"}

    async def validate_parameters(self, **kwargs) -> bool:
        """Validate smart home control parameters"""

        device_type = kwargs.get("device_type")
        action = kwargs.get("action")

        valid_device_types = ["light", "thermostat", "lock", "switch", "camera", "garage_door"]
        if device_type not in valid_device_types:
            return False

        # Validate action based on device type
        valid_actions = {
            "light": ["on", "off", "dim", "set_color", "toggle"],
            "thermostat": ["set_temperature", "set_mode", "on", "off"],
            "lock": ["lock", "unlock", "status"],
            "switch": ["on", "off", "toggle"],
            "camera": ["start_recording", "stop_recording", "snapshot"],
            "garage_door": ["open", "close", "status"]
        }

        if action not in valid_actions.get(device_type, []):
            return False

        return True

    async def _control_homeassistant(self,
                                    device_type: str,
                                    device_id: str,
                                    action: str,
                                    value: Dict) -> Dict[str, Any]:
        """Control Home Assistant devices"""

        api_url = self.device_config["api_url"]
        token = self.device_config["api_token"]

        # Map device type to Home Assistant domain
        domain_map = {
            "light": "light",
            "thermostat": "climate",
            "lock": "lock",
            "switch": "switch",
            "camera": "camera",
            "garage_door": "cover"
        }

        domain = domain_map.get(device_type)
        entity_id = f"{domain}.{device_id}"

        # Map actions to Home Assistant services
        if action == "on":
            service = "turn_on"
        elif action == "off":
            service = "turn_off"
        elif action == "lock":
            service = "lock"
        elif action == "unlock":
            service = "unlock"
        elif action == "set_temperature":
            service = "set_temperature"
        else:
            service = action

        # Prepare service data
        service_data = {"entity_id": entity_id}
        service_data.update(value)

        try:
            async with aiohttp.ClientSession() as session:
                # Call Home Assistant API
                async with session.post(
                    f"{api_url}/api/services/{domain}/{service}",
                    json=service_data,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                ) as response:
                    if response.status == 200:
                        # Get current state
                        async with session.get(
                            f"{api_url}/api/states/{entity_id}",
                            headers={"Authorization": f"Bearer {token}"}
                        ) as state_response:
                            state_data = await state_response.json()

                        return {
                            "success": True,
                            "state": {
                                "entity_id": entity_id,
                                "state": state_data.get("state"),
                                "attributes": state_data.get("attributes", {}),
                                "last_changed": state_data.get("last_changed")
                            }
                        }
                    else:
                        error = await response.text()
                        return {"success": False, "error": error}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _control_smartthings(self,
                                   device_type: str,
                                   device_id: str,
                                   action: str,
                                   value: Dict) -> Dict[str, Any]:
        """Control SmartThings devices"""
        # Implementation would use SmartThings API
        return {"success": False, "error": "SmartThings not implemented"}

    async def _control_alexa(self,
                            device_type: str,
                            device_id: str,
                            action: str,
                            value: Dict) -> Dict[str, Any]:
        """Control Alexa-connected devices"""
        # Implementation would use Alexa API
        return {"success": False, "error": "Alexa not implemented"}

    async def _get_user_confirmation(self,
                                    device_type: str,
                                    action: str) -> bool:
        """Get user confirmation for critical actions"""
        # In production, this would send a push notification
        # or display a confirmation dialog
        print(f"⚠️  CRITICAL ACTION: {action} on {device_type}")
        print("Requires user confirmation...")

        # For demo, auto-approve after delay
        await asyncio.sleep(2)
        return True

    async def verify_safety(self, **kwargs) -> bool:
        """Enhanced safety checks for physical devices"""

        device_type = kwargs.get("device_type")
        action = kwargs.get("action")

        # Check time-based restrictions
        current_hour = datetime.now().hour
        if device_type == "lock" and action == "unlock":
            # Don't unlock doors late at night without extra confirmation
            if current_hour >= 22 or current_hour <= 6:
                print("⚠️  Late night unlock attempt - extra verification required")
                # Would require 2FA or additional confirmation
                return True  # For demo

        # Check for rapid successive actions (possible malfunction)
        # In production, track recent actions and detect anomalies

        # Verify device is in expected state before action
        # E.g., don't try to lock an already locked door

        return await super().verify_safety(**kwargs)


# Example usage
async def example_smart_home_control():
    """Example of controlling smart home devices"""

    # Configure tool with Home Assistant
    config = {
        "platform": "homeassistant",
        "api_url": "http://192.168.1.100:8123",
        "api_token": "your-long-lived-token"
    }

    smart_home = SmartHomeTool(config)

    # Turn on living room lights
    result = await smart_home.execute(
        device_type="light",
        device_id="living_room",
        action="on",
        value={"brightness": 75, "color_temp": 3000}
    )
    print("Light control:", result)

    # Set thermostat temperature
    result = await smart_home.execute(
        device_type="thermostat",
        device_id="main",
        action="set_temperature",
        value={"temperature": 72}
    )
    print("Thermostat control:", result)

    # Lock front door (requires confirmation)
    result = await smart_home.execute(
        device_type="lock",
        device_id="front_door",
        action="lock"
    )
    print("Lock control:", result)