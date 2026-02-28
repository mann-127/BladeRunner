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
    parser.add_argument("-p", "--prompt", help="User prompt")
    parser.add_argument(
        "--model",
        help=(
            "Model to use (haiku, sonnet, opus | "
            "llama, gemini, mistral [free] | "
            "groq-llama, groq-mixtral [free + fast] | "
            "or full model name)"
        ),
    )

    # Session management
    parser.add_argument("--session", help="Session name or ID")
    parser.add_argument(
        "--continue",
        dest="continue_session",
        action="store_true",
        help="Continue last session",
    )
    parser.add_argument("--resume", help="Resume specific session by ID")
    parser.add_argument(
        "--list-sessions", action="store_true", help="List all sessions"
    )
    parser.add_argument(
        "--new-session",
        action="store_true",
        help="Force create new session (don't resume)",
    )

    # Permissions
    parser.add_argument(
        "--permissions",
        choices=["strict", "standard", "permissive", "none"],
        default="standard",
        help="Permission profile",
    )

    # Interactive mode
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Start interactive REPL mode"
    )

    # Agentic AI features
    parser.add_argument(
        "--no-planning",
        action="store_true",
        help="Disable planning before execution",
    )
    parser.add_argument(
        "--no-reflection",
        action="store_true",
        help="Disable reflection on tool output",
    )
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable automatic retries on errors",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream response tokens (real-time output)",
    )

    # Image support
    parser.add_argument("--image", action="append", help="Attach image file(s)")

    # Skills
    parser.add_argument("--skill", help="Use specific skill")
    parser.add_argument(
        "--list-skills", action="store_true", help="List available skills"
    )

    # Profile (easter egg presets)
    parser.add_argument(
        "--profile",
        choices=["officer-k", "constant-k", "agent-k"],
        help="Use preset profile",
    )

    # Easter egg commands (hidden)
    parser.add_argument(
        "--officer-k",
        dest="easteregg",
        action="store_const",
        const="officer-k",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--constant-k",
        dest="easteregg",
        action="store_const",
        const="constant-k",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--agent-k",
        dest="easteregg",
        action="store_const",
        const="agent-k",
        help=argparse.SUPPRESS,
    )

    # Config
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

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
