
import os
import sqlite3
import pytest
from datetime import datetime
from core.historico import GerenciadorHistorico

DB_PATH = "test_historico_unit.db"

def cleanup_db(path):
    for f in [path, path + "-wal", path + "-shm"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass

@pytest.fixture
def gerenciador():
    cleanup_db(DB_PATH)
    gh = GerenciadorHistorico(DB_PATH)
    yield gh
    cleanup_db(DB_PATH)

def test_wal_mode_enabled(gerenciador):
    """Verifica se o modo WAL foi ativado."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.upper() == "WAL"

def test_salvar_e_listar(gerenciador):
    """Verifica salvamento e listagem de dados."""
    id1 = gerenciador.salvar("bruto1", "polido1", 1.5)
    id2 = gerenciador.salvar("bruto2", "polido2", 2.5)

    assert id1 is not None
    assert id2 is not None

    registros = gerenciador.listar()
    assert len(registros) == 2
    assert registros[0].texto_bruto == "bruto2" # Order DESC
    assert registros[1].texto_bruto == "bruto1"

def test_salvar_synchronous_pragma(gerenciador):
    """
    Verifica se o PRAGMA synchronous é executado.
    Como PRAGMA synchronous não persiste, não podemos verificar o estado global.
    Mas podemos verificar se salvar() roda sem erro.
    """
    id_reg = gerenciador.salvar("teste", "teste", 1.0)
    assert id_reg > 0

def test_buscar(gerenciador):
    """Verifica busca de transcrições."""
    gerenciador.salvar("abacaxi", "fruta", 1.0)
    gerenciador.salvar("carro", "veiculo", 1.0)

    res = gerenciador.buscar("fruta")
    assert len(res) == 1
    assert res[0].texto_polido == "fruta"

    res = gerenciador.buscar("abacaxi")
    assert len(res) == 1
    assert res[0].texto_bruto == "abacaxi"

def test_excluir(gerenciador):
    """Verifica exclusão."""
    id1 = gerenciador.salvar("t1", "p1", 1.0)
    gerenciador.excluir_por_id(id1)
    assert gerenciador.contar() == 0
