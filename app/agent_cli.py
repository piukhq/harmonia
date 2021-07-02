import textwrap
import typing as t

import click

import settings
from app import db
from app.prometheus import prometheus_thread
from app.registry import NoSuchAgent, Registry, RegistryConfigurationError


def info(text):
    return click.style(text, fg="cyan")


def clean_abort():
    if settings.DEBUG:
        raise
    else:
        click.echo("Enable debug mode for a stack trace.")
        raise click.Abort()


def get_agent_cli(registry: Registry, *, registry_file: str) -> t.Callable:
    @click.command()
    @click.option("-a", "--agent", type=click.Choice(list(registry._entries.keys())), required=True)
    @click.option("-y", "--no-user-input", is_flag=True, help="bypass the y/N prompt to run the agent")
    @click.option("-N", "--dry-run", is_flag=True, help="print agent information then quit without executing")
    @click.option("-q", "--quiet", is_flag=True, help="skip printing agent information and warnings")
    @click.option("--no-prometheus", is_flag=True, help="Run without starting the Prometheus push thread.")
    def cli(agent: str, no_user_input: bool, dry_run: bool, quiet: bool, no_prometheus: bool) -> None:
        try:
            agent_instance = registry.instantiate(agent)
        except NoSuchAgent as ex:
            click.echo(
                f"{click.style('Error:', fg='red')} {ex}\n"
                f"Agent {info(agent)} was not found "
                f"in {info(registry_file)}.",
                err=True,
            )
            clean_abort()
        except RegistryConfigurationError as ex:
            click.echo(
                f"{click.style('Error:', fg='red')} {ex}\n"
                f"Check the value for key {info(agent)} "
                f"in {info(registry_file)}. "
                f"It is currently set to {info(registry._entries[agent])}.",
                err=True,
            )
            clean_abort()

        if not quiet:
            click.echo(f"Loaded {info(type(agent_instance).__name__)} agent from {info(registry._entries[agent])}.")

            click.echo()
            click.echo("Agent help text:")
            click.echo()
            with db.session_scope() as session:
                click.echo(textwrap.indent(agent_instance.help(session=session), "    "))
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

            # intentional double negative since the prometheus flag is set by default
            if not no_prometheus:
                # Start up the Prometheus push thread for pushing metrics
                prometheus_thread.start()
                click.echo("Prometheus push thread started")

            agent_instance.run()

    return cli
