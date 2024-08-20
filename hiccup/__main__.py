import typer
import uvicorn
import asyncio


cli_app = typer.Typer()


@cli_app.command(name="dev")
def dev_server(
    host: str = typer.Argument("127.0.0.1", help="Development Server Host"),
    port: int = typer.Argument(1440, help="Development Server port"),
    auto_reload: bool = typer.Argument(True, help="Auto reload server"),
):
    async def server_func() -> None:
        config = uvicorn.Config("hiccup:hiccup_app", host=host, port=port, log_level="info", reload=auto_reload)
        server = uvicorn.Server(config)
        await server.serve()
    asyncio.run(server_func())


@cli_app.command(name="test")
def test():
    print("test")


if __name__ == "__main__":
    cli_app()
