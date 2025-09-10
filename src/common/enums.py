from enum import Enum


class Colors(int, Enum):
    PRIMARY = 0xFF4654
    SECONDARY = 0x0C1824


class Emoji(str, Enum):
    QUESTIONMARK = '<:icons_questionmark:1275889904483696640>'
    LOCKED = '<:icons_locked:1275889862914080849>'
    WRONG = '<:icons_wrong:1275889761336430713>'
    JOIN = '<:icons_join:1275889849009836082>'
    BAN = '<:icons_ban:1275889713890201620>'
    LEAVE = '<:icons_leave:1275889855649550356>'
    MOD = '<:icons_mod:1275889869926957169>'
    NUMBER_ONE = '<:icons_1:1283516322839400479>'
    NUMBER_TWO = '<:icons_2:1283516328354775121>'
    NUMBER_THREE = '<:icons_3:1283516334063485113>'
    MEGA = '📣'
    QUESTION = '❓'
    APP_STORE = '<:App_Store:1405224683724345405>'

    def __str__(self):
        return self.value
