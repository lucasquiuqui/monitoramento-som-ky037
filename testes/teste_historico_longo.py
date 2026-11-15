"""Testes de 30 minutos, renderizacao min/max e preservacao do ultimo grafico."""

import unittest
from dataclasses import replace

from telemetria_gui import AnaliseLeituras, DecodificadorTelemetria, HistoricoLeituras


class TesteHistoricoLongo(unittest.TestCase):
    def setUp(self):
        self.exemplo = DecodificadorTelemetria().decodificar(b"KY-037,3800,raw")

    def test_historico_30_minutos_e_janelas_curtas(self):
        historico = HistoricoLeituras(janela_maxima_s=1800, max_amostras=60000)
        for tempo, valor in ((100, 100), (250, 250), (600, 600),
                             (1800, 1800), (1900, 1900)):
            historico.adicionar(replace(self.exemplo, valor=valor,
                                       tempo_monotonico_pc=float(tempo)))
        self.assertEqual([p.valor for p in historico.recentes(1800, agora=1900)],
                         [100, 250, 600, 1800, 1900])
        self.assertEqual([p.valor for p in historico.recentes(300, agora=1900)],
                         [1800, 1900])
        self.assertEqual([p.valor for p in historico.recentes(60, agora=1900)],
                         [1900])

    def test_ate_trinta_minutos_sem_perder_amostras_a_10_hz(self):
        historico = HistoricoLeituras(janela_maxima_s=1800, max_amostras=60000)
        for i in range(18000):
            historico.adicionar(replace(self.exemplo, valor=3000 + (i % 100),
                                       tempo_monotonico_pc=i * 0.1))
        pontos = historico.recentes(1800, agora=1799.9)
        self.assertEqual(len(pontos), 18000)
        self.assertEqual(pontos[0].tempo_monotonico_pc, 0)

    def test_reducao_visual_preserva_extremos_e_ordenacao(self):
        valores = [3700 + i % 90 for i in range(3000)]
        valores[1500] = 6493
        valores[1999] = 3073
        leituras = [replace(self.exemplo, valor=v,
                            tempo_monotonico_pc=float(i))
                    for i, v in enumerate(valores)]
        reduzidas = AnaliseLeituras.reduzir_para_grafico(leituras, 150)
        self.assertLessEqual(len(reduzidas), 302)
        self.assertEqual(reduzidas[0], leituras[0])
        self.assertEqual(reduzidas[-1], leituras[-1])
        self.assertIn(6493, [p.valor for p in reduzidas])
        self.assertIn(3073, [p.valor for p in reduzidas])
        self.assertEqual(sorted(p.tempo_monotonico_pc for p in reduzidas),
                         [p.tempo_monotonico_pc for p in reduzidas])
        self.assertEqual(len(AnaliseLeituras.reduzir_para_grafico(leituras[:6], 100)), 6)
        with self.assertRaises(ValueError):
            AnaliseLeituras.reduzir_para_grafico(leituras, 0)


if __name__ == "__main__":
    unittest.main()
