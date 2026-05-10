"""Command-line interface for BladeRunner."""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from . import __codename__, __version__
from .agent import Agent
from .config import Config
from .logging_config import configure_logging
from .sessions import SessionManager


class _VersionAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        verbose = getattr(namespace, "verbose", False)
        if verbose:
            print(f"BladeRunner {__version__} — {__codename__}")
        else:
            print(f"BladeRunner {__version__}")
        parser.exit()


def _build_prompt(prompt, image_paths):
    if not image_paths:
        return prompt
    lines = [prompt, "", "Attached image paths:"]
    lines.extend(f"- {p}" for p in image_paths)
    lines.append("Use ReadImage on relevant paths before answering when visual context is needed.")
    return "\n".join(lines)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="bladerunner",
        description="BladeRunner — autonomous coding agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--version", action=_VersionAction, nargs=0, help="Show version")

    # Prompt (positional or -p)
    parser.add_argument("prompt", nargs="?", help="Task to execute")
    parser.add_argument("-p", dest="prompt_flag", help=argparse.SUPPRESS)

    # Model
    parser.add_argument(
        "--model",
        help=("Model alias (gemma, llama-70b, qwen3-coder, gpt-oss-20b, groq-llama, groq-mixtral) or full model name"),
    )

    # Session flags
    parser.add_argument("--session", help="Session name or ID")
    parser.add_argument(
        "--continue",
        dest="continue_session",
        action="store_true",
        help="Continue the most recent session",
    )
    parser.add_argument("--resume", help="Resume a specific session by ID")
    parser.add_argument(
        "--new-session",
        action="store_true",
        help="Force a new session",
    )
    parser.add_argument("--list-sessions", action="store_true", help="List saved sessions")

    # Features
    parser.add_argument("--image", action="append", default=[], help="Attach image file(s) to prompt")
    parser.add_argument("--stream", action="store_true", help="Stream response tokens")
    parser.add_argument(
        "--permissions",
        choices=["strict", "standard", "permissive", "none"],
        default="standard",
        help="Permission profile for tool execution (default: standard)",
    )

    # Config / debug
    parser.add_argument("--config", help="Path to custom YAML config file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Blade Runner easter-egg profiles (hidden)
    parser.add_argument("--officer-k", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--constant-k", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--agent-k", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Resolve positional vs -p prompt
    prompt_text = args.prompt or args.prompt_flag

    # Easter-egg profiles set the permissions profile
    if args.officer_k:
        args.permissions = "strict"
    elif args.constant_k:
        args.permissions = "standard"
    elif args.agent_k:
        args.permissions = "permissive"

    # Load config
    config_path = Path(args.config) if args.config else None
    config = Config(config_path)

    if args.debug:
        config.config["debug"] = True
        configure_logging(config, service_name="bladerunner.cli")

    # --list-sessions
    if args.list_sessions:
        sessions = SessionManager().list_sessions()
        if not sessions:
            print("No sessions found")
            return
        print("Saved sessions:")
        for s in sessions:
            print(f"  {s['id']}: {s['message_count']} messages (updated: {s['updated']})")
        return

    if not prompt_text:
        parser.error("a prompt is required (positional or -p)")

    # Resolve session
    session_id = None
    if not args.new_session:
        if args.continue_session:
            session_id = SessionManager().get_latest_session()
            if not session_id:
                print("No previous session found; creating new one", file=sys.stderr)
        elif args.resume:
            session_id = args.resume
        elif args.session:
            session_id = args.session

    if not session_id and config.get("sessions.enabled", True):
        session_id = SessionManager().create_session(args.session)
        print(f"Session: {session_id}", file=sys.stderr)

    # Build agent
    use_permissions = args.permissions != "none"
    profile = args.permissions if use_permissions else "permissive"

    agent = Agent(
        config=config,
        model=args.model or config.get("model", "gemma"),
        use_permissions=use_permissions,
        permission_profile=profile,
        session_id=session_id,
    )

    # Load history if resuming
    if session_id and not args.new_session:
        agent.load_session(session_id)
        if agent.messages:
            print(
                f"Resumed session {session_id} ({len(agent.messages)} messages)",
                file=sys.stderr,
            )

    prepared = _build_prompt(prompt_text, args.image)
    result = agent.execute(prepared, use_streaming=args.stream)
    print(result)


if __name__ == "__main__":
    main()
