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
        try:
            t = threading.Thread(target=bulb.set_color, args=color)
            t.start()
            self.threads.append(t)
        except Exception as e:
            print(f"[Coordinator] Error updating bulb color: {e}")

    def start(self):
        try:
            print(f"[Coordinator] Starting screen sync with {len(self.bulbs)} bulb(s)")
            for bulb in self.bulbs:
                bulb_info = f"{bulb.type} - {getattr(bulb, 'device_alias', getattr(bulb, 'device_id', 'unknown'))}"
                print(f"[Coordinator] - {bulb_info} (placement: {bulb.placement})")
            self.running = True
            self.threads = []  # Initialize threads list
            self.update_thread = threading.Thread(target=self.run_update_loop)
            self.update_thread.start()
            print("[Coordinator] Screen sync started successfully")
        except Exception as e:
            print(f"[Coordinator] Error starting screen sync: {e}")
            self.running = False


    def run_update_loop(self):
        while self.running:
            try:
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
            except Exception as e:
                print(f"[Coordinator] Error in update loop: {e}")
                # Continue running even if there's an error
                time.sleep(0.1)  # Sleep a bit longer on error to avoid spam


    def stop(self):
        print("[Coordinator] Stopping screen sync...")
        self.running = False
        
        # Wait for update thread to finish with timeout
        if self.update_thread:
            try:
                self.update_thread.join(timeout=2.0)  # 2 second timeout
                if self.update_thread.is_alive():
                    print("[Coordinator] Warning: Update thread did not stop gracefully")
            except Exception as e:
                print(f"[Coordinator] Error stopping update thread: {e}")
        
        # Wait for all bulb threads to finish with timeout
        for t in self.threads:
            try:
                t.join(timeout=1.0)  # 1 second timeout per thread
                if t.is_alive():
                    print("[Coordinator] Warning: A bulb thread did not stop gracefully")
            except Exception as e:
                print(f"[Coordinator] Error stopping bulb thread: {e}")
        
        # Send a warm yellow color at 50% brightness to all bulbs in a non-blocking way
        def set_final_colors():
            warm_yellow = (255, 220, 150)  # Warm yellow RGB
            warm_yellow_dimmed = (int(255 * 0.5), int(220 * 0.5), int(150 * 0.5))
            for bulb in self.bulbs:
                try:
                    bulb.set_color(*warm_yellow_dimmed)
                except Exception as e:
                    print(f"[Coordinator] Error setting final color for bulb: {e}")
        
        # Run final color setting in background thread so it doesn't block UI
        try:
            final_color_thread = threading.Thread(target=set_final_colors)
            final_color_thread.daemon = True  # Daemon thread won't prevent program exit
            final_color_thread.start()
        except Exception as e:
            print(f"[Coordinator] Error starting final color thread: {e}")
        
        print("[Coordinator] Screen sync stopped")

# Usage in your main script
# coordinator = Coordinator(bulbs, color_processing)
# coordinator.start()  # This starts the processing and updating loop
