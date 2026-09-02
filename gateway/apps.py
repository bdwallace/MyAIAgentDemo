from django.apps import AppConfig


class GatewayConfig(AppConfig):
    name = "gateway"
    verbose_name = "Agent Gateway"

    def ready(self) -> None:
        import sys

        if any(cmd in sys.argv for cmd in ("check", "migrate", "makemigrations", "shell")):
            return
        from gateway.boot import ensure_ready

        ensure_ready()
