import os

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent_app.config import AppSettings
from agent_app.core import Agent, Step
from agent_app.interfaces.base import BaseInterface
from agent_app.llm import OpenAICompatibleClient, LLMError
from agent_app.memory import BaseMemory
from agent_app.tools import ToolRegistry


class CLIInterface(BaseInterface):
    def __init__(self, settings: AppSettings, agent: Agent, llm_client: OpenAICompatibleClient, memory: BaseMemory, tools: ToolRegistry) -> None:
        self.settings = settings
        self.agent = agent
        self.llm_client = llm_client
        self.memory = memory
        self.tools = tools

        self.console = Console(width=100)

    async def run(self) -> None:
        if self.settings.model is None:
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
        self.console.print("\n[bold]Главное меню[/bold]")
        self.console.print("1. Чат")
        self.console.print("2. Выбрать модель")
        self.console.print("3. Настройки генерации")
        self.console.print("4. Настройки отображения")
        self.console.print("5. Показать доступные tools")
        self.console.print("0. Выход\n")

    async def _chat_loop(self) -> None:
        last_result = None
        live_steps: list[Step] = []

        while True:
            self._print_header(clear=True)
            await self._show_memory()

            if live_steps and self.settings.show_steps:
                self.console.print("\n[bold]Steps последнего ответа:[/bold]")
                for step in live_steps:
                    self._print_step(step)

            if last_result is not None and self.settings.show_reasoning and last_result.reasoning:
                self.console.print("\n[bold]Reasoning последнего ответа:[/bold]")
                self.console.print(last_result.reasoning)

            self.console.print("\n[bold]Введите сообщение или /q для выхода в меню[/bold]")
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

            self.console.print("\n[bold]Steps последнего ответа:[/bold]")

            async def on_step(step: Step) -> None:
                live_steps.append(step)

                if self.settings.show_steps:
                    self._print_step(step)

            try:
                last_result = await self.agent.run(user_input=user_input, on_step=on_step)
            except LLMError:
                last_result = None

    async def _select_model(self, allow_exit: bool = False) -> bool:
        self.console.print("Загрузка моделей...\n")

        models = await self.llm_client.list_models()

        if not models:
            self.console.print("[red]Модели не найдены[/red]")
            return not allow_exit

        for index, model in enumerate(models, start=1):
            self.console.print(f"{index}. {model}")

        self.console.print("0. Выход" if allow_exit else "0. Назад")

        choice = input("\nВыберите модель: ").strip()

        if choice == "0":
            return False

        try:
            selected_index = int(choice) - 1
            selected_model = models[selected_index]
        except (ValueError, IndexError):
            self.console.print("[red]Неверный выбор[/red]")
            return True

        self.settings.model = selected_model
        self.llm_client.model = selected_model
        await self.memory.clear()

        self.console.print(f"\n[green]Выбрана модель:[/green] {selected_model}")
        return True

    def _generation_settings_menu(self) -> None:
        while True:
            self._print_header(clear=True)

            self.console.print("[bold]Настройки генерации[/bold]\n")
            self.console.print(f"1. Temperature: {self.settings.temperature}")
            self.console.print(f"2. Max tokens: {self.settings.max_tokens}")
            self.console.print("0. Назад\n")

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
            self.settings.temperature = None
            self.agent.temperature = None
            return

        try:
            self.settings.temperature = float(value)
            self.agent.temperature = self.settings.temperature
        except ValueError:
            self.console.print("[red]Неверное значение[/red]")

    def _change_max_tokens(self) -> None:
        value = input("Введите max_tokens или пусто для None: ").strip()

        if not value:
            self.settings.max_tokens = None
            self.agent.max_tokens = None
            return

        try:
            self.settings.max_tokens = int(value)
            self.agent.max_tokens = self.settings.max_tokens
        except ValueError:
            self.console.print("[red]Неверное значение[/red]")

    def _display_settings_menu(self) -> None:
        while True:
            self._print_header(clear=True)

            self.console.print("[bold]Настройки отображения[/bold]\n")
            self.console.print(f"1. Показывать steps: {self.settings.show_steps}")
            self.console.print(f"2. Показывать reasoning: {self.settings.show_reasoning}")
            self.console.print("0. Назад\n")

            choice = input("Выбор: ").strip()

            if choice == "1":
                self.settings.show_steps = not self.settings.show_steps
            elif choice == "2":
                self.settings.show_reasoning = not self.settings.show_reasoning
            elif choice == "0":
                return

    async def _show_memory(self, show_empty_message: bool = True) -> None:
        messages = await self.memory.get_context()

        self.console.print("\n[bold]История диалога:[/bold]")

        if not messages:
            if show_empty_message:
                self.console.print("[dim]Пока пусто[/dim]")

            return

        for message in messages:
            if message.role == "user":
                self._print_user_message(message.content)
            elif message.role == "assistant":
                self._print_agent_message(message.content)

    def _show_tools(self) -> None:
        self.console.print("[bold]Доступные tools:[/bold]\n")

        for name in self.tools.names():
            self.console.print(f"- {name}")

    def _print_header(self, clear: bool = False) -> None:
        if clear:
            self._clear_screen()

        table = Table.grid(expand=True)
        table.add_column(justify="left")
        table.add_column(justify="center")
        table.add_column(justify="right")

        model = self.settings.model or "не выбрана"

        left = Text()
        left.append("LLM Agent CLI\n", style="bold cyan")
        left.append(f"Модель: {model}", style="white")

        center = Text()
        center.append(f"Temp: {self.settings.temperature}\n")
        center.append(f"Tokens: {self.settings.max_tokens}")

        right = Text()
        right.append(f"Steps: {self.settings.show_steps}\n", style="green" if self.settings.show_steps else "red")
        right.append(f"Reasoning: {self.settings.show_reasoning}", style="green" if self.settings.show_reasoning else "red")

        table.add_row(left, center, right)

        self.console.print(
            Panel(
                table,
                border_style="cyan",
            )
        )

    def _print_user_message(self, text: str) -> None:
        self.console.print(
            Panel(
                Text(text),
                title="Вы",
                title_align="left",
                border_style="green",
            )
        )

    def _print_agent_message(self, text: str) -> None:
        self.console.print(
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

        self.console.print(
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