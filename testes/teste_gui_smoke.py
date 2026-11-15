"""Teste de integracao GUI local. Requer display/Xvfb, nao usa STM32."""

import socket
import tempfile
from pathlib import Path
import time
import tkinter as tk
import unittest

from interface_grafica import InterfaceMonitoramento


class TesteGuiSmoke(unittest.TestCase):
    def test_abertura_udp_alerta_grafico_e_encerramento(self):
        # Porta reservada pelo SO para teste, liberada antes de abrir a GUI.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(("127.0.0.1", 0))
            porta = s.getsockname()[1]
        pasta = tempfile.TemporaryDirectory()
        janela = tk.Tk()
        app = InterfaceMonitoramento(janela, porta=porta,
                                    caminho_alertas=str(Path(pasta.name) / "alertas.csv"))
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as emissor:
                emissor.sendto(b'{"sensor":"KY-037","valor":5500,"unidade":"raw"}',
                              ("127.0.0.1", porta))
            limite = time.monotonic() + 2
            while app._quantidade < 1 and time.monotonic() < limite:
                janela.update()
                time.sleep(0.04)
            self.assertEqual(app._quantidade, 1)
            self.assertIn("5.500", app._valor_var.get())
            self.assertEqual(app._estado_var.get(), "ALERTA!")
            self.assertEqual(len(app._historico.recentes(60)), 1)
            self.assertEqual(app._alertas.pendentes(), 1)
            self.assertEqual(app._alertas.listar()[0].tipo, "ACIMA")
            app._reconhecer_alertas()
            # Reconhecimento acontece apenas no painel; o CSV continua intacto.
            self.assertTrue(app._eventos_painel[0].reconhecido)
            self.assertEqual(app._alertas.pendentes(), 1)
            self.assertEqual(app._media_var.get(), "5.500,0")
            self.assertEqual(app._maximo_var.get(), "5.500")
            app._escala_var.set("Ampliada")
            app._desenhar_grafico()
            app._inferior_var.set("0")
            app._superior_var.set("6000")
            app._aplicar_limites()
            self.assertEqual(app._estado_var.get(), "NORMAL")
        finally:
            app._fechar()
            pasta.cleanup()


if __name__ == "__main__":
    unittest.main()
