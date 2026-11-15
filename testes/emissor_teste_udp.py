#!/usr/bin/env python3
"""Emissor SIMULADO para testar a GUI; NAO comprova funcionamento na STM32."""

import argparse
import json
import socket
import time


class EmissorTesteUDP:
    """Gera amostras ficticias para verificar grafico, alerta e exportacao CSV."""

    @staticmethod
    def executar() -> None:
        parser = argparse.ArgumentParser(description="Emissor UDP de teste (dados simulados)")
        parser.add_argument("--ip", default="127.0.0.1")
        parser.add_argument("--porta", type=int, default=8080)
        parser.add_argument("--amostras", type=int, default=80)
        argumentos = parser.parse_args()
        if not 1 <= argumentos.porta <= 65535 or argumentos.amostras <= 0:
            parser.error("Porta e quantidade de amostras invalidas")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as transmissor:
            for indice in range(argumentos.amostras):
                valor = 4200 + (indice * 17) % 240
                if indice % 17 in (10, 11, 12):
                    valor += 1300
                pacote = json.dumps({
                    "sensor": "KY-037-SIMULADO", "valor": valor, "unidade": "raw",
                    "timestamp": int(time.time() * 1000),
                }).encode("utf-8")
                transmissor.sendto(pacote, (argumentos.ip, argumentos.porta))
                time.sleep(0.1)
        print(f"Teste simulado concluido: {argumentos.amostras} pacotes enviados.")


if __name__ == "__main__":
    EmissorTesteUDP.executar()
