import asyncio
import colorsys
from kasa import Discover, Module
from .abstract_bulb_control import AbstractBulbControl
from screensync.screen_sync.stats import runtime_stats


class KasaBulbControl(AbstractBulbControl):
    """Control class for Kasa smart bulbs using python-kasa library."""

    def __init__(self, device_alias, rate_limiter, placement):
        """
        Initialize Kasa bulb control.
        
        Args:
            device_alias: The name/alias of the Kasa device as shown in the Kasa app
            rate_limiter: RateLimiter instance for controlling update frequency
            placement: Screen zone placement for this bulb (e.g., 'center', 'center-left')
        """
        self.device_alias = device_alias
        self.device = None
        self.light_module = None
        self.rate_limiter = rate_limiter
        self.last_color = None
        self.placement = placement
        self.type = "Kasa"

    def connect(self):
        """Discover and connect to the Kasa device by its alias."""
        try:
            # Run async discovery in synchronous context
            devices = asyncio.run(Discover.discover())
            
            # Find device by alias
            for device in devices.values():
                asyncio.run(device.update())
                if device.alias == self.device_alias:
                    self.device = device
                    # Get the light module for color control
                    if Module.Light in device.modules:
                        self.light_module = device.modules[Module.Light]
                    print(f"Connected to Kasa device: {self.device_alias}")
                    return
            
            print(f"Warning: Could not find Kasa device with alias '{self.device_alias}'")
        except Exception as e:
            print(f"Error connecting to Kasa device '{self.device_alias}': {e}")

    @runtime_stats.timed_function('update_kasa_bulb')
    def set_color(self, r, g, b):
        """
        Set the color of the Kasa bulb using RGB values.
        
        Args:
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
        """
        new_color = (r, g, b)
        if new_color == self.last_color:
            return  # No change in color, no need to update

        if self.rate_limiter.is_allowed() and self.device and self.light_module:
            try:
                # Convert RGB to HSV
                h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)

                # Scale HSV values to Kasa's expected range
                h_scaled = int(h * 360)  # Hue: 0-360
                s_scaled = int(s * 100)  # Saturation: 0-100
                v_scaled = int(v * 100)  # Value/Brightness: 0-100

                # Set the HSV color asynchronously
                asyncio.run(self.light_module.set_hsv(h_scaled, s_scaled, v_scaled))
                
                self.last_color = new_color  # Store the new color
            except Exception as e:
                print(f"Error setting color for '{self.device_alias}': {e}")

    def turn_off(self):
        """Turn off the Kasa bulb."""
        if self.device:
            try:
                asyncio.run(self.device.turn_off())
            except Exception as e:
                print(f"Error turning off '{self.device_alias}': {e}")

    def turn_on(self):
        """Turn on the Kasa bulb."""
        if self.device:
            try:
                asyncio.run(self.device.turn_on())
            except Exception as e:
                print(f"Error turning on '{self.device_alias}': {e}")

    def set_brightness(self, brightness):
        """
        Set the brightness of the Kasa bulb.
        
        Args:
            brightness: Brightness value (0-100)
        """
        if self.device and self.light_module:
            try:
                asyncio.run(self.light_module.set_brightness(brightness))
            except Exception as e:
                print(f"Error setting brightness for '{self.device_alias}': {e}")

    def status(self):
        """Get the current status of the Kasa bulb."""
        if self.device:
            try:
                asyncio.run(self.device.update())
                return self.device.sys_info
            except Exception as e:
                print(f"Error getting status for '{self.device_alias}': {e}")
                return None

