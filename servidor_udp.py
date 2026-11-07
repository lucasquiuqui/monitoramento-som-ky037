#!/usr/bin/env python3
"""
Servidor Receptor UDP - Monitoramento KY-037
Recebe telemetria do sensor KY-037 enviado pela placa STM32MP1-DK1 ou teste local.
Atende aos requisitos da Entrega 3 (Protocolo UDP) e prepara a base para a Entrega 4.
"""

import socket
import json
import sys
from datetime import datetime

PORTA_PADRAO = 5000
HOST_PADRAO = "0.0.0.0"

def iniciar_servidor(host=HOST_PADRAO, porta=PORTA_PADRAO):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((host, porta))
    except Exception as e:
        print(f"[ERRO] Nao foi possivel iniciar na porta {porta}: {e}")
        sys.exit(1)

    print("=" * 60)
    print(f" Servidor Receptor UDP ativo em {host}:{porta}")
    print(" Aguardando pacotes de telemetria do sensor KY-037...")
    print(" Pressione Ctrl+C para encerrar.")
    print("=" * 60)

    contador = 0
    try:
        while True:
            dados, endereco = sock.recvfrom(2048)
            texto = dados.decode("utf-8", errors="replace").strip()
            contador += 1
            hora_local = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            # Tenta decodificar como JSON
            try:
                msg = json.loads(texto)
                sensor = msg.get("sensor", "DESCONHECIDO")
                valor = msg.get("valor", 0)
                unidade = msg.get("unidade", "")
                ts = msg.get("timestamp", 0)
                print(f"[{hora_local}] #{contador:04d} de {endereco[0]}:{endereco[1]} -> "
                      f"Sensor: {sensor} | Leitura: {valor:5d} {unidade} | Timestamp: {ts}")
            except json.JSONDecodeError:
                # Exibe como texto/CSV se nao for JSON
                print(f"[{hora_local}] #{contador:04d} de {endereco[0]}:{endereco[1]} -> {texto}")

    except KeyboardInterrupt:
        print("\nServidor encerrado pelo usuario.")
    finally:
        sock.close()

if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else PORTA_PADRAO
    iniciar_servidor(porta=porta)
