import textwrap

import click

from app.imports.agents import registry


def info(text):
    return click.style(text, fg='cyan')


@click.command()
@click.option('-a', '--agent', type=click.Choice(registry.AGENTS.keys()), required=True)
@click.option('-y', '--no-user-input', is_flag=True, help='bypass the y/N prompt to run the agent')
@click.option('--immediate', is_flag=True, help='run the agent in immediate mode')
@click.option('--debug', is_flag=True, help='run the agent in debug mode')
@click.option('-N', '--dry-run', is_flag=True, help='print agent information then quit without executing')
def cli(agent: str, no_user_input: bool, immediate: bool, debug: bool, dry_run: bool) -> None:
    def show_error(msg: str) -> None:
        click.echo(
            f"{click.style('Error:', fg='red')} {msg}\n"
            f"Check the value for key {info(agent)} "
            f"in {info('app/imports/agents/registry.py')}. "
            f"The format should be {info('module.path.ClassName')}.",
            err=True)
        if debug:
            raise
        else:
            click.echo(f"Run with {info('--debug')} for a stack trace.")
            raise click.Abort()

    try:
        agent_instance = registry.get_agent(agent)
    except registry.InvalidRegistryPathError:
        show_error('Invalid path in registry.')
    except registry.InvalidImportModuleError:
        show_error('Failed to import agent module.')
    except registry.InvalidAgentClassError:
        show_error('Failed to find agent class in module.')

    click.echo(f"Loaded {info(agent_instance.__class__.__name__)} " f"agent from {info(registry.AGENTS[agent])}.")

    click.echo()
    click.echo('Agent help text:')
    click.echo()
    click.echo(textwrap.indent(agent_instance.help(), '    '))
    click.echo()

    if immediate:
        click.echo('Agent will be run in immediate mode.')
        click.echo()

    if debug:
        click.echo(
            f"{click.style('Warning', fg='yellow')}: Debug mode is on. Exceptions will not be handled gracefully!")
        click.echo()

    if dry_run:
        return

    if no_user_input or click.confirm('Do you wish to run this agent?'):
        click.echo()
        agent_instance.run(immediate=immediate, debug=debug)


if __name__ == '__main__':
    cli()
