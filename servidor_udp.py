#!/usr/bin/env python3
"""
Servidor Receptor UDP - Monitoramento KY-037
Recebe telemetria do sensor KY-037 enviado pela placa STM32MP1-DK1 ou teste local.
Implementado em orientacao a objetos, sem variaveis globais.
Atende aos requisitos da Entrega 3 (Protocolo UDP) e prepara a base para a Entrega 4.
"""

import socket
import json
import sys
from datetime import datetime
from typing import Optional, Tuple


class ServidorReceptorUDP:
    """
    Classe responsavel por encapsular o socket receptor UDP e processar os pacotes de telemetria.
    """

    def __init__(self, host: str = "0.0.0.0", porta: int = 8080) -> None:
        self._host = host
        self._porta = porta
        self._socket: Optional[socket.socket] = None
        self._total_pacotes_recebidos = 0

    def iniciar(self) -> None:
        """Inicia a escuta UDP no endereco e porta configurados."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self._socket.bind((self._host, self._porta))
        except OSError as erro:
            print(f"[ERRO] Nao foi possivel vincular a porta {self._porta}: {erro}")
            sys.exit(1)

        print("=" * 65)
        print(f" Servidor Receptor UDP ativo em {self._host}:{self._porta}")
        print(" Aguardando pacotes de telemetria do sensor KY-037...")
        print(" Pressione Ctrl+C para encerrar.")
        print("=" * 65)

        self._executar_loop_recepcao()

    def _executar_loop_recepcao(self) -> None:
        """Loop continuo de recepcao e tratamento de datagramas."""
        if not self._socket:
            return

        try:
            while True:
                dados, endereco = self._socket.recvfrom(2048)
                self._processar_datagrama(dados, endereco)
        except KeyboardInterrupt:
            print("\nServidor receptor encerrado pelo usuario.")
        finally:
            self.fechar()

    def _processar_datagrama(self, dados: bytes, endereco: Tuple[str, int]) -> None:
        """Decodifica e exibe as mensagens recebidas em JSON ou texto/CSV."""
        self._total_pacotes_recebidos += 1
        texto = dados.decode("utf-8", errors="replace").strip()
        hora_local = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        try:
            msg = json.loads(texto)
            sensor = msg.get("sensor", "DESCONHECIDO")
            valor = msg.get("valor", 0)
            unidade = msg.get("unidade", "")
            ts = msg.get("timestamp", 0)
            print(f"[{hora_local}] #{self._total_pacotes_recebidos:04d} de {endereco[0]}:{endereco[1]} -> "
                  f"Sensor: {sensor} | Leitura: {valor:5d} {unidade} | Timestamp: {ts}")
        except json.JSONDecodeError:
            print(f"[{hora_local}] #{self._total_pacotes_recebidos:04d} de {endereco[0]}:{endereco[1]} -> {texto}")

    def fechar(self) -> None:
        """Fecha o socket de forma segura."""
        if self._socket:
            self._socket.close()
            self._socket = None

    @property
    def total_pacotes(self) -> int:
        return self._total_pacotes_recebidos


class AplicacaoServidor:
    """Interface CLI da aplicacao servidora."""

    @staticmethod
    def executar() -> None:
        porta = 8080
        if len(sys.argv) > 1:
            try:
                porta = int(sys.argv[1])
            except ValueError:
                print(f"Porta invalida: {sys.argv[1]}. Usando porta padrao 8080.")

        servidor = ServidorReceptorUDP(host="0.0.0.0", porta=porta)
        servidor.iniciar()


if __name__ == "__main__":
    AplicacaoServidor.executar()
