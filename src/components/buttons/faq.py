from interactions import ActionRow, Button, ButtonStyle


class FaqCreateButton(Button):
    def __init__(self) -> None:
        super().__init__(
            style=ButtonStyle.PRIMARY,
            label='Create faq',
            custom_id='create_faq_button',
        )


class FaqCreateActionButton(ActionRow):
    def __init__(self) -> None:
        super().__init__(
            Button(
                style=ButtonStyle.SUCCESS,
                label='Yes',
                custom_id='yes_create_faq_button',
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label='Fix',
                custom_id='fix_create_faq_button',
            ),
            Button(
                style=ButtonStyle.DANGER,
                label='No',
                custom_id='no_create_faq_button',
            ),
        )


class FaqEditActionButton(ActionRow):
    def __init__(self) -> None:
        super().__init__(
            Button(
                style=ButtonStyle.SUCCESS,
                label='Edit',
                custom_id='start_edit_faq_button',
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label='Cancel',
                custom_id='cancel_edit_faq_button',
            ),
            Button(
                style=ButtonStyle.DANGER,
                label='Delete',
                custom_id='delete_faq_button',
            ),
        )
