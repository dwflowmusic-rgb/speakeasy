# -*- coding: utf-8 -*-
"""
Gerenciador de Histórico SQLite do VoiceFlow Transcriber.

Persiste todas transcrições em banco SQLite local, garantindo que
nenhum dado seja perdido independente de falhas em outras camadas.

Localização: %APPDATA%/VoiceFlow/historico.db
"""

import os
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

from core.logger import obter_logger

logger = obter_logger('historico')


@dataclass
class RegistroTranscricao:
    """Representa uma transcrição salva no histórico."""
    id: int
    timestamp: datetime
    texto_bruto: str
    texto_polido: str
    duracao_segundos: float
    
    @property
    def preview(self) -> str:
        """Retorna preview de 50 caracteres do texto polido."""
        if len(self.texto_polido) <= 50:
            return self.texto_polido
        return self.texto_polido[:47] + "..."
    
    @property
    def timestamp_formatado(self) -> str:
        """Retorna timestamp formatado para exibição."""
        return self.timestamp.strftime("%d/%m/%Y %H:%M")


class GerenciadorHistorico:
    """
    Gerencia persistência de transcrições em SQLite.
    
    Garante que todos dados são salvos de forma transacional
    e podem ser recuperados posteriormente via busca ou listagem.
    """
    
    SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS transcricoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        texto_bruto TEXT NOT NULL,
        texto_polido TEXT NOT NULL,
        duracao_segundos REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON transcricoes(timestamp DESC);
    """
    
    def __init__(self, caminho_db: Optional[str] = None):
        """
        Inicializa gerenciador de histórico.
        
        Args:
            caminho_db: Caminho opcional para banco de dados.
                        Se não fornecido, usa %APPDATA%/VoiceFlow/historico.db
        """
        if caminho_db is None:
            # Usa diretório padrão de dados de aplicação
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            diretorio = Path(appdata) / 'VoiceFlow'
            diretorio.mkdir(parents=True, exist_ok=True)
            self._caminho_db = str(diretorio / 'historico.db')
        else:
            self._caminho_db = caminho_db
        
        self._inicializar_banco()
        logger.info(f"GerenciadorHistorico inicializado: {self._caminho_db}")
    
    def _inicializar_banco(self) -> None:
        """Cria tabelas se não existirem."""
        with sqlite3.connect(self._caminho_db) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(self.SCHEMA_SQL)
            conn.commit()
        logger.debug("Schema do banco de dados verificado/criado")
    
    def salvar(
        self, 
        texto_bruto: str, 
        texto_polido: str, 
        duracao_segundos: float
    ) -> int:
        """
        Salva transcrição no histórico.
        
        Operação transacional - ou salva completamente ou falha.
        
        Args:
            texto_bruto: Texto original da transcrição Groq
            texto_polido: Texto processado pelo Gemini (ou bruto se polimento desabilitado)
            duracao_segundos: Duração da gravação original
            
        Returns:
            ID do registro criado
            
        Raises:
            sqlite3.Error: Se falhar ao salvar
        """
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self._caminho_db) as conn:
            conn.execute("PRAGMA synchronous = NORMAL")
            cursor = conn.execute(
                """
                INSERT INTO transcricoes 
                    (timestamp, texto_bruto, texto_polido, duracao_segundos)
                VALUES (?, ?, ?, ?)
                """,
                (timestamp, texto_bruto, texto_polido, duracao_segundos)
            )
            conn.commit()
            registro_id = cursor.lastrowid
        
        logger.info(f"Transcrição salva no histórico: ID {registro_id}")
        return registro_id
    
    def listar(self, limite: int = 100, offset: int = 0) -> List[RegistroTranscricao]:
        """
        Lista transcrições ordenadas por data (mais recente primeiro).
        
        Args:
            limite: Número máximo de registros a retornar
            offset: Número de registros a pular (para paginação)
            
        Returns:
            Lista de RegistroTranscricao
        """
        with sqlite3.connect(self._caminho_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, timestamp, texto_bruto, texto_polido, duracao_segundos
                FROM transcricoes
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """,
                (limite, offset)
            )
            rows = cursor.fetchall()
        
        return [self._row_para_registro(row) for row in rows]
    
    def buscar(self, termo: str, limite: int = 50) -> List[RegistroTranscricao]:
        """
        Busca transcrições por termo (case-insensitive).
        
        Procura tanto em texto_bruto quanto texto_polido.
        
        Args:
            termo: Termo de busca
            limite: Número máximo de resultados
            
        Returns:
            Lista de RegistroTranscricao que contêm o termo
        """
        termo_like = f"%{termo}%"
        
        with sqlite3.connect(self._caminho_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, timestamp, texto_bruto, texto_polido, duracao_segundos
                FROM transcricoes
                WHERE texto_bruto LIKE ? COLLATE NOCASE
                   OR texto_polido LIKE ? COLLATE NOCASE
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (termo_like, termo_like, limite)
            )
            rows = cursor.fetchall()
        
        logger.debug(f"Busca '{termo}' retornou {len(rows)} resultados")
        return [self._row_para_registro(row) for row in rows]
    
    def obter(self, registro_id: int) -> Optional[RegistroTranscricao]:
        """
        Obtém transcrição específica por ID.
        
        Args:
            registro_id: ID do registro
            
        Returns:
            RegistroTranscricao ou None se não encontrado
        """
        with sqlite3.connect(self._caminho_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, timestamp, texto_bruto, texto_polido, duracao_segundos
                FROM transcricoes
                WHERE id = ?
                """,
                (registro_id,)
            )
            row = cursor.fetchone()
        
        if row is None:
            return None
        
        return self._row_para_registro(row)
    
    def contar(self) -> int:
        """Retorna número total de transcrições no histórico."""
        with sqlite3.connect(self._caminho_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM transcricoes")
            return cursor.fetchone()[0]
    
    def _row_para_registro(self, row: sqlite3.Row) -> RegistroTranscricao:
        """Converte row SQLite para dataclass."""
        return RegistroTranscricao(
            id=row['id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            texto_bruto=row['texto_bruto'],
            texto_polido=row['texto_polido'],
            duracao_segundos=row['duracao_segundos']
        )
    
    def limpar_antigos(self, dias_retencao: int = 5) -> int:
        """
        Remove transcrições mais antigas que o número especificado de dias.
        
        Args:
            dias_retencao: Número de dias para manter (default: 5)
            
        Returns:
            Número de registros removidos
        """
        # Calcula data limite
        data_limite = (datetime.now() - timedelta(days=dias_retencao)).isoformat()
        
        try:
            with sqlite3.connect(self._caminho_db) as conn:
                cursor = conn.execute(
                    "DELETE FROM transcricoes WHERE timestamp < ?",
                    (data_limite,)
                )
                removidos = cursor.rowcount
                conn.commit()
            
            if removidos > 0:
                logger.info(f"Limpeza de histórico: {removidos} registros removidos (>{dias_retencao} dias)")
            
            return removidos
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao limpar histórico antigo: {e}")
            return 0
    
    def excluir_por_id(self, registro_id: int) -> bool:
        """
        Exclui uma transcrição específica.
        
        Args:
            registro_id: ID do registro a excluir
            
        Returns:
            True se excluiu com sucesso
        """
        try:
            with sqlite3.connect(self._caminho_db) as conn:
                cursor = conn.execute(
                    "DELETE FROM transcricoes WHERE id = ?",
                    (registro_id,)
                )
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Registro {registro_id} excluído com sucesso")
                    return True
                return False
        except sqlite3.Error as e:
            logger.error(f"Erro ao excluir registro {registro_id}: {e}")
            return False
            
    def excluir_tudo(self) -> int:
        """
        Exclui TODAS as transcrições do histórico.
        
        Returns:
            Número de registros excluídos
        """
        try:
            with sqlite3.connect(self._caminho_db) as conn:
                cursor = conn.execute("DELETE FROM transcricoes")
                removidos = cursor.rowcount
                conn.commit()
            
            logger.info(f"Histórico limpo completamente: {removidos} registros excluídos")
            return removidos
        except sqlite3.Error as e:
            logger.error(f"Erro ao limpar histórico: {e}")
            return 0
