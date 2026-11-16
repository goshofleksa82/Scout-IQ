"""Application composition. Domain behavior lives in routers and services."""
from fastapi import FastAPI
from app.api import auth, players, users, entities, history, matches, statistics, imports, analytics, watchlists, reports, admin_data
from app.core.errors import install_error_handlers
from app.core.config import settings
from app.core.operations import OperationalMiddleware
from app.api import health
from app.api import product
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware


def create_app():
    application = FastAPI(title='ScoutIQ', version='1.1.0')
    application.include_router(auth.router)
    application.include_router(users.router)
    application.include_router(players.router)
    application.include_router(entities.router)
    application.include_router(history.router)
    application.include_router(matches.router)
    application.include_router(statistics.router)
    application.include_router(imports.router)
    application.include_router(analytics.router)
    application.include_router(watchlists.router)
    application.include_router(reports.router)
    application.include_router(admin_data.router)
    application.include_router(health.router)
    application.include_router(product.router)
    application.add_middleware(CORSMiddleware,allow_origins=list(settings.allowed_origins),allow_credentials=True,allow_methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type'],expose_headers=['X-Request-ID'])
    if settings.enforce_https: application.add_middleware(HTTPSRedirectMiddleware)
    application.add_middleware(TrustedHostMiddleware,allowed_hosts=list(settings.allowed_hosts))
    application.add_middleware(OperationalMiddleware,hosted=settings.environment in {'staging','production'})
    install_error_handlers(application)
    return application


app = create_app()
