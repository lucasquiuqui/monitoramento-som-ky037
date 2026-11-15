"""Componentes orientados a objetos da interface de monitoramento KY-037.

Apenas biblioteca padrao: transporte UDP, validacao, historico e persistencia CSV.
Nenhuma variavel global armazena dados da aplicacao.
"""

import csv
import io
import json
import queue
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Deque, List, Optional, Tuple


@dataclass(frozen=True)
class LeituraSom:
    """Amostra recebida no PC; o timestamp da placa nao e usado no grafico.

    O relogio da STM32 pode nao estar sincronizado; tempo_monotonico_pc
    determina o eixo horizontal e horario_pc registra o instante local.
    """

    sensor: str
    valor: int
    unidade: str
    timestamp_placa_ms: Optional[int]
    horario_pc: str
    tempo_monotonico_pc: float
    origem: str


class DecodificadorTelemetria:
    """Valida datagramas UDP JSON ou CSV enviados por ProtocoloSom (C++)."""

    def decodificar(self, dados: bytes, origem: str = "desconhecida") -> LeituraSom:
        try:
            texto = dados.decode("utf-8", errors="strict").strip()
        except UnicodeDecodeError as erro:
            raise ValueError("Datagrama nao esta em UTF-8.") from erro
        if not texto:
            raise ValueError("Datagrama vazio.")
        if texto.startswith("{"):
            try:
                objeto = json.loads(texto)
            except json.JSONDecodeError as erro:
                raise ValueError("JSON invalido.") from erro
            if not isinstance(objeto, dict):
                raise ValueError("JSON deve ser um objeto.")
            sensor = objeto.get("sensor")
            valor = objeto.get("valor")
            unidade = objeto.get("unidade")
            instante = objeto.get("timestamp")
        else:
            try:
                linhas = list(csv.reader(io.StringIO(texto), strict=True))
            except csv.Error as erro:
                raise ValueError("CSV invalido.") from erro
            if len(linhas) != 1 or len(linhas[0]) not in (3, 4):
                raise ValueError("CSV exige sensor,valor,unidade[,timestamp].")
            partes = linhas[0]
            sensor, valor, unidade = partes[:3]
            instante = partes[3] if len(partes) == 4 else None
            try:
                valor = int(valor)
                if instante not in (None, ""):
                    instante = int(instante)
                else:
                    instante = None
            except (ValueError, TypeError) as erro:
                raise ValueError("Valor/timestamp CSV devem ser inteiros.") from erro

        if not isinstance(sensor, str) or not sensor.strip():
            raise ValueError("Identificador de sensor ausente.")
        if not isinstance(unidade, str) or not unidade.strip():
            raise ValueError("Unidade ausente.")
        if type(valor) is not int or valor < 0:
            raise ValueError("Valor do ADC deve ser inteiro nao negativo.")
        if instante is not None and (type(instante) is not int or instante < 0):
            raise ValueError("Timestamp deve ser inteiro nao negativo.")
        if len(sensor) > 120 or len(unidade) > 32:
            raise ValueError("Campo de identificacao demasiado longo.")
        return LeituraSom(
            sensor=sensor.strip(), valor=valor, unidade=unidade.strip(),
            timestamp_placa_ms=instante,
            horario_pc=datetime.now().astimezone().isoformat(timespec="milliseconds"),
            tempo_monotonico_pc=time.monotonic(), origem=origem,
        )


class HistoricoLeituras:
    """Historico movel em tempo monotonic do PC, com limite de memoria."""

    def __init__(self, janela_maxima_s: int = 60, max_amostras: int = 20000) -> None:
        if janela_maxima_s <= 0 or max_amostras < 1:
            raise ValueError("Janela e capacidade devem ser positivas.")
        self._janela_maxima_s = janela_maxima_s
        self._amostras: Deque[LeituraSom] = deque(maxlen=max_amostras)

    def adicionar(self, leitura: LeituraSom) -> None:
        self._amostras.append(leitura)
        self._limpar_antigas(leitura.tempo_monotonico_pc)

    def _limpar_antigas(self, agora: float) -> None:
        corte = agora - self._janela_maxima_s
        while self._amostras and self._amostras[0].tempo_monotonico_pc < corte:
            self._amostras.popleft()

    def recentes(self, janela_s: int = 60, agora: Optional[float] = None) -> List[LeituraSom]:
        if janela_s <= 0 or janela_s > self._janela_maxima_s:
            raise ValueError("Janela solicitada fora da faixa disponivel.")
        momento = time.monotonic() if agora is None else agora
        self._limpar_antigas(momento)
        limite = momento - janela_s
        return [dado for dado in self._amostras if dado.tempo_monotonico_pc >= limite]

    def limpar(self) -> None:
        self._amostras.clear()


