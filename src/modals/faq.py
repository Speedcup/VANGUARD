from interactions import Modal, ParagraphText, ShortText


class FaqCreateModal(Modal):
    def __init__(
        self, id_value: str = None, title_value: str = None, description_value: str = None
    ):
        self.id_value = id_value
        self.title_value = title_value
        self.description_value = description_value
        super().__init__(
            ShortText(
                label='ID',
                value=self.id_value,
                min_length=3,
                max_length=40,
                custom_id='id_faq',
            ),
            ShortText(
                label='Title',
                value=self.title_value,
                min_length=20,
                max_length=256,
                custom_id='title',
            ),
            ParagraphText(
                label='Description',
                value=self.description_value,
                min_length=20,
                max_length=4000,
                custom_id='description',
            ),
            title='Create new faq',
            custom_id='create_faq_modal',
        )


class FaqEditModal(Modal):
    def __init__(self, id_value: str, title_value: str, description_value: str):
        self.id_value = id_value
        self.title_value = title_value
        self.description_value = description_value
        super().__init__(
            ShortText(
                label='Title',
                value=self.title_value,
                min_length=20,
                max_length=256,
                custom_id='title',
            ),
            ParagraphText(
                label='Description',
                value=self.description_value,
                min_length=20,
                max_length=4000,
                custom_id='description',
            ),
            title=f'Edit FAQ: {self.id_value}',
            custom_id=f'edit_faq_modal:{self.id_value}',
        )
