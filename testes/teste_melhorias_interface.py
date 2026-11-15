"""Testes de estatisticas, escala ampliada e historico persistente de alertas."""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from telemetria_gui import (
    AnaliseLeituras, DecodificadorTelemetria, DetectorEventos,
    HistoricoAlertas, HistoricoLeituras,
)


class TesteEstatisticas(unittest.TestCase):
    def setUp(self):
        self.modelo = DecodificadorTelemetria().decodificar(b"KY-037,4100,raw")
        self.analise = AnaliseLeituras()

    def test_medias_minimos_e_maximos(self):
        dados = [replace(self.modelo, valor=v) for v in (4100, 4300, 4400, 4700)]
        resumo = self.analise.estatisticas(dados)
        self.assertEqual(resumo.quantidade, 4)
        self.assertEqual(resumo.media, 4375)
        self.assertEqual(resumo.minimo, 4100)
        self.assertEqual(resumo.maximo, 4700)
        self.assertIsNone(self.analise.estatisticas([]))

    def test_estatisticas_respeitam_janela_movel(self):
        historia = HistoricoLeituras(janela_maxima_s=60)
        for valor, instante in ((100, 100.0), (200, 135.0), (300, 155.0)):
            historia.adicionar(replace(self.modelo, valor=valor,
                                       tempo_monotonico_pc=instante))
        resumo = self.analise.estatisticas(historia.recentes(30, agora=160.0))
        self.assertEqual(resumo.quantidade, 2)
        self.assertEqual(resumo.media, 250)

    def test_escala_robusta_nao_perde_picos(self):
        valores = [4000 + (i % 9) * 25 for i in range(99)] + [41204]
        auto = self.analise.escala(valores, ampliada=False)
        ampliada = self.analise.escala(valores, ampliada=True)
        self.assertEqual(auto.acima, 0)
        self.assertEqual(ampliada.maximo_real, 41204)
        self.assertGreaterEqual(ampliada.acima, 1)
        self.assertLess(ampliada.maximo, auto.maximo)
        self.assertEqual(valores[-1], 41204)  # Dado original preservado.
        self.assertEqual(self.analise.escala([4300] * 40, True).acima, 0)
        with self.assertRaises(ValueError):
            self.analise.escala([], True)


class TesteAlertas(unittest.TestCase):
    def setUp(self):
        self.modelo = DecodificadorTelemetria().decodificar(b"KY-037,4100,raw")

    def test_transicoes_sem_duplicar_por_pacote(self):
        detector = DetectorEventos()
        self.assertIsNone(detector.avaliar(self.modelo, 3500, 5000))
        alto = replace(self.modelo, valor=5300)
        evento = detector.avaliar(alto, 3500, 5000)
        self.assertEqual(evento.tipo, "ACIMA")
        self.assertFalse(evento.reconhecido)
        self.assertIsNone(detector.avaliar(alto, 3500, 5000))
        normal = detector.avaliar(self.modelo, 3500, 5000)
        self.assertEqual(normal.tipo, "NORMALIZADO")
        self.assertTrue(normal.reconhecido)
        baixo = detector.avaliar(replace(self.modelo, valor=3400), 3500, 5000)
        self.assertEqual(baixo.tipo, "ABAIXO")
        detector.reiniciar()
        self.assertEqual(detector.avaliar(alto, 3500, 5000).tipo, "ACIMA")

    def test_grava_recupera_e_reconhece_eventos(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = str(Path(pasta) / "alertas.csv")
            detector = DetectorEventos()
            registro = HistoricoAlertas(caminho)
            primeiro = detector.avaliar(replace(self.modelo, valor=5500), 0, 5000)
            recuperado = detector.avaliar(self.modelo, 0, 5000)
            registro.registrar(primeiro)
            registro.registrar(recuperado)
            self.assertEqual(registro.pendentes(), 1)
            restaurado = HistoricoAlertas(caminho)
            self.assertEqual(len(restaurado.listar()), 2)
            self.assertEqual(restaurado.pendentes(), 1)
            self.assertEqual(restaurado.reconhecer_todos(), 1)
            self.assertEqual(HistoricoAlertas(caminho).pendentes(), 0)
            self.assertEqual(restaurado.reconhecer_todos(), 0)

    def test_historico_limitado(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = str(Path(pasta) / "alertas.csv")
            detector = DetectorEventos()
            registro = HistoricoAlertas(caminho, max_eventos=2)
            for valor in (5100, 4200, 5200):
                evento = detector.avaliar(replace(self.modelo, valor=valor), 0, 5000)
                registro.registrar(evento)
            self.assertEqual(len(registro.listar()), 2)
            # O cache em memoria e limitado a 2, mas o CSV e cumulativo.
            self.assertEqual(len(HistoricoAlertas(caminho).listar()), 3)
            self.assertEqual(len(HistoricoAlertas(caminho, max_eventos=2).listar()), 2)


if __name__ == "__main__":
    unittest.main()
