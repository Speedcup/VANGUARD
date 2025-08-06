import re
from typing import Pattern

VALPAW_LOGO: str = 'https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/4c/6f/df/4c6fdff2-397b-2512-9c96-345ebe20cbd3/AppIcon-0-1x_U007ephone-0-0-85-220-0.png/512x512bb.jpg'

EDIT_FAQ_MODAL_CUSTOM_ID_PATTERN: Pattern[str] = re.compile(
    r"edit_faq_modal:([A-Za-z0-9!@#$%^&*()_\-+=\[\]{};:'\",.<>?/\\|`~]+)"
)
