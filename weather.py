import tkinter as tk
import requests
import win32gui
import win32con
import json
import os
import asyncio
from winsdk.windows.devices import geolocation as geo

# ===== CONFIG =====
API_KEY = "3e04dee986b3b9b37bbda3d8cf171a1f"   # <-- put your OpenWeather API key here
REFRESH_INTERVAL = 600000  # 10 min in ms
CONFIG_FILE = "weather_widget_config.json"
# ==================

class WeatherWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("Weather Desktop Gadget")
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.9)
        self.root.configure(bg="black")

        self.label = tk.Label(root, font=("Arial", 14, "bold"), fg="cyan", bg="black", justify="center")
        self.label.pack(padx=15, pady=10)

        # Default settings
        self.units = "metric"  # "metric" = °C, "imperial" = °F

        # Right-click menu
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Toggle °C / °F", command=self.toggle_units)
        self.menu.add_command(label="Save Position", command=self.save_position)
        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=self.root.quit)
        self.root.bind("<Button-3>", self.show_menu)

        # Dragging
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

        # Attach widget to desktop
        self.set_parent_to_desktop()

        # Load saved config (position + units)
        self.load_config()

        # Start updates
        self.update_weather()

    def set_parent_to_desktop(self):
        progman = win32gui.FindWindow("Progman", None)
        win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)

        workerw = []
        def enum_handler(hwnd, lparam):
            if win32gui.GetClassName(hwnd) == "WorkerW":
                workerw.append(hwnd)
        win32gui.EnumWindows(enum_handler, None)

        hwnd = win32gui.FindWindow(None, self.root.title())
        if hwnd and workerw:
            win32gui.SetParent(hwnd, workerw[0])

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        x = event.x_root - self.x
        y = event.y_root - self.y
        self.root.geometry(f"+{x}+{y}")

    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def save_position(self):
        geom = self.root.geometry()
        pos = geom.split("+")[1:]
        config = {"x": int(pos[0]), "y": int(pos[1]), "units": self.units}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        print("Position + units saved:", config)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            x, y = config.get("x", 100), config.get("y", 100)
            self.units = config.get("units", "metric")
            self.root.geometry(f"+{x}+{y}")
            print("Loaded config:", config)
        else:
            self.root.geometry("+100+100")

    def toggle_units(self):
        self.units = "imperial" if self.units == "metric" else "metric"
        self.update_weather()
        self.save_position()

    # ===== Windows Location Service =====
    async def get_win_location(self):
        locator = geo.Geolocator()
        pos = await locator.get_geoposition_async()
        lat = pos.coordinate.point.position.latitude
        lon = pos.coordinate.point.position.longitude
        return lat, lon

    def get_location(self):
        # Try Windows Location
        try:
            lat, lon = asyncio.run(self.get_win_location())
            return None, None, lat, lon
        except Exception as e:
            print("Windows location failed:", e)

        # Fallback to IP-based location
        try:
            data = requests.get("http://ip-api.com/json").json()
            return data.get("city"), data.get("country"), data.get("lat"), data.get("lon")
        except Exception as e:
            print("IP location failed:", e)
            return None, None, None, None
    # ==============================

    def update_weather(self):
        try:
            city, country, lat, lon = self.get_location()
            if lat and lon:
                url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units={self.units}"
                data = requests.get(url).json()

                if data.get("main"):
                    temp = data["main"]["temp"]
                    tmin = data["main"]["temp_min"]
                    tmax = data["main"]["temp_max"]

                    unit_symbol = "°C" if self.units == "metric" else "°F"
                    location_name = data.get("name", city if city else "Unknown")

                    self.label.config(
                        text=f"{location_name}\n🌡 {temp:.1f}{unit_symbol}\n⬆ {tmax:.1f}{unit_symbol} ⬇ {tmin:.1f}{unit_symbol}"
                    )
                else:
                    self.label.config(text="Error fetching weather")
            else:
                self.label.config(text="Location not found")
        except Exception as e:
            self.label.config(text=f"Error: {e}")

        self.root.after(REFRESH_INTERVAL, self.update_weather)


if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherWidget(root)
    root.mainloop()