class ReceptorUDP:
    """Recebe datagramas em thread; nunca manipula widgets Tk diretamente."""

    def __init__(self, fila: "queue.Queue", host: str = "0.0.0.0", porta: int = 8080) -> None:
        self._fila = fila
        self._parar = threading.Event()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.settimeout(0.25)
        try:
            self._socket.bind((host, porta))
        except OSError:
            self._socket.close()
            raise
        self._porta = self._socket.getsockname()[1]
        self._thread = threading.Thread(target=self._receber, name="Receptor-KY037", daemon=True)
        self._descartados_fila = 0

    @property
    def porta(self) -> int:
        return self._porta

    @property
    def descartados_fila(self) -> int:
        return self._descartados_fila

    def iniciar(self) -> None:
        self._thread.start()

    def _receber(self) -> None:
        while not self._parar.is_set():
            try:
                dados, origem = self._socket.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError as erro:
                if not self._parar.is_set():
                    self._colocar(("erro", str(erro), ""))
                break
            self._colocar(("dados", dados, origem[0]))

    def _colocar(self, item: Tuple[str, object, str]) -> None:
        try:
            self._fila.put_nowait(item)
        except queue.Full:
            self._descartados_fila += 1

    def fechar(self) -> None:
        self._parar.set()
        self._socket.close()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)


