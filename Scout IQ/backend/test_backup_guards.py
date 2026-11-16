import pytest
from ops.database_backup import restore


def test_restore_requires_named_isolated_scratch_database_before_running_tools(monkeypatch,tmp_path):
    monkeypatch.setenv('DATABASE_URL','postgresql+psycopg://user:secret@localhost/scoutiq')
    for name in ['scoutiq','production','scoutiq_staging','scoutiq_test']:
        with pytest.raises(RuntimeError,match='scratch database'): restore(tmp_path/'missing.dump','postgresql+psycopg://user:secret@localhost/'+name)


def test_restore_cannot_target_its_source_even_when_source_is_a_scratch_db(monkeypatch,tmp_path):
    monkeypatch.setenv('DATABASE_URL','postgresql+psycopg://user:secret@localhost/scoutiq_restore_original')
    with pytest.raises(RuntimeError,match='targets must differ'): restore(tmp_path/'missing.dump','postgresql+psycopg://user:secret@localhost/scoutiq_restore_original')
