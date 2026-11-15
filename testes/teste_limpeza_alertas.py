"""Nova gravacao zera SOMENTE o painel; CSV de alertas nao e apagado/modificado."""

import csv
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from interface_grafica import InterfaceMonitoramento
from telemetria_gui import (
    DecodificadorTelemetria, DetectorEventos, EventoAlerta,
    HistoricoAlertas, HistoricoLeituras,
)


class TestePreservacaoCSV(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.caminho = Path(self.temp.name) / "alertas_ky037.csv"
        self.historico = HistoricoAlertas(str(self.caminho))
        self.antigo = EventoAlerta(
            horario_pc="2026-11-14T20:00:00-03:00", sensor="KY-037",
            tipo="ACIMA", valor=5100, unidade="raw", limite_inferior=0,
            limite_superior=4500, origem="192.168.42.2",
        )
        self.historico.registrar(self.antigo)
        self.conteudo_original = self.caminho.read_bytes()

    def test_novos_eventos_so_sao_anexados_sem_reescrever_antigos(self):
        seguinte = replace(self.antigo, horario_pc="2026-11-14T20:00:01-03:00",
                           valor=4200, tipo="NORMALIZADO", reconhecido=True)
        self.historico.registrar(seguinte)
        self.assertTrue(self.caminho.read_bytes().startswith(self.conteudo_original))
        self.assertEqual(len(self.historico.listar_todos()), 2)

    def test_cache_limitado_nao_exclui_alertas_antigos_do_csv(self):
        curto = HistoricoAlertas(str(self.caminho), max_eventos=2)
        for idx in range(5):
            curto.registrar(replace(self.antigo, valor=5001+idx))
        self.assertEqual(len(curto.listar()), 2)
        self.assertEqual(len(curto.listar_todos()), 6)
        self.assertTrue(self.caminho.read_bytes().startswith(self.conteudo_original))


class TestePainelPorGravacao(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pasta = Path(self.temp.name)
        self.caminho = self.pasta / "alertas_ky037.csv"
        self.historico = HistoricoAlertas(str(self.caminho))
        self.antigo = EventoAlerta(
            horario_pc="2026-11-14T20:00:00-03:00", sensor="KY-037",
            tipo="ACIMA", valor=5100, unidade="raw", limite_inferior=0,
            limite_superior=4500, origem="192.168.42.2",
        )
        self.historico.registrar(self.antigo)
        self.csv_original = self.caminho.read_bytes()
        self.app = InterfaceMonitoramento.__new__(InterfaceMonitoramento)
        self.app._janela = object()
        self.app._alertas = self.historico
        self.app._eventos_painel = [self.antigo]
        self.app._detector_alertas = DetectorEventos()
        self.app._historico = HistoricoLeituras()
        self.app._erro_alertas_var = Mock()
        self.app._detalhe_alerta_var = Mock()
        self.app._arquivo_var = Mock()
        self.app._atualizar_lista_alertas = Mock()
        self.app._gravador = Mock()
        self.app._ultimo_csv_gravado = None

    def test_zerar_painel_nao_toca_no_csv(self):
        self.app._limpar_alertas()
        self.assertEqual(self.app._eventos_painel, [])
        self.assertEqual(self.caminho.read_bytes(), self.csv_original)
        self.assertEqual(len(self.historico.listar()), 1)
        self.app._atualizar_lista_alertas.assert_called_once()

    @patch("interface_grafica.filedialog.asksaveasfilename")
    def test_iniciar_gravacao_zera_painel_mas_preserva_alertas(self, dialogo):
        dialogo.return_value = str(self.pasta / "nova_gravacao.csv")
        # Registrar estado de alarme previo no detector: nova sessao reavalia.
        leitura = DecodificadorTelemetria().decodificar(b"KY-037,5100,raw")
        self.app._detector_alertas.avaliar(leitura, 0, 4500)
        self.app._iniciar_gravacao()
        self.app._gravador.iniciar.assert_called_once_with(dialogo.return_value)
        self.assertEqual(self.app._eventos_painel, [])
        self.assertEqual(self.caminho.read_bytes(), self.csv_original)
        self.assertEqual(self.historico.listar(), [self.antigo])
        # Reavaliar leitura alta deve criar novo evento da sessao.
        self.assertEqual(self.app._detector_alertas.avaliar(leitura, 0, 4500).tipo, "ACIMA")

    @patch("interface_grafica.filedialog.asksaveasfilename", return_value="")
    def test_cancelar_dialogo_nao_zera_painel(self, _dialogo):
        self.app._iniciar_gravacao()
        self.assertEqual(self.app._eventos_painel, [self.antigo])
        self.app._gravador.iniciar.assert_not_called()
        self.assertEqual(self.caminho.read_bytes(), self.csv_original)

    @patch("interface_grafica.messagebox.showerror")
    @patch("interface_grafica.filedialog.asksaveasfilename", return_value="erro.csv")
    def test_falha_ao_iniciar_gravacao_nao_zera_painel(self, _dialogo, _aviso):
        self.app._gravador.iniciar.side_effect = OSError("sem permissao")
        self.app._iniciar_gravacao()
        self.assertEqual(self.app._eventos_painel, [self.antigo])
        self.assertEqual(self.caminho.read_bytes(), self.csv_original)

    def test_reconhecer_alertas_e_apenas_visual(self):
        self.app._reconhecer_alertas()
        self.assertTrue(self.app._eventos_painel[0].reconhecido)
        self.assertEqual(self.caminho.read_bytes(), self.csv_original)
        self.assertFalse(self.historico.listar()[0].reconhecido)

    def test_novo_evento_registrado_em_ambos_sem_restaurar_antigos_no_painel(self):
        self.app._limpar_alertas()
        novo = replace(self.antigo, valor=4700, horario_pc="2026-11-14T20:01:00-03:00")
        self.historico.registrar(novo)
        self.app._eventos_painel.append(novo)
        self.assertEqual(self.app._eventos_painel, [novo])
        self.assertEqual(len(self.historico.listar_todos()), 2)
        self.assertTrue(self.caminho.read_bytes().startswith(self.csv_original))


if __name__ == "__main__":
    unittest.main()