class GravadorCSV:
    """Grava dados validos em CSV, incluindo horario confiavel do computador."""

    def __init__(self) -> None:
        self._arquivo = None
        self._escritor = None
        self._caminho: Optional[Path] = None

    @property
    def gravando(self) -> bool:
        return self._arquivo is not None

    @property
    def caminho(self) -> Optional[Path]:
        return self._caminho

    def iniciar(self, caminho: str) -> None:
        self.parar()
        destino = Path(caminho)
        adicionar_cabecalho = not destino.exists() or destino.stat().st_size == 0
        self._arquivo = destino.open("a", newline="", encoding="utf-8")
        self._caminho = destino
        self._escritor = csv.writer(self._arquivo)
        if adicionar_cabecalho:
            self._escritor.writerow(self.cabecalho())
            self._arquivo.flush()

    @staticmethod
    def cabecalho() -> List[str]:
        return ["horario_pc", "sensor", "valor_adc", "unidade", "timestamp_placa_ms", "ip_origem"]

    @staticmethod
    def linha(leitura: LeituraSom) -> List[object]:
        return [leitura.horario_pc, leitura.sensor, leitura.valor, leitura.unidade,
                "" if leitura.timestamp_placa_ms is None else leitura.timestamp_placa_ms,
                leitura.origem]

    def registrar(self, leitura: LeituraSom) -> None:
        if self._arquivo is None or self._escritor is None:
            return
        self._escritor.writerow(self.linha(leitura))
        self._arquivo.flush()

    def exportar(self, caminho: str, leituras: List[LeituraSom]) -> None:
        with Path(caminho).open("w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(self.cabecalho())
            for leitura in leituras:
                escritor.writerow(self.linha(leitura))

    def parar(self) -> None:
        if self._arquivo is not None:
            self._arquivo.close()
        self._arquivo = None
        self._escritor = None
        self._caminho = None


@dataclass(frozen=True)
class EstatisticasJanela:
    """Resumo das contagens brutas da janela temporal selecionada."""

    quantidade: int
    media: float
    minimo: int
    maximo: int


@dataclass(frozen=True)
class EscalaVertical:
    """Faixa exibida no grafico; os valores originais nunca sao modificados."""

    minimo: float
    maximo: float
    abaixo: int
    acima: int
    minimo_real: int
    maximo_real: int


class AnaliseLeituras:
    """Calcula estatisticas e uma escala vertical robusta opcional."""

    def estatisticas(self, leituras: List[LeituraSom]) -> Optional[EstatisticasJanela]:
        if not leituras:
            return None
        valores = [leitura.valor for leitura in leituras]
        return EstatisticasJanela(
            quantidade=len(valores), media=sum(valores) / len(valores),
            minimo=min(valores), maximo=max(valores),
        )

    @staticmethod
    def reduzir_para_grafico(leituras: List[LeituraSom], colunas: int) -> List[LeituraSom]:
        """Amostragem min/max por coluna visual, preservando picos extremos.

        Reduz o custo de desenhar milhares de amostras por quadro, sem alterar
        a memoria de dados, o CSV, as estatisticas ou o detector de alarmes.
        Mantem a ordem temporal original de entrada.
        """
        if colunas < 1:
            raise ValueError("O grafico precisa de pelo menos uma coluna.")
        quantidade = len(leituras)
        if quantidade <= max(2, 2 * colunas):
            return list(leituras)
        indices = {0, quantidade - 1}
        for coluna in range(colunas):
            inicio = coluna * quantidade // colunas
            fim = min(quantidade, (coluna + 1) * quantidade // colunas)
            if inicio >= fim:
                continue
            menor = min(range(inicio, fim), key=lambda i: leituras[i].valor)
            maior = max(range(inicio, fim), key=lambda i: leituras[i].valor)
            indices.update((menor, maior))
        return [leituras[i] for i in sorted(indices)]

    @staticmethod
    def _percentil(ordenados: List[int], fracao: float) -> float:
        posicao = fracao * (len(ordenados) - 1)
        baixo = int(posicao)
        alto = min(baixo + 1, len(ordenados) - 1)
        fracao_alta = posicao - baixo
        return ordenados[baixo] * (1 - fracao_alta) + ordenados[alto] * fracao_alta

    def escala(self, valores: List[int], ampliada: bool = False) -> EscalaVertical:
        if not valores:
            raise ValueError("Escala requer pelo menos uma leitura.")
        real_min, real_max = min(valores), max(valores)
        if ampliada and len(valores) >= 20:
            ordenados = sorted(valores)
            inferior = self._percentil(ordenados, 0.05)
            superior = self._percentil(ordenados, 0.95)
        else:
            inferior, superior = real_min, real_max
        amplitude = max(100.0, superior - inferior)
        y_min = max(0.0, inferior - 0.15 * amplitude)
        y_max = superior + 0.15 * amplitude
        return EscalaVertical(
            minimo=y_min, maximo=y_max,
            abaixo=sum(valor < y_min for valor in valores),
            acima=sum(valor > y_max for valor in valores),
            minimo_real=real_min, maximo_real=real_max,
        )


@dataclass(frozen=True)
class EventoAlerta:
    """Transicao de alerta, com horário local do computador e limites usados."""

    horario_pc: str
    sensor: str
    tipo: str
    valor: int
    unidade: str
    limite_inferior: int
    limite_superior: int
    origem: str
    reconhecido: bool = False


class DetectorEventos:
    """Registra somente transicoes de estado para nao inundar o log por pacote."""

    def __init__(self) -> None:
        self._estado: Optional[str] = None

    def reiniciar(self) -> None:
        """Reavalia a proxima leitura quando os limites forem alterados."""
        self._estado = None

    def avaliar(self, leitura: LeituraSom, inferior: int, superior: int) -> Optional[EventoAlerta]:
        if inferior < 0 or superior <= inferior:
            raise ValueError("Limites invalidos.")
        novo = "ABAIXO" if leitura.valor < inferior else (
            "ACIMA" if leitura.valor > superior else "NORMAL")
        anterior = self._estado
        self._estado = novo
        if novo == anterior or (novo == "NORMAL" and anterior is None):
            return None
        if novo == "NORMAL" and anterior not in ("ACIMA", "ABAIXO"):
            return None
        return EventoAlerta(
            horario_pc=leitura.horario_pc, sensor=leitura.sensor,
            tipo="NORMALIZADO" if novo == "NORMAL" else novo,
            valor=leitura.valor, unidade=leitura.unidade,
            limite_inferior=inferior, limite_superior=superior,
            origem=leitura.origem, reconhecido=(novo == "NORMAL"),
        )


class HistoricoAlertas:
    """Registro CSV cumulativo dos alertas, com janela recente em memoria.

    Novos eventos sao adicionados ao CSV sem reescrever eventos anteriores.
    A capacidade max_eventos limita somente o cache de eventos na memoria.
    Zerar o painel visual e responsabilidade da interface, nao deste registro.
    """

    def __init__(self, caminho: str, max_eventos: int = 500) -> None:
        if max_eventos < 1:
            raise ValueError("max_eventos deve ser positivo")
        self._caminho = Path(caminho)
        self._eventos: Deque[EventoAlerta] = deque(maxlen=max_eventos)
        self._carregar()

    @property
    def caminho(self) -> Path:
        return self._caminho

    def listar(self) -> List[EventoAlerta]:
        """Ultimos eventos conservados em memoria (para interface)."""
        return list(self._eventos)

    def listar_todos(self) -> List[EventoAlerta]:
        """Todos os eventos do CSV para relatorios, sem modificar o arquivo."""
        if not self._caminho.exists():
            return []
        with self._caminho.open("r", newline="", encoding="utf-8-sig") as arquivo:
            leitor = csv.DictReader(arquivo)
            if leitor.fieldnames != self._campos():
                raise ValueError("Arquivo de alertas com cabecalho inesperado.")
            return [EventoAlerta(
                horario_pc=linha["horario_pc"], sensor=linha["sensor"],
                tipo=linha["tipo"], valor=int(linha["valor"]),
                unidade=linha["unidade"], limite_inferior=int(linha["limite_inferior"]),
                limite_superior=int(linha["limite_superior"]), origem=linha["origem"],
                reconhecido=linha["reconhecido"].strip().lower() == "true",
            ) for linha in leitor]

    def pendentes(self) -> int:
        return sum(not e.reconhecido and e.tipo != "NORMALIZADO" for e in self._eventos)

    @staticmethod
    def _campos() -> List[str]:
        return ["horario_pc", "sensor", "tipo", "valor", "unidade",
                "limite_inferior", "limite_superior", "origem", "reconhecido"]

    def _carregar(self) -> None:
        for evento in self.listar_todos():
            self._eventos.append(evento)

    def _salvar(self) -> None:
        """Compatibilidade com reconhecimento explicito no modelo antigo.

        A interface grafica nao chama esta operacao, pois o seu reconhecimento
        e somente visual. No fluxo normal, os alertas sao sempre anexados.
        """
        import os
        import tempfile

        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        arquivo_temporario = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", delete=False,
                prefix=".ky037_alertas_", suffix=".tmp", dir=str(self._caminho.parent),
            ) as arq:
                arquivo_temporario = Path(arq.name)
                escritor = csv.DictWriter(arq, fieldnames=self._campos())
                escritor.writeheader()
                for evento in self._eventos:
                    escritor.writerow({campo: getattr(evento, campo) for campo in self._campos()})
            os.replace(arquivo_temporario, self._caminho)
        finally:
            if arquivo_temporario is not None and arquivo_temporario.exists():
                arquivo_temporario.unlink()

    def registrar(self, evento: EventoAlerta) -> None:
        """Adiciona um novo alerta ao final do CSV, preservando os anteriores."""
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        novo = not self._caminho.exists() or self._caminho.stat().st_size == 0
        with self._caminho.open("a", newline="", encoding="utf-8") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=self._campos())
            if novo:
                escritor.writeheader()
            escritor.writerow({campo: getattr(evento, campo) for campo in self._campos()})
        self._eventos.append(evento)

    def reconhecer_todos(self) -> int:
        from dataclasses import replace

        quantidade = self.pendentes()
        if quantidade:
            self._eventos = deque(
                (replace(e, reconhecido=True) for e in self._eventos),
                maxlen=self._eventos.maxlen,
            )
            self._salvar()
        return quantidade
