import threading
import time
from collections import defaultdict
from screensync.screen_sync.stats import runtime_stats

class Coordinator:
    def __init__(self, bulbs, color_processing_module):
        self.bulbs = bulbs
        self.color_processing = color_processing_module
        self.mode = 'normal'
        self.running = False
        self.color_cache = defaultdict(lambda: (0, 0, 0))  # Default color is black
        self.lock = threading.Lock()
        self.brightness = 100  # Brightness percentage (1-100)

    def set_mode(self, mode):
        self.mode = mode
        # Any other updates required when changing modes

    def set_brightness(self, brightness):
        """Set the brightness percentage (1-100)"""
        self.brightness = max(1, min(100, brightness))  # Clamp between 1 and 100

    def apply_brightness(self, color):
        """Apply brightness multiplier to RGB color"""
        r, g, b = color
        multiplier = self.brightness / 100.0
        return (int(r * multiplier), int(g * multiplier), int(b * multiplier))

    def update_bulbs(self, new_bulbs):
        if self.running:
            self.stop()
        self.bulbs = new_bulbs
        self.start()
        if self.running:
            self.start()

    def update_bulb_color(self, bulb, color):
        # Update the bulb color in a new thread
        t = threading.Thread(target=bulb.set_color, args=color)
        t.start()
        self.threads.append(t)

    def start(self):
        print(f"[Coordinator] Starting screen sync with {len(self.bulbs)} bulb(s)")
        for bulb in self.bulbs:
            bulb_info = f"{bulb.type} - {getattr(bulb, 'device_alias', getattr(bulb, 'device_id', 'unknown'))}"
            print(f"[Coordinator] - {bulb_info} (placement: {bulb.placement})")
        self.running = True
        self.update_thread = threading.Thread(target=self.run_update_loop)
        self.update_thread.start()
        self.threads = [threading.Thread(target=self.update_bulb_color, args=(bulb,)) for bulb in self.bulbs]
        for thread in self.threads:
            thread.start()
        print("[Coordinator] Screen sync started successfully")


    def run_update_loop(self):
        while self.running:
            # Record update for stats
            runtime_stats.record_update()

            if self.mode == 'shooter':
                # In shooter mode, capture the screen once for the center
                center_color = self.color_processing.process_screen_zone('center', mode='Shooter')
                # Apply brightness
                center_color = self.apply_brightness(center_color)
                for bulb in self.bulbs:
                    # Update all bulbs with the center color
                    self.update_bulb_color(bulb, center_color)
            else:
                # In normal mode, update each bulb based on its zone
                for bulb in self.bulbs:
                    zone_color = self.color_processing.process_screen_zone(bulb.placement)
                    # Apply brightness
                    zone_color = self.apply_brightness(zone_color)
                    self.update_bulb_color(bulb, zone_color)

            # Sleep to avoid overloading
            time.sleep(0.0001)


    def stop(self):
        print("[Coordinator] Stopping screen sync...")
        self.running = False
        if self.update_thread:
            self.update_thread.join()
        for t in self.threads:
            t.join()
        
        # Send a warm yellow color at 50% brightness to all bulbs
        warm_yellow = (255, 220, 150)  # Warm yellow RGB
        warm_yellow_dimmed = (int(255 * 0.5), int(220 * 0.5), int(150 * 0.5))
        for bulb in self.bulbs:
            try:
                bulb.set_color(*warm_yellow_dimmed)
            except Exception as e:
                print(f"[Coordinator] Error setting final color for bulb: {e}")
        print("[Coordinator] Screen sync stopped")

# Usage in your main script
# coordinator = Coordinator(bulbs, color_processing)
# coordinator.start()  # This starts the processing and updating loop
