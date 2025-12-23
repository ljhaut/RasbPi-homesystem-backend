from controllers.talker import Talker
from core.config import app_settings
from core.logging_config import setup_logger

logger = setup_logger()


class PicoController:
    """
    Controller for managing two Talker instances connected to Pico devices.
    Provides methods to turn pins on/off and manage their states.
    """

    def __init__(self):
        """
        Initialize the PicoController with two Talker instances.

        :param self: Instance of the PicoController class
        """
        self.talker1 = Talker(app_settings.PICO1_PATH, id=1)
        self.talker2 = Talker(app_settings.PICO2_PATH, id=2)
        self.talkers = {
            self.talker1.get_id(): self.talker1,
            self.talker2.get_id(): self.talker2,
        }
        self.pin_states: dict[int, dict[int, bool]] = {
            self.talker1.get_id(): {pin: False for pin in range(1, 9)},
            self.talker2.get_id(): {pin: False for pin in range(1, 9)},
        }
        logger.info("PicoController initialized with two Talker instances.")

    async def turn_on_pin(self, talker_id: int, pin: int):
        """
        Turn on a specific pin on a specific talker.

        :param self: Instance of the PicoController class
        :param talker_id: ID of the Talker instance
        :type talker_id: int
        :param pin: Pin number to turn on
        :type pin: int
        """
        try:
            response = self.talkers[talker_id].send_to_pico(f"turn_on_pin({pin})")
            self.pin_states[talker_id][pin] = True
            logger.info(
                f"Turned ON pin {pin} on talker {talker_id}. Response: {response}"
            )
        except Exception as e:
            logger.error(f"Error turning ON pin {pin} on talker {talker_id}: {e}")
            raise

    async def turn_off_pin(self, talker_id: int, pin: int):
        """
        Turn off a specific pin on a specific talker.

        :param self: Instance of the PicoController class
        :param talker_id: ID of the Talker instance
        :type talker_id: int
        :param pin: Pin number to turn off
        :type pin: int
        """
        try:
            response = self.talkers[talker_id].send_to_pico(f"turn_off_pin({pin})")
            self.pin_states[talker_id][pin] = False
            logger.info(
                f"Turned OFF pin {pin} on talker {talker_id}. Response: {response}"
            )
        except Exception as e:
            logger.error(f"Error turning OFF pin {pin} on talker {talker_id}: {e}")
            raise

    async def get_pin_state(self, talker_id: int, pin: int) -> bool:
        """
        Get the current state of a specific pin on a specific talker.

        :param self: Instance of the PicoController class
        :param talker_id: ID of the Talker instance
        :type talker_id: int
        :param pin: Pin number to check
        :type pin: int
        :return: Current state of the pin (True for ON, False for OFF)
        :rtype: bool
        """
        return self.pin_states.get((talker_id, pin), False)

    async def turn_on_all_pins(self, talker_id: int):
        """
        Turn on all pins on a specific talker.

        :param self: Instance of the PicoController class
        :param talker_id: ID of the Talker instance
        :type talker_id: int
        """
        for pin in range(1, 9):
            if not await self.get_pin_state(talker_id, pin):
                await self.turn_on_pin(talker_id, pin)
        logger.info(f"Turned ON all pins on talker {talker_id}.")

    async def turn_off_all_pins(self, talker_id: int):
        """
        Turn off all pins on a specific talker.

        :param self: Instance of the PicoController class
        :param talker_id: ID of the Talker instance
        :type talker_id: int
        """
        for pin in range(1, 9):
            if await self.get_pin_state(talker_id, pin):
                await self.turn_off_pin(talker_id, pin)
        logger.info(f"Turned OFF all pins on talker {talker_id}.")

    async def clean_up(self):
        """
        Clean up by turning off all pins and closing serial connections.

        :param self: Instance of the PicoController class
        """
        for id, talker in self.talkers.items():
            await self.turn_off_all_pins(id)
            talker.close_connection()
        logger.info("Closed all Talker serial connections.")
