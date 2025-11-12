import os
import pty
import threading
import time
from pathlib import Path


class PicoSim:
    TERMINATOR = b"\r"

    def __init__(self, id: int):
        self.id = id
        self.master, self.slave = pty.openpty()
        self.slave_name = os.ttyname(self.slave)
        print(f"[PicoSim-{id}] Created virtual serial port: {self.slave_name}")

    def start(self):
        """Start simulation thread."""
        t = threading.Thread(target=self.run, daemon=True)
        t.start()

    def run(self):
        """Main loop simulating the Pico REPL."""
        os.write(self.master, b"MicroPython v1.21.0 on PicoSim\r>>> ")
        while True:
            data = os.read(self.master, 1024)
            if not data:
                break
            text = data.decode().strip()
            if text:
                response = self.handle_command(text)
                os.write(self.master, (response + "\r>>> ").encode())

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
