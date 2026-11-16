"""Validated environment configuration. Secrets never appear in its repr."""
from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import load_dotenv
from urllib.parse import urlsplit
from app.core.urls import normalize_database_url


@dataclass(frozen=True)
class Settings:
    database_url: str = field(repr=False)
    jwt_secret: str = field(repr=False)
    jwt_algorithm: str
    access_minutes: int
    refresh_days: int
    environment: str
    allowed_origins: tuple[str, ...]
    allowed_hosts: tuple[str, ...] = ('127.0.0.1','localhost','testserver')
    enforce_https: bool = False


def load_settings():
    load_dotenv(Path(__file__).resolve().parents[2]/'.env')
    database_url = os.getenv('DATABASE_URL')
    if not database_url: raise RuntimeError('DATABASE_URL is not configured')
    database_url=normalize_database_url(database_url)
    secret = os.getenv('JWT_SECRET_KEY')
    if not secret or len(secret) < 32: raise RuntimeError('JWT_SECRET_KEY must contain at least 32 characters')
    algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
    if algorithm != 'HS256': raise RuntimeError('Unsupported JWT algorithm')
    try:
        access = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '15'))
    except ValueError:
        raise RuntimeError('Invalid token expiration configuration') from None
    if not 1 <= access <= 60: raise RuntimeError('Invalid token expiration configuration')
    try:
        refresh = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '30'))
    except ValueError:
        raise RuntimeError('Invalid refresh expiration configuration') from None
    if not 1 <= refresh <= 90: raise RuntimeError('Invalid refresh expiration configuration')
    origins = tuple(value.strip() for value in os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if value.strip())
    if '*' in origins: raise RuntimeError('ALLOWED_ORIGINS must list explicit origins')
    environment=os.getenv('ENVIRONMENT','development')
    if environment not in {'development','test','staging','production'}: raise RuntimeError('Invalid ENVIRONMENT')
    hosted=environment in {'staging','production'}
    if hosted and (not os.getenv('ALLOWED_ORIGINS') or any(urlsplit(origin).scheme!='https' or urlsplit(origin).path not in ('','/') or not urlsplit(origin).netloc for origin in origins)):
        raise RuntimeError('Hosted environments require explicit HTTPS ALLOWED_ORIGINS')
    hosts=tuple(value.strip() for value in os.getenv('ALLOWED_HOSTS','localhost,127.0.0.1,testserver' if not hosted else 'localhost,127.0.0.1').split(',') if value.strip())
    external=os.getenv('PUBLIC_HOSTNAME')
    if external: hosts=(*hosts,external)
    if not hosts or any('*' in host or '/' in host or ':' in host for host in hosts): raise RuntimeError('ALLOWED_HOSTS must list explicit hostnames')
    enforce=os.getenv('ENFORCE_HTTPS','false').lower()
    if enforce not in {'true','false'}: raise RuntimeError('ENFORCE_HTTPS must be true or false')
    return Settings(database_url, secret, algorithm, access, refresh, environment, origins,hosts,enforce=='true')


settings = load_settings()
