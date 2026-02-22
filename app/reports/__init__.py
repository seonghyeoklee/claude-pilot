"""통합 리포트 패키지"""


def __getattr__(name: str):
    if name == "report_router":
        from app.reports.routes import report_router

        return report_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["report_router"]
