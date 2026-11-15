#!/usr/bin/env python3
"""Exportação XLSX do monitor KY-037 sem dependências de terceiros.

Gera um pacote OpenXML com quatro planilhas, gráfico editável (dispersão
XY), série reduzida para visualização e todas as medições originais intactas.
O timestamp da STM32 é conservado sem ser usado para tempo decorrido.
"""

import csv
import math
import statistics
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence
from xml.sax.saxutils import escape


class RelatorioExcel:
    """Escreve arquivos .xlsx de telemetria e eventos (Office Open XML)."""

    _TIPOS_CSV = ("horario_pc", "sensor", "valor_adc", "unidade",
                  "timestamp_placa_ms", "ip_origem")

    def __init__(self, limite_inferior: int = 0, limite_superior: int = 5000) -> None:
        if limite_inferior < 0 or limite_superior <= limite_inferior:
            raise ValueError("Os limites de ADC são inválidos.")
        self._inferior = limite_inferior
        self._superior = limite_superior

    @staticmethod
    def _xml(texto: object) -> str:
        valor = str(texto)
        # XML 1.0 não admite caracteres de controle, ainda que estejam no CSV.
        valor = "".join(c for c in valor if ord(c) >= 32 or c in "\t\n\r")
        return escape(valor, {'"': '&quot;'})

    @staticmethod
    def _coluna(indice: int) -> str:
        texto = ""
        while indice:
            indice, resto = divmod(indice - 1, 26)
            texto = chr(65 + resto) + texto
        return texto

    def carregar_csv(self, caminho: str) -> List[dict]:
        """Confere a gravação real e conserva a ordem original dos pacotes."""
        registros = []
        with Path(caminho).open("r", newline="", encoding="utf-8-sig") as arquivo:
            leitor = csv.DictReader(arquivo)
            if leitor.fieldnames is None or not set(self._TIPOS_CSV).issubset(leitor.fieldnames):
                raise ValueError("CSV não possui o cabeçalho gerado pelo monitor KY-037.")
            for indice, linha in enumerate(leitor, 1):
                try:
                    valor = int(linha["valor_adc"])
                    momento = datetime.fromisoformat(linha["horario_pc"])
                    placa = linha.get("timestamp_placa_ms", "").strip()
                    marca_placa = int(placa) if placa else None
                    if valor < 0 or (marca_placa is not None and marca_placa < 0):
                        raise ValueError("ADC/timestamp negativo")
                except (ValueError, TypeError, KeyError) as erro:
                    raise ValueError(f"Linha {indice + 1} do CSV inválida: {erro}") from erro
                registros.append({
                    "numero": indice,
                    "horario_pc": linha["horario_pc"],
                    "momento": momento,
                    "sensor": linha["sensor"],
                    "adc": valor,
                    "unidade": linha["unidade"],
                    "timestamp_placa_ms": marca_placa,
                    "origem": linha["ip_origem"],
                })
        if not registros:
            raise ValueError("O CSV de gravação não contém leituras.")
        inicio = registros[0]["momento"]
        for item in registros:
            item["segundos"] = max(0.0, (item["momento"] - inicio).total_seconds())
        return registros

    @staticmethod
    def _reduzir_serie(dados: Sequence[dict], max_pontos: int = 1800) -> List[dict]:
        """Mantém primeiro/último e extremos por faixa, sem alterar a aba bruta."""
        n = len(dados)
        if n <= max_pontos:
            return list(dados)
        baldes = max(1, (max_pontos - 2) // 2)
        selecionados = {0, n - 1}
        for balde in range(baldes):
            inicio = balde * n // baldes
            fim = min(n, (balde + 1) * n // baldes)
            if inicio >= fim:
                continue
            selecionados.add(min(range(inicio, fim), key=lambda p: dados[p]["adc"]))
            selecionados.add(max(range(inicio, fim), key=lambda p: dados[p]["adc"]))
        return [dados[i] for i in sorted(selecionados)]

    @staticmethod
    def _colher_alertas(eventos: Sequence[object], inicio: datetime,
                        fim: datetime) -> List[dict]:
        saida = []
        for evento in eventos:
            def propriedade(nome, padrao=""):
                return evento.get(nome, padrao) if isinstance(evento, dict) else getattr(evento, nome, padrao)
            horario = str(propriedade("horario_pc"))
            try:
                instante = datetime.fromisoformat(horario)
                periodo = inicio <= instante <= fim
            except (ValueError, TypeError):
                periodo = False
            saida.append({
                "horario_pc": horario,
                "sensor": propriedade("sensor"),
                "tipo": propriedade("tipo"),
                "valor": int(propriedade("valor", 0)),
                "unidade": propriedade("unidade"),
                "inferior": int(propriedade("limite_inferior", 0)),
                "superior": int(propriedade("limite_superior", 0)),
                "origem": propriedade("origem"),
                "reconhecido": str(propriedade("reconhecido", False)).lower() in ("true", "1", "sim"),
                "na_gravacao": periodo,
            })
        return saida

    def _celula(self, col: int, row: int, valor: object, estilo: int = 0) -> str:
        ref = f"{self._coluna(col)}{row}"
        if valor is None:
            return f'<c r="{ref}" s="{estilo}"/>'
        if isinstance(valor, bool):
            return f'<c r="{ref}" s="{estilo}" t="b"><v>{int(valor)}</v></c>'
        if isinstance(valor, (int, float)) and math.isfinite(valor):
            return f'<c r="{ref}" s="{estilo}"><v>{valor}</v></c>'
        texto = self._xml(valor)
        return (f'<c r="{ref}" s="{estilo}" t="inlineStr">'
                f'<is><t xml:space="preserve">{texto}</t></is></c>')

    def _linha(self, n: int, celulas: Sequence[tuple], altura: int = 0) -> str:
        ajuste = f' ht="{altura}" customHeight="1"' if altura else ""
        return (f'<row r="{n}"{ajuste}>' +
                "".join(self._celula(i, n, valor, estilo)
                        for i, (valor, estilo) in enumerate(celulas, 1)) + "</row>")

    @staticmethod
    def _cabecalho_xml() -> str:
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'

    def _planilha(self, linhas: Sequence[str], larguras: Sequence[float],
                   filtro: Optional[str] = None, desenho: bool = False,
                   mesclagens: Optional[List[str]] = None, congelar: int = 0) -> str:
        colunas = "".join(
            f'<col min="{i}" max="{i}" width="{largura}" customWidth="1"/>'
            for i, largura in enumerate(larguras, 1))
        vistas = ('<sheetViews><sheetView workbookViewId="0">'
                  + (f'<pane ySplit="{congelar}" topLeftCell="A{congelar + 1}" '
                     'activePane="bottomLeft" state="frozen"/>' if congelar else '')
                  + '</sheetView></sheetViews>')
        merges = ('<mergeCells count="{}">'.format(len(mesclagens))
                  + ''.join(f'<mergeCell ref="{m}"/>' for m in mesclagens)
                  + '</mergeCells>') if mesclagens else ''
        auto_filtro = f'<autoFilter ref="{filtro}"/>' if filtro else ''
        rels = ('<drawing r:id="rId1"/>' if desenho else '')
        return (self._cabecalho_xml()
                + '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                  'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                + vistas + '<sheetFormatPr defaultRowHeight="17"/>'
                + f'<cols>{colunas}</cols><sheetData>{"".join(linhas)}</sheetData>'
                + merges + auto_filtro + rels + '</worksheet>')

    def _estilos(self) -> str:
        fontes = [
            ('#152138', False, 11), ('#FFFFFF', True, 12), ('#FFFFFF', True, 22),
            ('#087A97', True, 15), ('#53677B', False, 10),
            ('#8F1832', True, 11), ('#1D6F51', True, 11),
        ]
        fxml = "".join(
            '<font><sz val="{}"/>{}<color rgb="FF{}"/><name val="Aptos"/></font>'.format(
                tamanho, '<b/>' if negrito else '', cor.lstrip('#'))
            for cor, negrito, tamanho in fontes)
        cores = ['#FFFFFF', '#14253E', '#087A97', '#ECF4FA', '#EDF6FA', '#FCE8EB', '#E7F7EF']
        fills = '<fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
        fills += "".join(
            f'<fill><patternFill patternType="solid"><fgColor rgb="FF{cor[1:]}"/>'
            '<bgColor indexed="64"/></patternFill></fill>' for cor in cores)
        # fontId, fillId, number format, aligned: styles 0...10
        estilos = [
            (0, 2, 0), (1, 3, 0), (2, 3, 0), (1, 4, 0), (3, 5, 0),
            (4, 2, 0), (0, 2, 2), (0, 2, 4), (5, 7, 0), (6, 8, 0),
            (0, 5, 0), (4, 4, 0),
        ]
        xfs = ''.join(
            f'<xf numFmtId="{num}" fontId="{fonte}" fillId="{fill}" borderId="0" '
            'xfId="0" applyFont="1" applyFill="1" applyNumberFormat="1">'
            '<alignment vertical="center"/></xf>'
            for fonte, fill, num in estilos)
        return (self._cabecalho_xml()
                + '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                + f'<fonts count="{len(fontes)}">{fxml}</fonts>'
                + f'<fills count="{len(cores) + 2}">{fills}</fills>'
                + '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
                + '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
                + f'<cellXfs count="{len(estilos)}">{xfs}</cellXfs>'
                + '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
                + '</styleSheet>')

    def _numero_cache(self, valores: Sequence[float], formato='General') -> str:
        pontos = ''.join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>'
                         for i, v in enumerate(valores))
        return f'<c:numCache><c:formatCode>{formato}</c:formatCode><c:ptCount val="{len(valores)}"/>{pontos}</c:numCache>'

    def _grafico_xml(self, serie: Sequence[dict]) -> str:
        """Gráfico XY sem rótulos por ponto e com eixos adequados à gravação.

        O limite inferior 0 não entra como série quando distorce a escala.
        Toda amostra permanece íntegra em Leituras / Serie Grafico.
        """
        n = len(serie) + 1
        xs = [round(p['segundos'], 3) for p in serie]
        adcs = [p['adc'] for p in serie]
        menor, maior = min(adcs), max(adcs)
        amplitude = max(1, maior - menor)
        margem = max(80, amplitude * 0.08)
        # Foco nos dados: evita que o limite inferior 0 comprima a curva.
        piso = max(0, 100 * math.floor((menor - margem) / 100))
        teto = 100 * math.ceil((maior + margem) / 100)
        if teto <= piso:
            teto = piso + 200
        # Limites só aparecem como linhas se estão dentro da área relevante.
        conjuntos = [('Leitura ADC', '#08B5C6', adcs, 'B')]
        if piso <= self._superior <= teto:
            conjuntos.append((f'Limite superior ({self._superior})', '#DE5066',
                              [self._superior] * len(serie), 'C'))
        if piso <= self._inferior <= teto:
            conjuntos.append((f'Limite inferior ({self._inferior})', '#9EA9B7',
                              [self._inferior] * len(serie), 'D'))

        ocultar_rotulos = ('<c:dLbls><c:showLegendKey val="0"/>'
                           '<c:showVal val="0"/><c:showCatName val="0"/>'
                           '<c:showSerName val="0"/><c:showPercent val="0"/>'
                           '<c:showBubbleSize val="0"/></c:dLbls>')
        partes = []
        for i, (nome, cor, valores, coluna) in enumerate(conjuntos):
            traco = '<a:prstDash val="dash"/>' if i else ''
            partes.append(
                f'<c:ser><c:idx val="{i}"/><c:order val="{i}"/>'
                f'<c:tx><c:v>{self._xml(nome)}</c:v></c:tx>'
                '<c:spPr><a:ln w="{}"><a:solidFill><a:srgbClr val="{}"/></a:solidFill>{}</a:ln></c:spPr>'.format(
                    25000 if i == 0 else 17000, cor[1:], traco)
                + '<c:marker><c:symbol val="none"/></c:marker>'
                + ocultar_rotulos
                + '<c:xVal><c:numRef><c:f>\'Serie Grafico\'!$A$2:$A${}</c:f>{}</c:numRef></c:xVal>'.format(
                    n, self._numero_cache(xs, '0.0'))
                + '<c:yVal><c:numRef><c:f>\'Serie Grafico\'!${}$2:${}${}</c:f>{}</c:numRef></c:yVal>'.format(
                    coluna, coluna, n, self._numero_cache(valores))
                + '<c:smooth val="0"/></c:ser>')
        duracao = max(xs[-1], 1) if xs else 1
        max_x = math.ceil(duracao / 5) * 5
        if max_x <= 0:
            max_x = 5
        # Cerca de 6-10 marcações no eixo de tempo, evitando 600 rótulos.
        passo_x = max(1, 5 * math.ceil((max_x / 8) / 5))
        # Marcas verticais em intervalos legíveis.
        delta_y = teto - piso
        passo_y = min((100, 200, 250, 500, 1000, 2000, 5000, 10000),
                      key=lambda k: abs(delta_y / k - 6))
        axis_x = (
            '<c:valAx><c:axId val="10"/><c:scaling><c:orientation val="minMax"/>'
            f'<c:max val="{max_x}"/><c:min val="0"/></c:scaling>'
            '<c:axPos val="b"/><c:numFmt formatCode="0" sourceLinked="0"/>'
            '<c:majorTickMark val="out"/><c:minorTickMark val="none"/>'
            '<c:tickLblPos val="nextTo"/>'
            f'<c:majorUnit val="{passo_x}"/>'
            '<c:crossAx val="20"/><c:crosses val="min"/></c:valAx>')
        axis_y = (
            '<c:valAx><c:axId val="20"/><c:scaling><c:orientation val="minMax"/>'
            f'<c:max val="{teto}"/><c:min val="{piso}"/></c:scaling>'
            '<c:axPos val="l"/><c:majorGridlines/>'
            '<c:numFmt formatCode="0" sourceLinked="0"/>'
            '<c:majorTickMark val="none"/><c:minorTickMark val="none"/>'
            '<c:tickLblPos val="nextTo"/>'
            f'<c:majorUnit val="{passo_y}"/>'
            '<c:crossAx val="10"/><c:crosses val="min"/></c:valAx>')
        return (
            self._cabecalho_xml()
            + '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
              'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            + '<c:chart><c:autoTitleDeleted val="1"/><c:plotArea><c:layout/>'
            + '<c:scatterChart><c:scatterStyle val="line"/><c:varyColors val="0"/>'
            + ''.join(partes)
            + ocultar_rotulos
            + '<c:axId val="10"/><c:axId val="20"/></c:scatterChart>'
            + axis_x + axis_y
            + '</c:plotArea><c:legend><c:legendPos val="b"/><c:layout/></c:legend>'
              '<c:plotVisOnly val="1"/><c:dispBlanksAs val="gap"/></c:chart>'
            + '</c:chartSpace>')

    def _desenho(self) -> str:
        return (self._cabecalho_xml()
                + '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
                  'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                  'xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
                  'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                  '<xdr:twoCellAnchor><xdr:from><xdr:col>5</xdr:col><xdr:colOff>0</xdr:colOff>'
                  '<xdr:row>7</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>'
                  '<xdr:to><xdr:col>16</xdr:col><xdr:colOff>0</xdr:colOff>'
                  '<xdr:row>34</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>'
                  '<xdr:graphicFrame macro=""><xdr:nvGraphicFramePr><xdr:cNvPr id="2" name="Grafico KY-037"/>'
                  '<xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr>'
                  '<xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm>'
                  '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">'
                  '<c:chart r:id="rId1"/></a:graphicData></a:graphic></xdr:graphicFrame>'
                  '<xdr:clientData/></xdr:twoCellAnchor></xdr:wsDr>')

    def _gerar_xml(self, registros: List[dict], eventos: List[dict]):
        numeros = [x['adc'] for x in registros]
        n = len(registros)
        duracao = round(registros[-1]['segundos'], 3)
        resumo = [
            self._linha(1, [("CENTRAL DE MONITORAMENTO  /  KY-037", 2)], 40),
            self._linha(2, [("RELATÓRIO DE TELEMETRIA • ADC BRUTO (NÃO dB)", 1)], 25),
            self._linha(4, [("AMOSTRAS", 3), (n, 4), ("MÉDIA ADC", 3), (round(statistics.mean(numeros), 2), 4),
                             ("MÁXIMO", 3), (max(numeros), 4), ("MÍNIMO", 3), (min(numeros), 4)], 31),
            self._linha(6, [("IDENTIFICAÇÃO DA SESSÃO", 3)], 27),
            self._linha(8, [("Início no PC", 5), (registros[0]['horario_pc'], 0)], 24),
            self._linha(9, [("Fim no PC", 5), (registros[-1]['horario_pc'], 0)], 24),
            self._linha(10, [("Duração (s)", 5), (duracao, 6)], 24),
            self._linha(11, [("Sensor", 5), (registros[0]['sensor'], 0)], 24),
            self._linha(12, [("IP de origem", 5), (registros[0]['origem'], 0)], 24),
            self._linha(13, [("Limite inferior*", 5), (self._inferior, 6)], 24),
            self._linha(14, [("Limite superior*", 5), (self._superior, 6)], 24),
            self._linha(15, [("Alertas registrados", 5), (len(eventos), 6)], 24),
            self._linha(16, [("Alertas na sessão", 5), (sum(e['na_gravacao'] for e in eventos), 6)], 24),
            self._linha(18, [("LEGENDA & CONFIABILIDADE", 3)], 25),
            self._linha(20, [("Gráfico XY", 5), ("Tempo transcorrido do PC × ADC bruto", 0)]),
            self._linha(21, [("*Limites", 5), ("Referência atual aplicada retrospectivamente", 0)]),
            self._linha(22, [("Horários", 5), ("Usados: relógio do PC, não da STM32", 0)]),
            self._linha(23, [("Alertas", 5), ("Somente eventos realmente salvos pela GUI", 0)]),
            self._linha(24, [("Gráfico", 5), ("Extremos preservados na redução visual", 0)]),
            self._linha(25, [("Leituras", 5), ("Dados originais sem arredondamento", 0)]),
        ]
        colunas_painel = [19, 22, 16, 19, 16, 17, 17, 17, 14, 14, 14, 14, 14, 14, 14, 14, 14]
        resumo_xml = self._planilha(resumo, colunas_painel, desenho=True,
                                   mesclagens=["A1:Q1", "A2:Q2", "A6:D6", "A18:D18"])
        titulos = ["Nº", "Horário PC (ISO 8601)", "Tempo desde início (s)", "ADC bruto",
                   "Sensor", "Unidade", "Timestamp placa (ms)", "IP origem", "Acima do limite*?"]
        medicao = [self._linha(1, [(v, 3) for v in titulos], 30)]
        for index, leitura in enumerate(registros, 2):
            medicao.append(self._linha(index, [
                (leitura['numero'], 0), (leitura['horario_pc'], 0),
                (round(leitura['segundos'], 3), 7), (leitura['adc'], 8 if leitura['adc'] > self._superior else 6),
                (leitura['sensor'], 0), (leitura['unidade'], 0),
                (leitura['timestamp_placa_ms'], 0), (leitura['origem'], 0),
                ("SIM" if leitura['adc'] > self._superior else "NÃO", 8 if leitura['adc'] > self._superior else 0),
            ]))
        medicoes_xml = self._planilha(medicao, [9, 33, 21, 15, 17, 12, 24, 18, 24],
                                     filtro=f"A1:I{n+1}", congelar=1)
        titulos_alerta = ["Horário PC", "Sensor", "Evento", "ADC", "Unidade", "Limite inf.",
                          "Limite sup.", "IP origem", "Reconhecido", "Nesta gravação?"]
        alertas = [self._linha(1, [(v, 3) for v in titulos_alerta], 30)]
        for i, evento in enumerate(eventos, 2):
            estilo = 8 if evento['tipo'] in ("ACIMA", "ABAIXO") else 9
            alertas.append(self._linha(i, [
                (evento['horario_pc'], 0), (evento['sensor'], 0), (evento['tipo'], estilo),
                (evento['valor'], 6), (evento['unidade'], 0), (evento['inferior'], 0),
                (evento['superior'], 0), (evento['origem'], 0),
                ("SIM" if evento['reconhecido'] else "NÃO", 0),
                ("SIM" if evento['na_gravacao'] else "NÃO", 0),
            ]))
        if not eventos:
            alertas.append(self._linha(3, [("Nenhum evento persistido em alertas_ky037.csv foi fornecido para este relatório.", 5)]))
        alertas_xml = self._planilha(alertas, [34, 17, 18, 12, 12, 14, 14, 20, 16, 20],
                                    filtro=f"A1:J{len(eventos)+1}" if eventos else None, congelar=1)
        grafico = [self._linha(1, [("Tempo transcorrido (s)", 3), ("Leitura ADC bruto", 3),
                                    ("Limite superior", 3), ("Limite inferior", 3)], 30)]
        serie = self._reduzir_serie(registros)
        for i, item in enumerate(serie, 2):
            grafico.append(self._linha(i, [(round(item['segundos'], 3), 7), (item['adc'], 6),
                                          (self._superior, 6), (self._inferior, 6)]))
        grafico_xml = self._planilha(grafico, [25, 22, 20, 20], congelar=1)
        return resumo_xml, medicoes_xml, alertas_xml, grafico_xml, serie

    def gerar(self, caminho_csv: str, destino_xlsx: str, eventos: Sequence[object] = ()) -> dict:
        """Gera um relatório da gravação selecionada, com alertas persistidos.

        Não altera o CSV, não cria falsos eventos e não depende de pip install.
        O histórico de eventos pode incluir outras sessões, sinalizadas por coluna.
        """
        registros = self.carregar_csv(caminho_csv)
        primeiro, ultimo = registros[0]['momento'], registros[-1]['momento']
        eventos_normalizados = self._colher_alertas(eventos, primeiro, ultimo)
        painel, leituras, alertas, serie_dados, serie = self._gerar_xml(registros, eventos_normalizados)
        destino = Path(destino_xlsx)
        destino.parent.mkdir(parents=True, exist_ok=True)
        tipos = (self._cabecalho_xml() +
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet4.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>'
            '<Override PartName="/xl/charts/chart1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>'
            '</Types>')
        rels_base = ('<?xml version="1.0" encoding="UTF-8"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">')
        rels_raiz = (rels_base + '<Relationship Id="rId1" '
                     'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                     'Target="xl/workbook.xml"/></Relationships>')
        pastas = ["Visao Geral", "Leituras", "Alertas", "Serie Grafico"]
        livro = (self._cabecalho_xml()
                 + '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   '<bookViews><workbookView activeTab="0"/></bookViews><sheets>'
                 + ''.join(f'<sheet name="{nome}" sheetId="{i}" r:id="rId{i}"/>'
                           for i, nome in enumerate(pastas, 1))
                 + '</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
        workbook_rels = (rels_base + ''.join(
            '<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet{}.xml"/>'.format(i, i) for i in range(1, 5))
            + '<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
              'Target="styles.xml"/></Relationships>')
        draw_rel = (rels_base + '<Relationship Id="rId1" '
                    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" '
                    'Target="../drawings/drawing1.xml"/></Relationships>')
        chart_rel = (rels_base + '<Relationship Id="rId1" '
                     'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" '
                     'Target="../charts/chart1.xml"/></Relationships>')
        try:
            with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as arq:
                partes = {
                    "[Content_Types].xml": tipos,
                    "_rels/.rels": rels_raiz,
                    "xl/workbook.xml": livro,
                    "xl/_rels/workbook.xml.rels": workbook_rels,
                    "xl/styles.xml": self._estilos(),
                    "xl/worksheets/sheet1.xml": painel,
                    "xl/worksheets/sheet2.xml": leituras,
                    "xl/worksheets/sheet3.xml": alertas,
                    "xl/worksheets/sheet4.xml": serie_dados,
                    "xl/worksheets/_rels/sheet1.xml.rels": draw_rel,
                    "xl/drawings/drawing1.xml": self._desenho(),
                    "xl/drawings/_rels/drawing1.xml.rels": chart_rel,
                    "xl/charts/chart1.xml": self._grafico_xml(serie),
                }
                for nome, conteudo in partes.items():
                    arq.writestr(nome, conteudo.encode("utf-8"))
        except Exception:
            if destino.exists():
                destino.unlink()
            raise
        return {"amostras": len(registros), "pontos_grafico": len(serie),
                "alertas": len(eventos_normalizados),
                "alertas_na_gravacao": sum(x["na_gravacao"] for x in eventos_normalizados)}
