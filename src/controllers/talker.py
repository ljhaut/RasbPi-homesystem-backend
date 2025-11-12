import serial

from core.logging_config import setup_logger

logger = setup_logger()


class Talker:
    TERMINATOR = "\r".encode("UTF8")

    def __init__(self, name: str, timeout: int = 1):
        self.name = name
        self.id = name[-1]  # last character of name
        self.serial = serial.Serial(name, 115200, timeout=timeout)
        # TODO: Add error handling for serial connection
        # TODO: user input for successful connection

    def send_to_pico(self, text: str):
        line = "%s\r\f" % text
        self.serial.write(line.encode("utf-8"))
        reply = self.receive_from_pico()
        reply = reply.replace(
            ">>> ", ""
        )  # lines after first will be prefixed by a propmt

    def receive_from_pico(self) -> str:
        line = self.serial.read_until(self.TERMINATOR)
        return line.decode("UTF8").strip() + " " + self.name

    def close_connection(self):
        self.serial.close()

    def get_id(self) -> str:
        return self.id
