import os

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent_app.config import AppSettings
from agent_app.core import Agent, Step
from agent_app.interfaces.base import BaseInterface
from agent_app.llm import LLMError


class CLIInterface(BaseInterface):
    def __init__(self, agent: Agent) -> None:
        self._agent = agent
        self._console = Console(width=100)

    async def run(self) -> None:
        if self._agent.settings.model is None:
            self._print_header(clear=True)

            should_continue = await self._select_model(allow_exit=True)
            if not should_continue:
                self._clear_screen()
                return

        while True:
            self._print_header(clear=True)
            self._show_main_menu()

            choice = input("Выбор: ").strip()

            if choice == "1":
                await self._chat_loop()
            elif choice == "2":
                self._print_header(clear=True)
                await self._select_model()
            elif choice == "3":
                self._generation_settings_menu()
            elif choice == "4":
                self._display_settings_menu()
            elif choice == "5":
                self._print_header(clear=True)
                self._show_tools()
                self._pause()
            elif choice == "0":
                self._clear_screen()
                break

    def _show_main_menu(self) -> None:
        self._console.print("\n[bold]Главное меню[/bold]")
        self._console.print("1. Чат")
        self._console.print("2. Выбрать модель")
        self._console.print("3. Настройки генерации")
        self._console.print("4. Настройки отображения")
        self._console.print("5. Показать доступные tools")
        self._console.print("0. Выход\n")

    async def _chat_loop(self) -> None:
        last_result = None
        live_steps: list[Step] = []

        while True:
            self._print_header(clear=True)
            await self._show_memory()

            if live_steps and self._agent.settings.show_steps:
                self._console.print("\n[bold]Steps последнего ответа:[/bold]")
                for step in live_steps:
                    self._print_step(step)

            if last_result is not None and self._agent.settings.show_reasoning and last_result.reasoning:
                self._console.print("\n[bold]Reasoning последнего ответа:[/bold]")
                self._console.print(last_result.reasoning)

            self._console.print("\n[bold]Введите сообщение или /q для выхода в меню[/bold]")
            user_input = input("Вы: ").strip()

            if user_input.lower() in {"/exit", "/quit", "/q"}:
                return

            if not user_input:
                continue

            live_steps = []

            self._print_header(clear=True)
            await self._show_memory(show_empty_message=False)
            self._print_user_message(user_input)
            self._print_agent_message("[Думает...]")

            self._console.print("\n[bold]Steps последнего ответа:[/bold]")

            async def on_step(step: Step) -> None:
                live_steps.append(step)

                if self._agent.settings.show_steps:
                    self._print_step(step)

            try:
                last_result = await self._agent.run(user_input=user_input, on_step=on_step)
            except LLMError:
                last_result = None

    async def _select_model(self, allow_exit: bool = False) -> bool:
        self._console.print("Загрузка моделей...\n")

        models = await self._agent.llm_client.list_models()

        if not models:
            self._console.print("[red]Модели не найдены[/red]")
            return not allow_exit

        for index, model in enumerate(models, start=1):
            self._console.print(f"{index}. {model}")

        self._console.print("0. Выход" if allow_exit else "0. Назад")

        choice = input("\nВыберите модель: ").strip()

        if choice == "0":
            return False

        try:
            selected_index = int(choice) - 1
            selected_model = models[selected_index]
        except (ValueError, IndexError):
            self._console.print("[red]Неверный выбор[/red]")
            return True

        self._agent.settings.model = selected_model
        self._agent.llm_client.model = selected_model
        await self._agent.memory.clear()

        self._console.print(f"\n[green]Выбрана модель:[/green] {selected_model}")
        return True

    def _generation_settings_menu(self) -> None:
        while True:
            self._print_header(clear=True)

            self._console.print("[bold]Настройки генерации[/bold]\n")
            self._console.print(f"1. Temperature: {self._agent.settings.temperature}")
            self._console.print(f"2. Max tokens: {self._agent.settings.max_tokens}")
            self._console.print("0. Назад\n")

            choice = input("Выбор: ").strip()

            if choice == "1":
                self._change_temperature()
            elif choice == "2":
                self._change_max_tokens()
            elif choice == "0":
                return

    def _change_temperature(self) -> None:
        value = input("Введите temperature или пусто для None: ").strip()

        if not value:
            self._agent.settings.temperature = None
            self._agent.temperature = None
            return

        try:
            self._agent.settings.temperature = float(value)
            self._agent.temperature = self._agent.settings.temperature
        except ValueError:
            self._console.print("[red]Неверное значение[/red]")

    def _change_max_tokens(self) -> None:
        value = input("Введите max_tokens или пусто для None: ").strip()

        if not value:
            self._agent.settings.max_tokens = None
            self._agent.max_tokens = None
            return

        try:
            self._agent.settings.max_tokens = int(value)
            self._agent.max_tokens = self._agent.settings.max_tokens
        except ValueError:
            self._console.print("[red]Неверное значение[/red]")

    def _display_settings_menu(self) -> None:
        while True:
            self._print_header(clear=True)

            self._console.print("[bold]Настройки отображения[/bold]\n")
            self._console.print(f"1. Показывать steps: {self._agent.settings.show_steps}")
            self._console.print(f"2. Показывать reasoning: {self._agent.settings.show_reasoning}")
            self._console.print("0. Назад\n")

            choice = input("Выбор: ").strip()

            if choice == "1":
                self._agent.settings.show_steps = not self._agent.settings.show_steps
            elif choice == "2":
                self._agent.settings.show_reasoning = not self._agent.settings.show_reasoning
            elif choice == "0":
                return

    async def _show_memory(self, show_empty_message: bool = True) -> None:
        messages = await self._agent.memory.get_context()

        self._console.print("\n[bold]История диалога:[/bold]")

        if not messages:
            if show_empty_message:
                self._console.print("[dim]Пока пусто[/dim]")

            return

        for message in messages:
            if message.role == "user":
                self._print_user_message(message.content)
            elif message.role == "assistant":
                self._print_agent_message(message.content)

    def _show_tools(self) -> None:
        self._console.print("[bold]Доступные tools:[/bold]\n")

        for name in self._agent.tools.names():
            self._console.print(f"- {name}")

    def _print_header(self, clear: bool = False) -> None:
        if clear:
            self._clear_screen()

        table = Table.grid(expand=True)
        table.add_column(justify="left")
        table.add_column(justify="center")
        table.add_column(justify="right")

        model = self._agent.settings.model or "не выбрана"

        left = Text()
        left.append("LLM Agent CLI\n", style="bold cyan")
        left.append(f"Модель: {model}", style="white")

        center = Text()
        center.append(f"Temp: {self._agent.settings.temperature}\n")
        center.append(f"Tokens: {self._agent.settings.max_tokens}")

        right = Text()
        right.append(f"Steps: {self._agent.settings.show_steps}\n", style="green" if self._agent.settings.show_steps else "red")
        right.append(f"Reasoning: {self._agent.settings.show_reasoning}", style="green" if self._agent.settings.show_reasoning else "red")

        table.add_row(left, center, right)

        self._console.print(
            Panel(
                table,
                border_style="cyan",
            )
        )

    def _print_user_message(self, text: str) -> None:
        self._console.print(
            Panel(
                Text(text),
                title="Вы",
                title_align="left",
                border_style="green",
            )
        )

    def _print_agent_message(self, text: str) -> None:
        self._console.print(
            Panel(
                Text(text),
                title="Агент",
                title_align="left",
                border_style="cyan",
            )
        )

    def _print_step(self, step: Step) -> None:
        text = step.message

        if step.meta:
            meta_lines = []

            for key, value in step.meta.items():
                value_text = str(value)

                if len(value_text) > 120:
                    value_text = value_text[:120] + "..."

                meta_lines.append(f"{key}: {value_text}")

            text += "\n[dim]" + "\n".join(meta_lines) + "[/dim]"

        self._console.print(
            Panel(
                Text.from_markup(text),
                title=step.name,
                title_align="left",
                border_style="dim",
            )
        )

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def _pause(self) -> None:
        input("\nНажмите Enter, чтобы продолжить...")