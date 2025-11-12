from controllers.talker import Talker
from core.config import app_settings
from core.logging_config import setup_logger

logger = setup_logger()


class PicoController:
    """Interface for controlling Raspberry Pi Pico I/O pins"""

    def __init__(self):
        self.talker1 = Talker(app_settings.PICO1_PATH)
        self.talker2 = Talker(app_settings.PICO2_PATH)
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
        """Turn on a specific pin on a specific talker"""
        try:
            self.talkers[talker_id].send_to_pico(f"turn_on_pin({pin})")
            self.pin_states[talker_id][pin] = True
            logger.info(f"Turned ON pin {pin} on talker {talker_id}.")
        except Exception as e:
            logger.error(f"Error turning ON pin {pin} on talker {talker_id}: {e}")
            raise

    async def turn_off_pin(self, talker_id: int, pin: int):
        """Turn off a specific pin on a specific talker"""
        try:
            self.talkers[talker_id].send_to_pico(f"turn_off_pin({pin})")
            self.pin_states[talker_id][pin] = False
            logger.info(f"Turned OFF pin {pin} on talker {talker_id}.")
        except Exception as e:
            logger.error(f"Error turning OFF pin {pin} on talker {talker_id}: {e}")
            raise

    async def get_pin_state(self, talker_id: int, pin: int) -> bool:
        """Get current state of a pin on a specific talker"""
        return self.pin_states.get((talker_id, pin), False)

    async def turn_on_all_pins(self, talker_id: int):
        """Turn on all pins on a specific talker"""
        for pin in range(1, 9):
            if not await self.get_pin_state(talker_id, pin):
                await self.turn_on_pin(talker_id, pin)
        logger.info(f"Turned ON all pins on talker {talker_id}.")

    async def turn_off_all_pins(self, talker_id: int):
        """Turn off all pins on a specific talker"""
        for pin in range(1, 9):
            if await self.get_pin_state(talker_id, pin):
                await self.turn_off_pin(talker_id, pin)
        logger.info(f"Turned OFF all pins on talker {talker_id}.")

    async def clean_up(self):
        """Close serial connections"""
        for id, talker in self.talkers.items():
            await self.turn_off_all_pins(id)
            talker.close_connection()
        logger.info("Closed all Talker serial connections.")
