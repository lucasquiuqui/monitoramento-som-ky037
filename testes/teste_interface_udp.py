"""Testes da Entrega 4 independentes de janela grafica e de STM32."""

import csv
import json
import queue
import socket
import tempfile
import unittest
from pathlib import Path

from telemetria_gui import DecodificadorTelemetria, GravadorCSV, HistoricoLeituras, ReceptorUDP


class TesteDecodificacao(unittest.TestCase):
    def setUp(self):
        self.conversor = DecodificadorTelemetria()

    def test_json_com_timestamp(self):
        texto = json.dumps({"sensor": "KY-037", "valor": 4250, "unidade": "raw",
                            "timestamp": 946686107619}).encode()
        leitura = self.conversor.decodificar(texto, "192.168.42.2")
        self.assertEqual(leitura.valor, 4250)
        self.assertEqual(leitura.sensor, "KY-037")
        self.assertEqual(leitura.timestamp_placa_ms, 946686107619)
        self.assertEqual(leitura.origem, "192.168.42.2")
        self.assertTrue(leitura.horario_pc)

    def test_json_sem_timestamp(self):
        leitura = self.conversor.decodificar(b'{"sensor":"KY-037","valor":4000,"unidade":"raw"}')
        self.assertIsNone(leitura.timestamp_placa_ms)

    def test_csv_com_e_sem_timestamp(self):
        leitura = self.conversor.decodificar(b"KY-037,4100,raw,1000")
        self.assertEqual(leitura.valor, 4100)
        self.assertEqual(leitura.timestamp_placa_ms, 1000)
        outro = self.conversor.decodificar(b"KY-037,4140,raw")
        self.assertIsNone(outro.timestamp_placa_ms)

    def test_rejeita_valores_invalidos(self):
        invalidos = [
            b"", b"abc", b"KY-037,ABC,raw,100", b"KY-037,-1,raw,100",
            b'{"sensor":"KY-037","valor":true,"unidade":"raw"}',
            b'{"sensor":"KY-037","valor":4000}',
            b'{"sensor":"KY-037","valor":4000,"unidade":"raw","timestamp":"errado"}',
            b'{"sensor":"KY-037",', b"\xff\xfe",
        ]
        for texto in invalidos:
            with self.subTest(texto=texto), self.assertRaises(ValueError):
                self.conversor.decodificar(texto)


class TesteHistorico(unittest.TestCase):
    def test_janela_movel_e_memoria(self):
        from dataclasses import replace
        leitor = DecodificadorTelemetria()
        modelo = leitor.decodificar(b"KY-037,100,raw")
        historia = HistoricoLeituras(janela_maxima_s=60, max_amostras=3)
        for instante in (100.0, 135.0, 155.0, 160.0):
            historia.adicionar(replace(modelo, tempo_monotonico_pc=instante))
        self.assertEqual(len(historia.recentes(60, agora=160.0)), 3)
        self.assertEqual(len(historia.recentes(30, agora=160.0)), 3)
        self.assertEqual(len(historia.recentes(30, agora=190.0)), 1)
        self.assertEqual(len(historia.recentes(60, agora=300.0)), 0)


class TesteGravacao(unittest.TestCase):
    def test_csv_gravacao_e_exportacao(self):
        amostra = DecodificadorTelemetria().decodificar(b"KY-037,4200,raw,946686107619")
        with tempfile.TemporaryDirectory() as pasta:
            arquivo_log = str(Path(pasta) / "log.csv")
            arquivo_exportado = str(Path(pasta) / "janela.csv")
            gravador = GravadorCSV()
            gravador.iniciar(arquivo_log)
            gravador.registrar(amostra)
            gravador.parar()
            gravador.iniciar(arquivo_log)
            gravador.registrar(amostra)
            gravador.parar()
            gravador.exportar(arquivo_exportado, [amostra])
            with open(arquivo_log, newline="", encoding="utf-8") as arquivo:
                linhas = list(csv.reader(arquivo))
            self.assertEqual(len(linhas), 3)
            self.assertEqual(linhas[0], GravadorCSV.cabecalho())
            self.assertEqual(linhas[1][2], "4200")
            self.assertEqual(linhas[1][4], "946686107619")
            with open(arquivo_exportado, newline="", encoding="utf-8") as arquivo:
                self.assertEqual(len(list(csv.reader(arquivo))), 2)


class TesteUDP(unittest.TestCase):
    def test_datagrama_real_em_loopback(self):
        fila = queue.Queue()
        receptor = ReceptorUDP(fila, host="127.0.0.1", porta=0)
        receptor.iniciar()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as transmissor:
                transmissor.sendto(b'{"sensor":"KY-037","valor":5100,"unidade":"raw"}',
                                   ("127.0.0.1", receptor.porta))
            tipo, conteudo, origem = fila.get(timeout=2.0)
            self.assertEqual(tipo, "dados")
            self.assertEqual(origem, "127.0.0.1")
            self.assertEqual(DecodificadorTelemetria().decodificar(conteudo).valor, 5100)
        finally:
            receptor.fechar()


if __name__ == "__main__":
    unittest.main()
