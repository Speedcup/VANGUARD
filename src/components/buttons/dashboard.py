from interactions import Button, ButtonStyle


class DashboardUpdateButton(Button):
    def __init__(self) -> None:
        super().__init__(
            style=ButtonStyle.PRIMARY,
            label='♻ Update Dashboard',
            custom_id='update_dashboard_button',
        )
