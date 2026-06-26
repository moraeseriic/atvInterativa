# Simula um sensor IoT gerando leituras de temperatura e umidade
import json
import random
import time


class Sensor:
    def __init__(self, sensor_id: str = "sensor-01"):
        self.sensor_id = sensor_id
        self._temp = 25.0
        self._hum = 60.0

    def read(self) -> dict:
        self._temp = round(self._temp + random.uniform(-0.5, 0.5), 2)
        self._hum = round(self._hum + random.uniform(-1.0, 1.0), 2)
        self._temp = max(15.0, min(40.0, self._temp))
        self._hum = max(20.0, min(95.0, self._hum))
        return {
            "id": self.sensor_id,
            "temperatura": self._temp,
            "umidade": self._hum,
            "ts": int(time.time()),
        }

    def read_json(self) -> bytes:
        return json.dumps(self.read(), separators=(",", ":")).encode("utf-8")


if __name__ == "__main__":
    s = Sensor()
    for _ in range(3):
        print(s.read_json().decode())
        time.sleep(0.2)
