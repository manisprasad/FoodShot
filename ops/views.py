from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, RadioButton, RadioSet


class GrantPremiumModal(ModalScreen[dict[str, int] | None]):
    """Modal dialog to select or enter duration to grant Premium subscription."""

    def __init__(self, user_id: int, username: str):
        super().__init__()
        self.user_id = user_id
        self.username = username

    def compose(self) -> ComposeResult:
        yield Container(
            Label(
                f"Grant Premium to User: [bold]{self.username}[/bold] ({self.user_id})"
            ),
            Label("Select Subscription Duration:"),
            RadioSet(
                RadioButton("10 Minutes (Test)", id="m10"),
                RadioButton("7 Days", value=True, id="d7"),
                RadioButton("30 Days (1 Month)", id="d30"),
                RadioButton("90 Days (3 Months)", id="d90"),
                RadioButton("365 Days (1 Year)", id="d365"),
                RadioButton("Lifetime (9999 Days)", id="d9999"),
                id="duration_radios",
            ),
            Horizontal(
                Button("Grant Premium", variant="success", id="grant_btn"),
                Button("Cancel", variant="error", id="cancel_btn"),
                classes="modal_buttons",
            ),
            id="modal_dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.dismiss(None)
        elif event.button.id == "grant_btn":
            radio_set = self.query_one("#duration_radios", RadioSet)
            selected_id = (
                radio_set.pressed_button.id if radio_set.pressed_button else "d30"
            )
            if selected_id == "m10":
                self.dismiss({"minutes": 10})
            else:
                days_map = {
                    "d7": 7,
                    "d30": 30,
                    "d90": 90,
                    "d365": 365,
                    "d9999": 9999,
                }
                self.dismiss({"days": days_map.get(selected_id, 30)})


class RevokePremiumModal(ModalScreen[bool]):
    """Modal dialog to confirm revoking Premium subscription."""

    def __init__(self, user_id: int, username: str):
        super().__init__()
        self.user_id = user_id
        self.username = username

    def compose(self) -> ComposeResult:
        yield Container(
            Label(
                f"Revoke Premium from [bold]{self.username}[/bold] ({self.user_id})?"
            ),
            Label("This will reset the user's subscription to Free tier immediately."),
            Horizontal(
                Button("Confirm Revoke", variant="error", id="confirm_btn"),
                Button("Cancel", variant="primary", id="cancel_btn"),
                classes="modal_buttons",
            ),
            id="modal_dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.dismiss(False)
        elif event.button.id == "confirm_btn":
            self.dismiss(True)


class SendMessageModal(ModalScreen[str | None]):
    """Modal dialog to type a message to send directly to a Telegram user."""

    def __init__(self, user_id: int, username: str):
        super().__init__()
        self.user_id = user_id
        self.username = username

    def compose(self) -> ComposeResult:
        yield Container(
            Label(
                f"Send Telegram Message to [bold]{self.username}[/bold] ({self.user_id})"
            ),
            Input(placeholder="Type message text here...", id="msg_input"),
            Horizontal(
                Button("Send Message", variant="success", id="send_btn"),
                Button("Cancel", variant="error", id="cancel_btn"),
                classes="modal_buttons",
            ),
            id="modal_dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.dismiss(None)
        elif event.button.id == "send_btn":
            input_widget = self.query_one("#msg_input", Input)
            text = input_widget.value.strip()
            self.dismiss(text if text else None)


class MealHistoryModal(ModalScreen[None]):
    """Modal dialog to inspect user meal history logs."""

    def __init__(self, username: str, meals: list[dict]):
        super().__init__()
        self.username = username
        self.meals = meals

    def compose(self) -> ComposeResult:
        yield Container(
            Label(f"Meal History Inspector for [bold]{self.username}[/bold]"),
            DataTable(id="history_table"),
            Horizontal(
                Button("Close Inspector", variant="primary", id="close_btn"),
                classes="modal_buttons",
            ),
            id="modal_dialog_large",
        )

    def on_mount(self) -> None:
        table = self.query_one("#history_table", DataTable)
        table.add_columns(
            "ID",
            "Date",
            "Dish Name",
            "Portion (g)",
            "Carbs (g)",
            "Kcal",
            "Bolus (U)",
        )
        for m in self.meals:
            table.add_row(
                str(m["id"]),
                str(m["created_at"]),
                str(m["dish_name"]),
                f"{m['portion_g']:.0f}g",
                f"{m['carbs_g']:.1f}g",
                f"{m['kcal']:.0f}",
                f"{m['bolus_dose']:.1f}U" if m["bolus_dose"] is not None else "—",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)
