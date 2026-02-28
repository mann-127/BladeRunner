"""Interactive REPL mode for BladeRunner."""

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from rich.console import Console

    INTERACTIVE_AVAILABLE = True
except ImportError:
    INTERACTIVE_AVAILABLE = False

from pathlib import Path


class InteractiveMode:
    """Interactive REPL for continuous conversation."""

    def __init__(self, agent, session_manager=None):
        if not INTERACTIVE_AVAILABLE:
            raise ImportError(
                "Interactive mode requires 'prompt_toolkit' and 'rich' packages"
            )

        self.agent = agent
        self.session_manager = session_manager
        self.console = Console()

        history_file = Path.home() / ".bladerunner" / "history"
        history_file.parent.mkdir(parents=True, exist_ok=True)

        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
        )

        self.active = True
        self.current_session_id = None

    def run(self):
        """Main REPL loop."""
        self.console.print("[bold blue]BladeRunner Interactive Mode[/]")
        self.console.print("Type /help for commands, Ctrl+D to exit\n")

        while self.active:
            try:
                user_input = self.session.prompt("You: ", multiline=False)

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    self.handle_command(user_input)
                    continue

                # Execute with agent
                self.console.print("\n[bold green]Assistant:[/] ")
                result = self.agent.execute(user_input)
                self.console.print(result)
                self.console.print()

            except KeyboardInterrupt:
                continue
            except EOFError:
                self.console.print("\nGoodbye!")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {str(e)}[/]")

    def handle_command(self, command: str):
        """Handle slash commands."""
        cmd = command.lower().strip()

        if cmd == "/help":
            self.show_help()
        elif cmd == "/exit" or cmd == "/quit":
            self.active = False
        elif cmd == "/clear":
            self.agent.clear_history()
            self.console.clear()
            self.console.print("[dim]Conversation cleared[/]")
        elif cmd == "/history":
            self.show_history()
        elif cmd.startswith("/model"):
            parts = cmd.split(maxsplit=1)
            if len(parts) > 1:
                self.agent.set_model(parts[1])
                self.console.print(f"[dim]Switched to model: {parts[1]}[/]")
            else:
                self.console.print(f"[dim]Current model: {self.agent.model}[/]")
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/]")
            self.console.print("[dim]Type /help for available commands[/]")

    def show_help(self):
        """Display help message."""
        help_text = """
[bold]Available Commands:[/]

/help       - Show this help message
/clear      - Clear conversation history
/history    - Show conversation history
/model [name] - Show or switch model
/exit       - Exit interactive mode
        """
        self.console.print(help_text)

    def show_history(self):
        """Show conversation history."""
        if not self.agent.messages:
            self.console.print("[dim]No conversation history[/]")
            return

        self.console.print("\n[bold]Conversation History:[/]\n")
        for msg in self.agent.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                self.console.print(f"[blue]You:[/] {content}")
            elif role == "assistant":
                self.console.print(f"[green]Assistant:[/] {content}")
        self.console.print()
