import typer
from pydantic import ValidationError
from .app import ServerApplication, ChatApplication
from .config import Config, setup_logging

app = typer.Typer()


@app.command(help="Start agent and listen for incoming emails.")
def serve(
    config_path: str = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to the YAML config file",
        envvar="CONFIG_FILE",
    )
):
    cfg = Config.from_path(config_path)
    setup_logging(cfg.logging)
    app = ServerApplication(cfg)
    app.run()


@app.command(help="Start agent in inline chat mode. Used for AI prompt testing.")
def chat(
    actor_email: str = typer.Option(
        ..., "--email", "-e", envvar="CHAT_EMAIL", help="Email of chat user"
    ),
    actor_name: str = typer.Option(
        ..., "--name", "-n", envvar="CHAT_USER", help="First and last name of chat user"
    ),
    config_path: str = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to the YAML config file",
        envvar="CONFIG_FILE",
    ),
):
    cfg = Config.from_path(config_path)
    setup_logging(cfg.logging)
    app = ChatApplication(cfg, actor_email, actor_name)
    app.run()


def main():
    try:
        app()
    except ValidationError as e:
        print(format_config_error(e))
        exit(1)


if __name__ == "__main__":
    main()


def format_config_error(e: ValidationError) -> str:
    error_messages = []
    for error in e.errors():
        loc = " -> ".join(str(x) for x in error["loc"])
        msg = error["msg"]
        error_messages.append(f"{loc}: {msg}")
    return "\n".join(error_messages)
