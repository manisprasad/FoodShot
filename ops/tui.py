from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Input, Label

from ops import actions
from ops.views import (
    GrantPremiumModal,
    MealHistoryModal,
    RevokePremiumModal,
    SendMessageModal,
)

TUI_CSS = """
Screen {
    layout: vertical;
    background: $surface;
}

#search_input {
    margin: 1 1 0 1;
}

#status_label {
    height: 1;
    margin: 0 1 1 1;
    color: $text-muted;
}

DataTable {
    height: 1fr;
    border: solid $primary;
    margin: 0 1;
}

#modal_dialog {
    padding: 1 2;
    width: 60;
    height: 20;
    border: thick $background 80%;
    background: $surface;
}

#modal_dialog_large {
    padding: 1 2;
    width: 85;
    height: 25;
    border: thick $background 80%;
    background: $surface;
}

.modal_buttons {
    height: 3;
    align: center middle;
    margin-top: 1;
}

Button {
    margin: 0 1;
}
"""


class OpsConsoleApp(App):
    """FoodShot Operations TUI Console Application."""

    TITLE = "📸 FoodShot Operations Console (ops)"
    SUB_TITLE = "User Management & Subscription Control"
    CSS = TUI_CSS

    BINDINGS = [
        Binding("g", "grant_premium", "Grant Premium", show=True),
        Binding("r", "revoke_premium", "Revoke Premium", show=True),
        Binding("m", "send_message", "Message User", show=True),
        Binding("h", "view_history", "Meal History", show=True),
        Binding("f5", "refresh_data", "Refresh DB", show=True),
        Binding("q", "quit", "Quit Console", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.all_users: list[actions.UserOpRow] = []
        self.filtered_users: list[actions.UserOpRow] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Input(
            placeholder="🔍 Search user by @username or Telegram ID...",
            id="search_input",
        )
        yield Label("Loading data from database...", id="status_label")
        yield DataTable(id="users_table")
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one("#users_table", DataTable)
        table.cursor_type = "row"
        table.add_columns(
            "Telegram ID",
            "Username",
            "Language",
            "Diabetes Mode",
            "Subscription Status",
            "Premium Until",
            "Total Meals",
            "Registered",
        )
        await self.action_refresh_data()

    async def action_refresh_data(self) -> None:
        status_label = self.query_one("#status_label", Label)
        status_label.update("Fetching users from PostgreSQL database...")

        try:
            self.all_users = await actions.fetch_ops_users()
            self._apply_filter()
            status_label.update(
                f"Total Users: {len(self.all_users)} | Active Premium: {sum(1 for u in self.all_users if u.is_premium)}"
            )
        except Exception as e:
            status_label.update(f"❌ Error loading DB records: {e}")

    def _apply_filter(self) -> None:
        search_term = self.query_one("#search_input", Input).value.strip().lower()
        if search_term.startswith("@"):
            search_term = search_term[1:]

        if not search_term:
            self.filtered_users = list(self.all_users)
        else:
            self.filtered_users = [
                u
                for u in self.all_users
                if search_term in str(u.id) or search_term in u.username.lower()
            ]

        self._populate_table()

    def _populate_table(self) -> None:
        table = self.query_one("#users_table", DataTable)
        table.clear()
        for u in self.filtered_users:
            status_str = "💎 PREMIUM" if u.is_premium else "🆓 FREE"
            until_str = (
                u.premium_until.strftime("%Y-%m-%d") if u.premium_until else "—"
            )
            reg_str = u.created_at.strftime("%Y-%m-%d") if u.created_at else "—"
            table.add_row(
                str(u.id),
                f"@{u.username}" if u.username != "—" else "—",
                u.language.upper(),
                "✅ Enabled" if u.diabetes_mode else "❌ Disabled",
                status_str,
                until_str,
                str(u.total_meals),
                reg_str,
                key=str(u.id),
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search_input":
            self._apply_filter()

    def get_selected_user(self) -> actions.UserOpRow | None:
        table = self.query_one("#users_table", DataTable)
        if table.cursor_row is None or table.cursor_row >= len(self.filtered_users):
            return None
        return self.filtered_users[table.cursor_row]

    async def action_grant_premium(self) -> None:
        user = self.get_selected_user()
        if not user:
            return

        def handle_result(days: int | None) -> None:
            if days is not None:
                self.run_worker(self._do_grant_premium(user.id, days))

        self.push_screen(GrantPremiumModal(user.id, user.username), handle_result)

    async def _do_grant_premium(self, user_id: int, days: int) -> None:
        success = await actions.op_grant_premium(user_id, days)
        if success:
            self.notify(f"Granted Premium for {days} days to user {user_id}!")
            await self.action_refresh_data()

    async def action_revoke_premium(self) -> None:
        user = self.get_selected_user()
        if not user:
            return

        def handle_result(confirm: bool) -> None:
            if confirm:
                self.run_worker(self._do_revoke_premium(user.id))

        self.push_screen(RevokePremiumModal(user.id, user.username), handle_result)

    async def _do_revoke_premium(self, user_id: int) -> None:
        success = await actions.op_revoke_premium(user_id)
        if success:
            self.notify(f"Revoked Premium for user {user_id}!")
            await self.action_refresh_data()

    async def action_send_message(self) -> None:
        user = self.get_selected_user()
        if not user:
            return

        def handle_result(text: str | None) -> None:
            if text:
                self.run_worker(self._do_send_message(user.id, text))

        self.push_screen(SendMessageModal(user.id, user.username), handle_result)

    async def _do_send_message(self, user_id: int, text: str) -> None:
        success = await actions.op_send_message(user_id, text)
        if success:
            self.notify(f"Message sent to Telegram chat {user_id}!")
        else:
            self.notify(f"Failed to send message to {user_id}", severity="error")

    async def action_view_history(self) -> None:
        user = self.get_selected_user()
        if not user:
            return

        meals = await actions.fetch_user_history(user.id)
        self.push_screen(MealHistoryModal(user.username, meals))
