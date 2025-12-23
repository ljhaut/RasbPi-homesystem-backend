import serial

from core.logging_config import setup_logger

logger = setup_logger()


class Talker:
    TERMINATOR = "\r".encode("UTF8")

    def __init__(self, name: str, timeout: int = 1):
        """
        Initialize Talker object.

        :param self: Instance of the Talker class
        :param name: Name of the serial port
        :type name: str
        :param timeout: Timeout for serial communication in seconds, defaults to 1
        :type timeout: int
        """
        self.name = name
        self.id = name[-1]  # last character of name
        self.serial = serial.Serial(name, 115200, timeout=timeout)
        # TODO: Add error handling for serial connection
        # TODO: user input for successful connection

    def send_to_pico(self, text: str) -> str:
        """
        Send a line of text to the Pico device.

        :param self: Instance of the Talker class
        :param text: Text to send to the Pico device
        :type text: str
        :return: Reply from the Pico device
        :rtype: str
        """
        line = "%s\r\f" % text
        self.serial.write(line.encode("utf-8"))
        reply = self.receive_from_pico()
        reply = reply.replace(
            ">>> ", ""
        )  # lines after first will be prefixed by a propmt
        return reply

    def receive_from_pico(self) -> str:
        """
        Receive a line of text from the Pico device.

        :param self: Instance of the Talker class
        :return: Received text from the Pico device
        :rtype: str
        """
        line = self.serial.read_until(self.TERMINATOR)
        return line.decode("UTF8").strip() + " " + self.name

    def close_connection(self) -> None:
        """
        Close the serial connection.

        :param self: Instance of the Talker class
        """
        self.serial.close()

    def get_id(self) -> str:
        """
        Get the ID of the Talker instance.

        :param self: Instance of the Talker class
        :return: ID of the Talker instance
        :rtype: str
        """
        return self.id
