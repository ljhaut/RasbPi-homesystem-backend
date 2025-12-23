import serial

from core.logging_config import setup_logger

logger = setup_logger()


class Talker:
    TERMINATOR = "\r".encode("UTF8")

    def __init__(self, name: str, id: int, timeout: int = 1):
        """
        Initialize Talker object.

        :param self: Instance of the Talker class
        :param name: Name of the serial port
        :type name: str
        :param timeout: Timeout for serial communication in seconds, defaults to 1
        :type timeout: int
        """
        self.name = name
        self.id = id
        self.serial = serial.Serial(name, 115200, timeout=timeout)
        logger.info(f"[Talker {self.id}] Serial connection opened on {name}")
        self.verify_connection()
        # TODO: Add error handling for serial connection
        # TODO: user input for successful connection

    def verify_connection(self) -> bool:
        """
        Verify the connection to the Pico device is stable.

        :param self: Instance of the Talker class
        :return: True if connection is verified, False otherwise
        :rtype: bool
        """
        try:
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

            response = self.send_to_pico("ping()")

            if response:
                logger.info(
                    f"[Talker {self.id}] Connection verified with response: {response}"
                )
                return True
            else:
                logger.error(
                    f"[Talker {self.id}] No response received during connection verification."
                )
                return False
        except Exception as e:
            logger.error(f"[Talker {self.id}] Connection verification failed: {e}")
            return False

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
        logger.debug(f"[Talker {self.id}] Sent: {text} | Received: {reply}")
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
        logger.info(f"[Talker {self.id}] Closing serial connection on {self.name}")
        self.serial.close()

    def get_id(self) -> int:
        """
        Get the ID of the Talker instance.

        :param self: Instance of the Talker class
        :return: ID of the Talker instance
        :rtype: int
        """
        return self.id
