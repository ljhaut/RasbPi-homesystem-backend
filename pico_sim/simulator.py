import os
import pty
import re
import termios
import threading
import time
from pathlib import Path


class PicoSim:
    TERMINATOR = b"\r"

    def __init__(self, id: int):
        self.id = id
        self.master, self.slave = pty.openpty()
        self.slave_name = os.ttyname(self.slave)

        attrs = termios.tcgetattr(self.master)
        attrs[3] = attrs[3] & ~termios.ECHO | ~termios.ICANON
        termios.tcsetattr(self.master, termios.TCSANOW, attrs)

        print(f"[PicoSim-{id}] Created virtual serial port: {self.slave_name}")

    def start(self):
        """Start simulation thread."""
        t = threading.Thread(target=self.run, daemon=True)
        t.start()

    def run(self):
        """Main loop simulating the Pico REPL."""
        while True:
            data = os.read(self.master, 1024)
            if not data:
                break
            text = data.decode().strip()
            if not text or text in ("\r", "\n", "\r\n"):
                continue
            text = re.sub(r"[\x00-\x1F\x7F]+", "", text).strip()
            if text:
                response = self.handle_command(text)
                os.write(self.master, (response + "\r ").encode())

    def handle_command(self, text: str) -> str:
        """Mock a simple MicroPython interpreter."""
        if text.lower() in ("help()", "?"):
            return "PicoSim help: try print('hi') or 1+1"
        elif text.startswith("print("):
            try:
                val = eval(text[6:-1])
                return str(val)
            except Exception as e:
                return f"Error: {e}"
        elif text == "1+1":
            return "2"
        elif text == "machine.freq()":
            return "125000000"
        elif text == "ping()":
            return "pong"
        elif text.startswith("turn_on_pin("):
            pin = text[len("turn_on_pin(") : -1]
            return f"PicoSim {self.id}: turned ON pin {pin}"
        elif text.startswith("turn_off_pin("):
            pin = text[len("turn_off_pin(") : -1]
            return f"PicoSim {self.id}: turned OFF pin {pin}"
        else:
            return f"PicoSim {self.id}: received '{text}'"


def write_env_file(simulators: list[PicoSim], filepath="/workspace/pico_sim.env"):
    """Write Pico port mappings to an .env file for other containers."""
    lines = [f"PICO{i.id}_PATH={i.slave_name}" for i in simulators]
    filepath = Path(filepath)
    filepath.write_text("\n".join(lines) + "\n")
    print(f"\n📝 Wrote Pico port paths to: {filepath}")
    print(filepath.read_text())


def main():
    num_picos = int(os.getenv("NUM_PICOS", "2"))
    sims = [PicoSim(i + 1) for i in range(num_picos)]
    for sim in sims:
        sim.start()

    write_env_file(sims)

    print("\n🟢 Pico simulators running.")

    for sim in sims:
        print(f"  -> {sim.slave_name}")

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
