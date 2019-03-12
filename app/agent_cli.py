import textwrap
import typing as t

import click

from app.registry import Registry, RegistryError
import settings


def info(text):
    return click.style(text, fg="cyan")


def get_agent_cli(registry: Registry, *, registry_file: str) -> t.Callable:
    @click.command()
    @click.option("-a", "--agent", type=click.Choice(registry._entries.keys()), required=True)
    @click.option("-y", "--no-user-input", is_flag=True, help="bypass the y/N prompt to run the agent")
    @click.option("--once", is_flag=True, help="run the agent once")
    @click.option("-N", "--dry-run", is_flag=True, help="print agent information then quit without executing")
    @click.option("-q", "--quiet", is_flag=True, help="skip printing agent information and warnings")
    def cli(agent: str, no_user_input: bool, once: bool, dry_run: bool, quiet: bool) -> None:
        try:
            agent_instance = registry.instantiate(agent)
        except RegistryError as ex:
            click.echo(
                f"{click.style('Error:', fg='red')} {ex}\n"
                f"Check the value for key {info(agent)} "
                f"in {info(registry_file)}. "
                f"It is currently set to {info(registry._entries[agent])}.",
                err=True,
            )
            if settings.DEBUG:
                raise
            else:
                click.echo("Enable debug mode for a stack trace.")
                raise click.Abort()

        if not quiet:
            click.echo(f"Loaded {info(type(agent_instance).__name__)} agent from {info(registry._entries[agent])}.")

            click.echo()
            click.echo("Agent help text:")
            click.echo()
            click.echo(textwrap.indent(agent_instance.help(), "    "))
            click.echo()

            if once:
                click.echo("Agent will be run once.")
                click.echo()

            if settings.DEBUG:
                click.echo(
                    f"{click.style('Warning', fg='yellow')}: "
                    "Debug mode is on. Exceptions will not be handled gracefully!"
                )
                click.echo()

        if dry_run:
            return

        if no_user_input or click.confirm("Do you wish to run this agent?"):
            if not no_user_input:
                click.echo()
            agent_instance.run(once=once)

    return cli
