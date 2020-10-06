import os
import textwrap
import typing as t

import click

import settings
from app.prometheus import PrometheusPushThread
from app.registry import NoSuchAgent, Registry, RegistryConfigurationError


def info(text):
    return click.style(text, fg="cyan")


def clean_abort():
    if settings.DEBUG:
        raise
    else:
        click.echo("Enable debug mode for a stack trace.")
        raise click.Abort()


def get_prometheus_thread():
    process_id = str(os.getpid())
    prometheus_thread = PrometheusPushThread(
        process_id=process_id,
        prometheus_push_gateway=settings.PROMETHEUS_PUSH_GATEWAY,
        prometheus_job=settings.PROMETHEUS_JOB,
    )
    prometheus_thread.daemon = True

    return prometheus_thread


def get_agent_cli(registry: Registry, *, registry_file: str) -> t.Callable:
    @click.command()
    @click.option("-a", "--agent", type=click.Choice(registry._entries.keys()), required=True)
    @click.option(
        "-y", "--no-user-input", is_flag=True, help="bypass the y/N prompt to run the agent",
    )
    @click.option(
        "-N", "--dry-run", is_flag=True, help="print agent information then quit without executing",
    )
    @click.option(
        "-q", "--quiet", is_flag=True, help="skip printing agent information and warnings",
    )
    def cli(agent: str, no_user_input: bool, dry_run: bool, quiet: bool) -> None:
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
            click.echo(textwrap.indent(agent_instance.help(), "    "))
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
            # Start up the Prometheus push thread for pushing metrics
            prometheus_thread = get_prometheus_thread()
            prometheus_thread.start()
            click.echo("Prometheus push thread started")
            agent_instance.run()

    return cli
