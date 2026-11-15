"""Testes do relatório .xlsx, chart editável e alertas persistidos."""

import csv
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from relatorio_excel import RelatorioExcel


class TesteRelatorioExcel(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.csv = self.base / "gravacao.csv"
        self.xlsx = self.base / "relatorio.xlsx"
        self.inicio = datetime(2026, 11, 14, 21, 0, tzinfo=timezone(timedelta(hours=-3)))
        with self.csv.open("w", encoding="utf-8", newline="") as arq:
            escritor = csv.writer(arq)
            escritor.writerow(["horario_pc", "sensor", "valor_adc", "unidade",
                              "timestamp_placa_ms", "ip_origem"])
            for n in range(25):
                escritor.writerow([(self.inicio + timedelta(milliseconds=100*n)).isoformat(),
                                   "KY-037", 3500 if n != 10 else 6493,
                                   "raw", 946684800000 + n * 100, "192.168.42.2"])

    def test_relatorio_todas_as_leituras_e_grafico(self):
        evento = {"horario_pc": (self.inicio + timedelta(seconds=1)).isoformat(),
                  "sensor": "KY-037", "tipo": "ACIMA", "valor": 6493,
                  "unidade": "raw", "limite_inferior": 0,
                  "limite_superior": 5000, "origem": "192.168.42.2",
                  "reconhecido": False}
        r = RelatorioExcel().gerar(str(self.csv), str(self.xlsx), [evento])
        self.assertEqual(r['amostras'], 25)
        self.assertEqual(r['alertas_na_gravacao'], 1)
        with zipfile.ZipFile(self.xlsx) as z:
            self.assertIsNone(z.testzip())
            for nome in z.namelist():
                if nome.endswith('.xml') or nome.endswith('.rels'):
                    ET.fromstring(z.read(nome))
            self.assertIn(b'scatterChart', z.read('xl/charts/chart1.xml'))
            self.assertIn(b'6493', z.read('xl/charts/chart1.xml'))
            self.assertIn(b'ACIMA', z.read('xl/worksheets/sheet3.xml'))
            self.assertIn(b'946684801000', z.read('xl/worksheets/sheet2.xml'))
            self.assertEqual(z.read('xl/worksheets/sheet2.xml').count(b'<row '), 26)

    def test_dados_nao_fabricam_alertas(self):
        resultado = RelatorioExcel().gerar(str(self.csv), str(self.xlsx))
        self.assertEqual(resultado['alertas'], 0)
        with zipfile.ZipFile(self.xlsx) as z:
            self.assertIn('xl/worksheets/sheet3.xml', z.namelist())
            self.assertIn(b'Nenhum evento persistido', z.read('xl/worksheets/sheet3.xml'))

    def test_csv_invalido_rejeitado(self):
        self.csv.write_text('x,y\n1,2\n',encoding='utf-8')
        with self.assertRaises(ValueError):
            RelatorioExcel().gerar(str(self.csv), str(self.xlsx))

    def test_serie_longa_preserva_extremos_e_nao_altera_base(self):
        dados = [{'numero':i,'adc':3500 if i!=4500 else 19000,
                  'segundos':i/10} for i in range(10000)]
        serie = RelatorioExcel._reduzir_serie(dados)
        self.assertLessEqual(len(serie),1800)
        self.assertEqual(len(dados),10000)
        self.assertIn(19000,[p['adc'] for p in serie])
        self.assertEqual(serie[0]['numero'],0)
        self.assertEqual(serie[-1]['numero'],9999)


    def test_grafico_legivel_sem_rotulos_ponto_a_ponto(self):
        """O eixo vertical deve enquadrar os valores reais, sem comprimir por 0."""
        r = RelatorioExcel().gerar(str(self.csv), str(self.xlsx))
        with zipfile.ZipFile(self.xlsx) as z:
            raiz = ET.fromstring(z.read('xl/charts/chart1.xml'))
        ns = {'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'}
        self.assertEqual(len(raiz.findall('.//c:scatterChart/c:ser', ns)), 2)
        eixos = raiz.findall('.//c:valAx', ns)
        self.assertEqual(len(eixos), 2)
        eixo_y = eixos[1]
        minimo = float(eixo_y.find('c:scaling/c:min', ns).attrib['val'])
        maximo = float(eixo_y.find('c:scaling/c:max', ns).attrib['val'])
        self.assertGreater(minimo, 0)
        self.assertLess(minimo, 3500)
        self.assertGreater(maximo, 6493)
        for rotulo in raiz.findall('.//c:dLbls', ns):
            self.assertEqual(rotulo.find('c:showVal', ns).attrib['val'], '0')
            self.assertEqual(rotulo.find('c:showCatName', ns).attrib['val'], '0')
            self.assertEqual(rotulo.find('c:showSerName', ns).attrib['val'], '0')
        self.assertEqual(r['amostras'], 25)

    def test_limite_superior_distante_nao_comprime_a_curva(self):
        r = RelatorioExcel(limite_superior=30000).gerar(str(self.csv), str(self.xlsx))
        with zipfile.ZipFile(self.xlsx) as z:
            raiz = ET.fromstring(z.read('xl/charts/chart1.xml'))
        ns = {'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'}
        self.assertEqual(len(raiz.findall('.//c:scatterChart/c:ser', ns)), 1)
        self.assertEqual(r['amostras'], 25)


if __name__ == '__main__':
    unittest.main()
