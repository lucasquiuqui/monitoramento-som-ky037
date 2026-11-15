"""Teste visual via Tk/Xvfb; verifica grafico visivel com janela nao maximizada."""

import socket
import tempfile
import tkinter as tk
import unittest
from dataclasses import replace
from pathlib import Path
import time

from interface_grafica import InterfaceMonitoramento
from telemetria_gui import DecodificadorTelemetria


class TesteLayoutJanela(unittest.TestCase):
    def test_grafico_visivel_900x600_e_estatisticas_retorna_em_janela_maior(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", 0))
            porta = sock.getsockname()[1]
        with tempfile.TemporaryDirectory() as pasta:
            janela = tk.Tk()
            app = InterfaceMonitoramento(janela, porta=porta,
                                        caminho_alertas=str(Path(pasta) / "alertas.csv"))
            try:
                janela.geometry("900x600+0+0")
                for _ in range(4):
                    janela.update()
                self.assertTrue(app._compacto)
                modelo = DecodificadorTelemetria().decodificar(b"KY-037,3835,raw")
                agora = time.monotonic()
                for n in range(100):
                    leitura = replace(modelo, valor=3800 + n % 45,
                                      tempo_monotonico_pc=agora - 10 + n * 0.1)
                    app._consumir_leitura(leitura)
                app._janela_var.set("30 min")
                app._atualizar_estatisticas()
                app._desenhar_grafico()
                janela.update()
                self.assertGreaterEqual(app._grafico.winfo_height(), 140)
                self.assertGreaterEqual(app._grafico.winfo_width(), 600)
                self.assertIsNotNone(app._grafico.bbox("all"))
                self.assertEqual(app._janela_segundos(), 1800)
                janela.geometry("1200x800+0+0")
                for _ in range(4):
                    janela.update()
                self.assertFalse(app._compacto)
                self.assertGreater(app._grafico.winfo_height(), 170)
                # Ao perder a rede, o historico permanece ancorado na ultima amostra.
                app._ultimo = replace(app._ultimo,
                                      tempo_monotonico_pc=agora - 15)
                self.assertEqual(app._tempo_referencia(), app._ultimo.tempo_monotonico_pc)
                app._desenhar_grafico()
                self.assertIsNotNone(app._grafico.bbox("all"))
            finally:
                app._fechar()


if __name__ == "__main__":
    unittest.main()
