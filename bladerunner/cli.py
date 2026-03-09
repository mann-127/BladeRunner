"""Command-line interface for BladeRunner."""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from .config import Config
from .agent import Agent
from .sessions import SessionManager
from . import __version__, __codename__, __aliases__
from .interactive import InteractiveMode


class VersionAction(argparse.Action):
    """Custom version action with verbose support."""

    def __call__(self, parser, namespace, values, option_string=None):
        verbose = getattr(namespace, "verbose", False)
        if verbose:
            print(f"BladeRunner {__version__}")
            print(f"Designation: {__codename__}")
            print(f"Also known as: {', '.join(__aliases__)}")
        else:
            print(f"BladeRunner {__version__} ({__codename__})")
        parser.exit()


def main():
    """Main entry point."""
    # Load environment variables from .env if present.
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="BladeRunner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Verbose flag (for extended version info)
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output (use with --version for extended info)",
    )

    # Version
    parser.add_argument(
        "--version",
        action=VersionAction,
        nargs=0,
        help="Show version information",
    )

    # Core arguments
    core_group = parser.add_argument_group(
        "Core", "Essential arguments for running BladeRunner."
    )
    core_group.add_argument(
        "-p", "--prompt", help="User prompt to execute non-interactively."
    )
    core_group.add_argument(
        "-i", "--interactive", action="store_true", help="Start interactive REPL mode."
    )
    core_group.add_argument(
        "--model",
        help=(
            "Model to use (haiku, sonnet, opus | "
            "llama, gemini, mistral [free] | "
            "groq-llama, groq-mixtral [free + fast] | "
            "or full model name)."
        ),
    )

    # Session management
    session_group = parser.add_argument_group(
        "Session Management", "Control conversation history and context."
    )
    session_group.add_argument("--session", help="Session name or ID to use.")
    session_group.add_argument(
        "--continue",
        dest="continue_session",
        action="store_true",
        help="Continue the last session.",
    )
    session_group.add_argument("--resume", help="Resume a specific session by ID.")
    session_group.add_argument(
        "--list-sessions", action="store_true", help="List all available sessions."
    )
    session_group.add_argument(
        "--new-session",
        action="store_true",
        help="Force the creation of a new session.",
    )

    # Agentic features & skills
    agentic_group = parser.add_argument_group(
        "Agentic Features", "Customize the agent's behavior and capabilities."
    )
    agentic_group.add_argument(
        "--image", action="append", help="Attach one or more image files to the prompt."
    )
    agentic_group.add_argument("--skill", help="Apply a specific skill to the prompt.")
    agentic_group.add_argument(
        "--list-skills", action="store_true", help="List all available skills."
    )
    agentic_group.add_argument(
        "--stream",
        action="store_true",
        help="Stream response tokens for real-time output.",
    )
    agentic_group.add_argument(
        "--no-planning",
        action="store_true",
        help="Disable planning before execution.",
    )
    agentic_group.add_argument(
        "--no-reflection",
        action="store_true",
        help="Disable reflection on tool output.",
    )
    agentic_group.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable automatic retries on tool errors.",
    )

    # Configuration & permissions
    config_group = parser.add_argument_group(
        "Configuration", "Fine-tune security, models, and system settings."
    )
    config_group.add_argument(
        "--permissions",
        choices=["strict", "standard", "permissive", "none"],
        default="standard",
        help="Set the permission profile for tool execution.",
    )
    config_group.add_argument("--config", help="Path to a custom YAML config file.")
    config_group.add_argument(
        "--debug", action="store_true", help="Enable debug logging for detailed output."
    )

    # Profiles (easter egg presets)
    profile_group = parser.add_argument_group(
        "Profiles", "Use one of the preset agent profiles."
    )
    profile_group.add_argument(
        "--profile",
        choices=["officer-k", "constant-k", "agent-k"],
        help="Use a preset profile for the agent.",
    )

    args = parser.parse_args()

    # Load configuration
    config_path = Path(args.config) if args.config else None
    config = Config(config_path)

    # Handle --list-sessions
    if args.list_sessions:
        session_manager = SessionManager()
        sessions = session_manager.list_sessions()

        if not sessions:
            print("No sessions found")
            return

        print("Available sessions:")
        for session in sessions:
            print(
                f"  {session['id']}: {session['message_count']} messages "
                f"(updated: {session['updated']})"
            )
        return

    # Handle --list-skills
    if args.list_skills:
        from .skills import SkillManager

        skill_manager = SkillManager()
        skills = skill_manager.list_skills()

        if not skills:
            print("No skills found")
            return

        print("Available skills:")
        for skill in skills:
            print(f"  {skill['name']}: {skill['description']}")
        return

    # Determine model
    model = args.model or config.get("model", "haiku")

    # Determine permission profile
    use_permissions = args.permissions != "none"
    permission_profile = args.permissions if use_permissions else "permissive"

    # Determine session
    session_id = None
    if not args.new_session:
        if args.continue_session:
            # Get most recent session
            session_manager = SessionManager()
            session_id = session_manager.get_latest_session()
            if not session_id:
                print(
                    "No previous session found, creating new session", file=sys.stderr
                )
        elif args.resume:
            session_id = args.resume
        elif args.session:
            session_id = args.session

    # Create session if needed
    if not session_id and config.get("sessions.enabled", True) and not args.interactive:
        session_manager = SessionManager()
        session_id = session_manager.create_session(args.session)
        print(f"Created session: {session_id}", file=sys.stderr)

    # Initialize agent
    agent = Agent(
        config=config,
        model=model,
        use_permissions=use_permissions,
        permission_profile=permission_profile,
        session_id=session_id,
    )

    # Configure agentic AI features
    agent.enable_planning = not args.no_planning
    agent.enable_reflection = not args.no_reflection
    agent.enable_retry = not args.no_retry
    agent.enable_streaming = args.stream

    # Load session history if resuming
    if session_id and not args.new_session:
        agent.load_session(session_id)
        if agent.messages:
            print(
                f"Resumed session: {session_id} ({len(agent.messages)} messages)",
                file=sys.stderr,
            )

    # Interactive mode
    if args.interactive:
        try:
            interactive = InteractiveMode(agent, agent.session_manager)
            interactive.run()
        except ImportError:
            print(
                "Error: Interactive mode requires 'prompt_toolkit' and 'rich' packages"
            )
            print("Install with: pip install prompt_toolkit rich")
            sys.exit(1)
        return

    # Check for prompt
    if not args.prompt:
        parser.error(
            "the following arguments are required: -p/--prompt (or use --interactive)"
        )

    # Execute agent
    result = agent.execute(args.prompt, use_streaming=args.stream)
    print(result)


if __name__ == "__main__":
    main()
