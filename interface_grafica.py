#!/usr/bin/env python3
"""Entrega 4: interface Tkinter do servidor central KY-037.

Recepcao UDP em thread, atualizacao grafica na thread principal, historico
movel de 30 s a 30 min, alerta por limites e gravacao/exportacao CSV.
"""

import argparse
import queue
import time
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from relatorio_excel import RelatorioExcel

from telemetria_gui import (
    DecodificadorTelemetria, GravadorCSV, HistoricoLeituras,
    LeituraSom, ReceptorUDP, AnaliseLeituras, DetectorEventos, HistoricoAlertas,
    EventoAlerta,
)


class InterfaceMonitoramento:
    """Controla os widgets, o historico e o ciclo de vida do receptor UDP."""

    def __init__(self, janela: tk.Tk, porta: int = 8080,
                 caminho_alertas: str = "alertas_ky037.csv") -> None:
        self._janela = janela
        # Paleta consistente: painel operacional noturno, acento ciano e estados
        # semanticamente distintos. Tkinter puro: funciona no Windows sem pip.
        self._cores = {
            "fundo": "#071320", "cartao": "#112339", "grafico": "#0B1A2C",
            "texto": "#F4F8FC", "suave": "#96ABC3", "azul": "#57D7E8",
            "verde": "#38DCA9", "vermelho": "#FB7587", "grade": "#294059",
            "amarelo": "#F9C96E", "borda": "#233C55", "area": "#15364A",
            "escuro": "#06111E", "botao_sec": "#93A8C2",
        }
        self._fila: "queue.Queue" = queue.Queue(maxsize=20000)
        self._receptor: Optional[ReceptorUDP] = None
        self._decodificador = DecodificadorTelemetria()
        self._historico = HistoricoLeituras(janela_maxima_s=1800, max_amostras=60000)
        self._gravador = GravadorCSV()
        self._analise = AnaliseLeituras()
        self._detector_alertas = DetectorEventos()
        # Persistencia local automatica: o arquivo acompanha a pasta de execucao no PC.
        self._alertas = HistoricoAlertas(caminho_alertas)
        # Painel independente do arquivo historico: zerar a visualizacao
        # nunca remove ou modifica eventos persistidos em CSV.
        self._eventos_painel: List[EventoAlerta] = self._alertas.listar()
        self._quantidade = 0
        self._invalidos = 0
        self._ultimo: Optional[LeituraSom] = None
        self._ativo = True
        self._compacto = False
        self._limite_inferior = 0
        self._limite_superior = 5000  # Contagens ADC; configuravel na tela.
        self._porta_var = tk.StringVar(value=str(porta))
        self._inferior_var = tk.StringVar(value="0")
        self._superior_var = tk.StringVar(value="5000")
        self._janela_var = tk.StringVar(value="60 s")
        self._escala_var = tk.StringVar(value="Automática")
        self._escala_info_var = tk.StringVar(value="Escala automática: todos os valores visíveis")
        self._media_var = tk.StringVar(value="—")
        self._minimo_var = tk.StringVar(value="—")
        self._maximo_var = tk.StringVar(value="—")
        self._amostras_var = tk.StringVar(value="0 amostras na janela")
        self._resumo_alertas_var = tk.StringVar(value="0 eventos")
        self._detalhe_alerta_var = tk.StringVar(value="Selecione um evento para detalhes")
        self._erro_alertas_var = tk.StringVar(value="")
        self._recepcao_var = tk.StringVar(value="RECEPTOR PARADO")
        self._valor_var = tk.StringVar(value="—")
        self._sensor_var = tk.StringVar(value="Aguardando pacotes...")
        self._estado_var = tk.StringVar(value="AGUARDANDO")
        self._total_var = tk.StringVar(value="0 válidos  |  0 inválidos")
        self._ultima_var = tk.StringVar(value="Nenhuma leitura recebida")
        self._arquivo_var = tk.StringVar(value="Gravação desativada")
        self._resumo_compacto_var = tk.StringVar(value="Aguardando leituras da STM32...")
        self._origem_var = tk.StringVar(value="Origem: —")
        self._marca_estado_var = tk.StringVar(value="●  AGUARDANDO SINAL")
        self._ultimo_csv_gravado: Optional[str] = None
        self._janela.title("SINAL / KY-037  •  Central de Monitoramento")
        largura = min(1220, max(920, self._janela.winfo_screenwidth() - 80))
        altura = min(850, max(620, self._janela.winfo_screenheight() - 90))
        self._janela.geometry(f"{largura}x{altura}")
        self._janela.minsize(900, 600)
        self._janela.configure(bg=self._cores["fundo"])
        self._janela.protocol("WM_DELETE_WINDOW", self._fechar)
        self._montar_interface()
        self._janela.bind("<Configure>", self._reagir_redimensionamento)
        self._janela.after_idle(self._ajustar_layout)
        self._atualizar_lista_alertas()
        self._iniciar_receptor()
        self._janela.after(100, self._atualizar)

    def _rotulo(self, pai: tk.Misc, texto: str, tamanho: int = 11, negrito: bool = False,
                cor: Optional[str] = None, fundo: Optional[str] = None) -> tk.Label:
        return tk.Label(
            pai, text=texto, bg=fundo or self._cores["cartao"],
            fg=cor or self._cores["texto"],
            font=("Segoe UI", tamanho, "bold" if negrito else "normal"),
            anchor="w",
        )

    def _botao(self, pai: tk.Misc, texto: str, acao, cor: Optional[str] = None) -> tk.Button:
        base = cor or self._cores["azul"]
        botao = tk.Button(
            pai, text=texto, command=acao, bg=base,
            fg=self._cores["escuro"], activebackground="#E8F8FB",
            activeforeground=self._cores["escuro"],
            font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
            padx=13, pady=7, cursor="hand2", highlightthickness=0,
        )
        botao.bind("<Enter>", lambda _e, controle=botao: controle.config(bg="#B9F4F5"))
        botao.bind("<Leave>", lambda _e, controle=botao, fundo=base: controle.config(bg=fundo))
        return botao

    def _cartao(self, pai: tk.Misc, margem: int = 0) -> tk.Frame:
        return tk.Frame(
            pai, bg=self._cores["cartao"], padx=12, pady=8,
            highlightthickness=1, highlightbackground=self._cores["borda"],
        )

    def _montar_interface(self) -> None:
        """Prioriza o grafico: sem painel lateral que possa esmagar o Canvas.

        As notificacoes continuam acessiveis na aba Alertas. O grafico ocupa
        toda a largura e recebe a altura restante ao redimensionar a janela.
        """
        fundo = self._janela
        cabecalho = tk.Frame(fundo, bg=self._cores["fundo"])
        cabecalho.pack(fill="x", padx=15, pady=(9, 7))
        assinatura = tk.Canvas(cabecalho, width=45, height=45, bg=self._cores["fundo"],
                              highlightthickness=0)
        assinatura.pack(side="left", padx=(0, 12))
        assinatura.create_oval(2, 2, 43, 43, outline=self._cores["borda"], width=2,
                              fill=self._cores["cartao"])
        assinatura.create_line(8, 24, 15, 24, 19, 13, 24, 34, 29, 18, 33, 24,
                              38, 24, fill=self._cores["azul"], width=2, smooth=False)
        titular = tk.Frame(cabecalho, bg=self._cores["fundo"])
        titular.pack(side="left", fill="x", expand=True)
        self._rotulo(titular, "SINAL  /  CENTRO DE TELEMETRIA", 8, True,
                     cor=self._cores["azul"], fundo=self._cores["fundo"]).pack(anchor="w")
        self._rotulo(titular, "Monitoramento de som  ·  KY-037", 18, True,
                     fundo=self._cores["fundo"]).pack(anchor="w")
        self._rotulo(titular, "STM32MP1-DK1  →  UDP  →  PC     •     Leitura ADC bruto (não dB)",
                     9, cor=self._cores["suave"], fundo=self._cores["fundo"]).pack(anchor="w")
        chip = tk.Frame(cabecalho, bg=self._cores["cartao"], padx=12, pady=9,
                        highlightthickness=1, highlightbackground=self._cores["borda"])
        chip.pack(side="right", padx=(8, 0))
        self._marca_estado = self._rotulo(chip, "", 9, True, self._cores["amarelo"])
        self._marca_estado.configure(textvariable=self._marca_estado_var)
        self._marca_estado.pack()

        conexao = self._cartao(fundo)
        conexao.pack(fill="x", padx=15, pady=(0, 5))
        linha = tk.Frame(conexao, bg=self._cores["cartao"])
        linha.pack(fill="x")
        self._rotulo(linha, "Porta UDP:", 9).pack(side="left")
        tk.Entry(linha, textvariable=self._porta_var, width=7, font=("Arial", 10),
                 justify="center").pack(side="left", padx=(7, 9))
        self._botao(linha, "Iniciar / reiniciar", self._iniciar_receptor).pack(side="left", padx=(0, 7))
        self._botao(linha, "Parar receptor", self._parar_receptor,
                    self._cores["botao_sec"]).pack(side="left")
        self._rotulo(linha, "0.0.0.0 · todas as interfaces", 9,
                     cor=self._cores["suave"]).pack(side="right")
        self._rotulo_status = self._rotulo(conexao, "", 9, cor=self._cores["verde"])
        self._rotulo_status.config(textvariable=self._recepcao_var)
        self._rotulo_status.pack(anchor="w", pady=(3, 0))

        indicadores = tk.Frame(fundo, bg=self._cores["fundo"])
        indicadores.pack(fill="x", padx=15, pady=(0, 5))
        self._criar_indicador(indicadores, "VALOR ATUAL", self._valor_var,
                             20, self._cores["azul"], 0)
        self._rotulo_atual_estado = self._criar_indicador(
            indicadores, "ESTADO", self._estado_var, 14, self._cores["suave"], 1)
        self._criar_indicador(indicadores, "PACOTES", self._total_var,
                             10, self._cores["texto"], 2)
        self._criar_indicador(indicadores, "ÚLTIMA ATUALIZAÇÃO", self._ultima_var,
                             10, self._cores["texto"], 3)
        for coluna in range(4):
            indicadores.grid_columnconfigure(coluna, weight=1, uniform="indicadores")

        self._indicadores_frame = indicadores
        estatisticas = tk.Frame(fundo, bg=self._cores["fundo"])
        estatisticas.pack(fill="x", padx=15, pady=(0, 5))
        for coluna, (titulo, variavel) in enumerate((
            ("MÉDIA DA JANELA", self._media_var),
            ("MÍNIMO DA JANELA", self._minimo_var),
            ("MÁXIMO DA JANELA", self._maximo_var),
        )):
            self._criar_indicador(estatisticas, titulo, variavel, 13,
                                  self._cores["azul"], coluna)
        for coluna in range(3):
            estatisticas.grid_columnconfigure(coluna, weight=1, uniform="estatisticas")

        self._estatisticas_frame = estatisticas
        # Em janelas pequenas, um resumo compacto substitui os sete cartoes.
        self._barra_compacta = self._cartao(fundo)
        compacto = self._rotulo(self._barra_compacta, "", 10, True)
        compacto.config(textvariable=self._resumo_compacto_var)
        compacto.pack(fill="x")

        ajustes = self._cartao(fundo)
        self._ajustes_frame = ajustes
        ajustes.pack(fill="x", padx=15, pady=(0, 5))
        linha2 = tk.Frame(ajustes, bg=self._cores["cartao"])
        linha2.pack(fill="x")
        self._rotulo(linha2, "Abaixo de:", 9).pack(side="left")
        tk.Entry(linha2, textvariable=self._inferior_var, width=6,
                 justify="center").pack(side="left", padx=(5, 9))
        self._rotulo(linha2, "Acima de:", 9).pack(side="left")
        tk.Entry(linha2, textvariable=self._superior_var, width=7,
                 justify="center").pack(side="left", padx=(5, 9))
        self._botao(linha2, "Aplicar limites", self._aplicar_limites).pack(side="left")
        self._rotulo(linha2, "Histórico:", 9).pack(side="left", padx=(14, 5))
        ttk.Combobox(linha2, width=7, state="readonly",
                     values=("30 s", "60 s", "5 min", "10 min", "30 min"),
                     textvariable=self._janela_var).pack(side="left")
        self._rotulo(linha2, "Escala:", 9).pack(side="left", padx=(12, 5))
        ttk.Combobox(linha2, width=11, state="readonly",
                     values=("Automática", "Ampliada"),
                     textvariable=self._escala_var).pack(side="left")

        rodape = self._cartao(fundo)
        rodape.pack(side="bottom", fill="x", padx=15, pady=(0, 10))
        linha3 = tk.Frame(rodape, bg=self._cores["cartao"])
        linha3.pack(fill="x")
        self._botao(linha3, "●  Gravar CSV", self._iniciar_gravacao).pack(
            side="left", padx=(0, 7))
        self._botao(linha3, "Parar gravação", self._parar_gravacao,
                    self._cores["botao_sec"]).pack(side="left", padx=(0, 7))
        self._botao(linha3, "Exportar CSV", self._exportar_historico).pack(
            side="left", padx=(0, 7))
        self._botao(linha3, "▦  Relatório Excel", self._exportar_excel,
                    self._cores["verde"]).pack(side="left", padx=(0, 7))
        self._botao(linha3, "Limpar gráfico", self._limpar_historico,
                    self._cores["botao_sec"]).pack(side="left")
        etiqueta = self._rotulo(rodape, "", 9, cor=self._cores["suave"])
        etiqueta.config(textvariable=self._arquivo_var)
        etiqueta.pack(anchor="w", pady=(4, 0))
        etiqueta_origem = self._rotulo(rodape, "", 9, cor=self._cores["suave"])
        self._etiqueta_origem = etiqueta_origem
        etiqueta_origem.config(textvariable=self._origem_var)
        etiqueta_origem.pack(anchor="w")

        # Notebook: em janelas estreitas o grafico nao divide largura com alertas.
        estilo = ttk.Style(self._janela)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("Monitor.TNotebook", background=self._cores["fundo"],
                         borderwidth=0, padding=0)
        estilo.configure("Monitor.TNotebook.Tab", font=("Segoe UI", 10, "bold"),
                         padding=(16, 6), background=self._cores["cartao"],
                         foreground=self._cores["suave"], borderwidth=0)
        estilo.map("Monitor.TNotebook.Tab",
                   background=[("selected", self._cores["azul"])],
                   foreground=[("selected", self._cores["escuro"])])
        estilo.configure("Monitor.TCombobox", fieldbackground="#EAF5FB",
                         background="#EAF5FB", foreground="#081828", padding=3)
        self._abas = ttk.Notebook(fundo, style="Monitor.TNotebook")
        self._abas.pack(fill="both", expand=True, padx=15, pady=(0, 7))
        aba_grafico = tk.Frame(self._abas, bg=self._cores["cartao"])
        aba_alertas = tk.Frame(self._abas, bg=self._cores["cartao"])
        self._abas.add(aba_grafico, text="GRÁFICO · TEMPO REAL")
        self._abas.add(aba_alertas, text="HISTÓRICO DE ALERTAS")

        topo = tk.Frame(aba_grafico, bg=self._cores["cartao"])
        topo.pack(fill="x", padx=12, pady=(6, 0))
        self._rotulo(topo, "CURVA DE TELEMETRIA", 12, True).pack(side="left")
        contagem = self._rotulo(topo, "", 9, cor=self._cores["suave"])
        contagem.config(textvariable=self._amostras_var)
        contagem.pack(side="right")
        self._rotulo(topo, "●  ADC bruto     ┄  Limite superior", 9,
                     cor=self._cores["azul"]).pack(side="right", padx=(0, 18))
        etiqueta_escala = self._rotulo(aba_grafico, "", 9, cor=self._cores["amarelo"])
        etiqueta_escala.config(textvariable=self._escala_info_var)
        etiqueta_escala.pack(fill="x", padx=12, pady=(1, 0))
        self._grafico = tk.Canvas(aba_grafico, bg=self._cores["grafico"],
                                 highlightthickness=0, height=300, cursor="crosshair")
        self._grafico.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        # Aba separada: conserva as tres melhorias sem reduzir o grafico.
        quadro_alertas = self._cartao(aba_alertas)
        quadro_alertas.pack(fill="both", expand=True)
        self._rotulo(quadro_alertas, "HISTÓRICO DE ALERTAS", 12, True).pack(anchor="w")
        resumo = self._rotulo(quadro_alertas, "", 9, cor=self._cores["amarelo"])
        resumo.config(textvariable=self._resumo_alertas_var)
        resumo.pack(anchor="w", pady=(3, 4))
        lista_frame = tk.Frame(quadro_alertas, bg=self._cores["cartao"])
        lista_frame.pack(fill="both", expand=True)
        self._lista_alertas = tk.Listbox(
            lista_frame, bg=self._cores["grafico"], fg=self._cores["texto"],
            selectbackground=self._cores["azul"], selectforeground="#071522",
            relief="flat", font=("Consolas", 10), highlightthickness=0,
            activestyle="none", exportselection=False,
        )
        self._lista_alertas.pack(side="left", fill="both", expand=True)
        barra = tk.Scrollbar(lista_frame, command=self._lista_alertas.yview)
        barra.pack(side="right", fill="y")
        self._lista_alertas.configure(yscrollcommand=barra.set)
        self._lista_alertas.bind("<<ListboxSelect>>", self._selecionar_alerta)
        detalhe = self._rotulo(quadro_alertas, "", 9, cor=self._cores["suave"])
        detalhe.config(textvariable=self._detalhe_alerta_var, wraplength=650, justify="left")
        detalhe.pack(anchor="w", pady=(5, 3))
        acoes_alertas = tk.Frame(quadro_alertas, bg=self._cores["cartao"])
        acoes_alertas.pack(fill="x", pady=(2, 4))
        self._botao(acoes_alertas, "Reconhecer alertas", self._reconhecer_alertas,
                    self._cores["suave"]).pack(side="left", padx=(0, 8))
        self._botao(acoes_alertas, "Zerar painel (preserva CSV)", self._limpar_alertas,
                    self._cores["botao_sec"]).pack(side="left")
        self._rotulo(quadro_alertas,
                     f"Painel da sessão • registro histórico preservado em: {self._alertas.caminho.name}",
                     8, cor=self._cores["suave"]).pack(anchor="w")
        aviso = self._rotulo(quadro_alertas, "", 8, cor=self._cores["vermelho"])
        aviso.config(textvariable=self._erro_alertas_var, wraplength=650)
        aviso.pack(anchor="w")

    def _reagir_redimensionamento(self, evento) -> None:
        if evento.widget is self._janela:
            self._ajustar_layout()

    def _ajustar_layout(self) -> None:
        """Modo compacto garante que o Canvas ainda apareca em janela pequena."""
        compacto = self._janela.winfo_height() < 735
        if compacto == self._compacto:
            return
        self._compacto = compacto
        if compacto:
            self._indicadores_frame.pack_forget()
            self._estatisticas_frame.pack_forget()
            self._barra_compacta.pack(fill="x", padx=15, pady=(0, 5),
                                     before=self._ajustes_frame)
            self._etiqueta_origem.pack_forget()
        else:
            self._barra_compacta.pack_forget()
            self._indicadores_frame.pack(fill="x", padx=15, pady=(0, 5),
                                        before=self._ajustes_frame)
            self._estatisticas_frame.pack(fill="x", padx=15, pady=(0, 5),
                                         before=self._ajustes_frame)
            self._etiqueta_origem.pack(anchor="w")

    def _criar_indicador(self, pai: tk.Frame, titulo: str, variavel: tk.StringVar,
                         tamanho: int, cor: str, coluna: int) -> tk.Label:
        cartao = self._cartao(pai)
        cartao.grid(row=0, column=coluna, sticky="nsew", padx=(0 if coluna == 0 else 4,
                                                               0 if coluna == 3 else 4))
        faixa = tk.Frame(cartao, bg=cor, width=3, height=28)
        faixa.pack(side="left", fill="y", padx=(0, 10))
        conteudo = tk.Frame(cartao, bg=self._cores["cartao"])
        conteudo.pack(side="left", fill="both", expand=True)
        self._rotulo(conteudo, titulo, 9, True, self._cores["suave"]).pack(anchor="w")
        etiqueta = self._rotulo(conteudo, "", tamanho, True, cor)
        etiqueta.config(textvariable=variavel)
        etiqueta.pack(anchor="w", pady=(2, 0))
        return etiqueta

    def _iniciar_receptor(self) -> None:
        try:
            porta = int(self._porta_var.get())
            if not 1 <= porta <= 65535:
                raise ValueError("Use uma porta entre 1 e 65535.")
        except ValueError:
            messagebox.showerror("Porta inválida", "Informe uma porta UDP válida (1 a 65535).")
            return
        self._parar_receptor()
        try:
            self._receptor = ReceptorUDP(self._fila, "0.0.0.0", porta)
            self._receptor.iniciar()
        except OSError as erro:
            self._receptor = None
            self._recepcao_var.set("ERRO: não foi possível iniciar o receptor")
            self._rotulo_status.config(fg=self._cores["vermelho"])
            messagebox.showerror("Erro de rede", f"Porta {porta} indisponível:\n{erro}")
            return
        self._recepcao_var.set(f"RECEPTOR ATIVO  •  UDP {porta}  •  aguardando dados")
        self._rotulo_status.config(fg=self._cores["verde"])
        self._marca_estado_var.set(f"●  UDP {porta} ATIVO")
        self._marca_estado.config(fg=self._cores["verde"])

    def _parar_receptor(self) -> None:
        if self._receptor is not None:
            self._receptor.fechar()
            self._receptor = None
        self._recepcao_var.set("RECEPTOR PARADO")
        self._marca_estado_var.set("●  RECEPTOR PARADO")
        self._marca_estado.config(fg=self._cores["amarelo"])
        if hasattr(self, "_rotulo_status"):
            self._rotulo_status.config(fg=self._cores["suave"])

    def _aplicar_limites(self) -> None:
        try:
            inferior = int(self._inferior_var.get())
            superior = int(self._superior_var.get())
            if inferior < 0 or superior <= inferior:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Limites inválidos", "Use inteiros não negativos, com inferior < superior.")
            return
        self._limite_inferior, self._limite_superior = inferior, superior
        self._detector_alertas.reiniciar()
        self._atualizar_estado()

    def _janela_segundos(self) -> int:
        """Converte a janela escolhida em segundos; toda a serie continua em RAM."""
        return {"30 s": 30, "60 s": 60, "5 min": 300,
                "10 min": 600, "30 min": 1800}.get(self._janela_var.get(), 60)

    def _tempo_referencia(self) -> float:
        """Mantem o ultimo grafico visivel apos a transmissao parar."""
        agora = time.monotonic()
        if self._ultimo is not None and agora - self._ultimo.tempo_monotonico_pc > 5.0:
            return self._ultimo.tempo_monotonico_pc
        return agora

    @staticmethod
    def _legenda_tempo(segundos: int) -> str:
        if segundos < 60:
            return f"{segundos} s"
        minutos, resto = divmod(segundos, 60)
        return f"{minutos} min" if resto == 0 else f"{minutos}m{resto:02d}s"

    def _consumir_leitura(self, leitura: LeituraSom) -> None:
        self._historico.adicionar(leitura)
        evento = self._detector_alertas.avaliar(
            leitura, self._limite_inferior, self._limite_superior)
        if evento is not None:
            try:
                self._alertas.registrar(evento)
                self._erro_alertas_var.set("")
            except OSError as erro:
                self._erro_alertas_var.set(f"Erro salvando alertas: {erro}")
            # Mesmo em caso de erro de disco, o novo evento aparece na tela.
            self._eventos_painel.append(evento)
            if len(self._eventos_painel) > 500:
                self._eventos_painel.pop(0)
            self._atualizar_lista_alertas()
        self._ultimo = leitura
        self._quantidade += 1
        self._valor_var.set(f"{leitura.valor:,}".replace(",", ".") + f" {leitura.unidade}")
        self._sensor_var.set(leitura.sensor)
        self._origem_var.set(f"Sensor: {leitura.sensor}    •    Origem: {leitura.origem}"
                             f"    •    Horário do PC: {leitura.horario_pc}")
        if self._gravador.gravando:
            try:
                self._gravador.registrar(leitura)
            except OSError as erro:
                self._gravador.parar()
                self._arquivo_var.set(f"ERRO ao gravar CSV: {erro}")

    def _atualizar_estado(self) -> None:
        if self._ultimo is None:
            self._estado_var.set("AGUARDANDO")
            cor = self._cores["suave"]
        elif time.monotonic() - self._ultimo.tempo_monotonico_pc > 5.0:
            self._estado_var.set("SEM DADOS")
            cor = self._cores["amarelo"]
        elif self._ultimo.valor < self._limite_inferior or self._ultimo.valor > self._limite_superior:
            self._estado_var.set("ALERTA!")
            cor = self._cores["vermelho"]
        else:
            self._estado_var.set("NORMAL")
            cor = self._cores["verde"]
        self._rotulo_atual_estado.config(fg=cor)
        if self._ultimo is not None and self._receptor is not None:
            self._marca_estado_var.set(f"●  {self._estado_var.get()}")
            self._marca_estado.config(fg=cor)
        if self._ultimo is not None:
            idade = max(0, int(time.monotonic() - self._ultimo.tempo_monotonico_pc))
            self._ultima_var.set(f"Há {idade} s")

    def _atualizar(self) -> None:
        if not self._ativo:
            return
        for _ in range(800):
            try:
                tipo, conteudo, origem = self._fila.get_nowait()
            except queue.Empty:
                break
            if tipo == "erro":
                self._recepcao_var.set(f"ERRO DE REDE: {conteudo}")
                self._rotulo_status.config(fg=self._cores["vermelho"])
            else:
                try:
                    self._consumir_leitura(self._decodificador.decodificar(conteudo, origem))
                except ValueError:
                    self._invalidos += 1
        fila_perdida = self._receptor.descartados_fila if self._receptor is not None else 0
        self._total_var.set(f"{self._quantidade} válidos | {self._invalidos} inválidos"
                            + (f" | {fila_perdida} descartados" if fila_perdida else ""))
        if self._receptor is not None and self._ultimo is not None:
            inativo = time.monotonic() - self._ultimo.tempo_monotonico_pc > 5.0
            situacao = "sem novos dados" if inativo else "recebendo dados"
            self._recepcao_var.set(
                f"RECEPTOR ATIVO  •  UDP {self._receptor.porta}  •  {situacao}")
        self._atualizar_estado()
        self._atualizar_estatisticas()
        self._resumo_compacto_var.set(
            f"ADC {self._valor_var.get()}  |  {self._estado_var.get()}"
            f"  |  {self._quantidade} pacotes  |  Média {self._media_var.get()}"
            f"  |  Mín {self._minimo_var.get()}  |  Máx {self._maximo_var.get()}")
        self._desenhar_grafico()
        self._janela.after(150, self._atualizar)

    def _desenhar_grafico(self) -> None:
        tela = self._grafico
        tela.delete("all")
        largura = tela.winfo_width()
        altura = tela.winfo_height()
        if largura < 150 or altura < 100:
            return
        cor = self._cores
        margem_esq, margem_dir, margem_sup, margem_inf = 65, 20, 24, 36
        x0, x1 = margem_esq, largura - margem_dir
        y0, y1 = margem_sup, altura - margem_inf
        tempo_atual = self._tempo_referencia()
        janela = self._janela_segundos()
        pontos = self._historico.recentes(janela, agora=tempo_atual)
        if not pontos:
            tela.create_text(largura // 2, altura // 2,
                             text="Aguardando leituras recebidas pela rede UDP...",
                             fill=cor["suave"], font=("Arial", 13))
            return

        valores = [p.valor for p in pontos]
        # Apenas a renderizacao e reduzida; CSV, estatisticas e alertas
        # continuam utilizando todas as leituras originais na memoria.
        pontos_desenho = self._analise.reduzir_para_grafico(
            pontos, max(1, int(x1 - x0)))
        ampliada = self._escala_var.get() == "Ampliada"
        escala = self._analise.escala(valores, ampliada=ampliada)
        y_min, y_max = escala.minimo, escala.maximo
        if ampliada and (escala.acima or escala.abaixo):
            self._escala_info_var.set(
                f"Escala ampliada • {escala.acima} acima, {escala.abaixo} abaixo"
                f" • máximo real {escala.maximo_real:,}".replace(",", "."))
        elif ampliada:
            self._escala_info_var.set("Escala ampliada • sem picos fora da faixa")
        else:
            self._escala_info_var.set("Escala automática • todos os valores visíveis")

        def coord_x(momento: float) -> float:
            return x1 - ((tempo_atual - momento) / janela) * (x1 - x0)

        def coord_y(valor: float) -> float:
            return y1 - ((valor - y_min) / (y_max - y_min)) * (y1 - y0)

        # Painel de plotagem: linha visível, faixa de aviso e quadriculado sutil.
        tela.create_rectangle(x0, y0, x1, y1, fill=cor["grafico"], outline=cor["borda"])
        if y_min < self._limite_superior < y_max:
            topo_alerta = max(y0, min(y1, y1 - ((self._limite_superior - y_min) /
                                                      (y_max - y_min)) * (y1 - y0)))
            tela.create_rectangle(x0, y0, x1, topo_alerta,
                                  fill="#321D30", outline="", stipple="gray25")
        for indice in range(5):
            proporcao = indice / 4
            y = y1 - proporcao * (y1 - y0)
            valor = y_min + proporcao * (y_max - y_min)
            tela.create_line(x0, y, x1, y, fill=cor["grade"], dash=(3, 5))
            tela.create_text(x0 - 8, y, text=str(int(valor)), fill=cor["suave"], anchor="e",
                             font=("Arial", 9))
        for indice in range(5):
            segundos_atras = janela * (4 - indice) // 4
            x = x0 + indice / 4 * (x1 - x0)
            tela.create_line(x, y0, x, y1, fill=cor["grade"], dash=(3, 5))
            tela.create_text(x, y1 + 19, text=f"-{self._legenda_tempo(segundos_atras)}", fill=cor["suave"],
                             font=("Arial", 9))

        limite = self._limite_superior
        if y_min <= limite <= y_max:
            y = coord_y(limite)
            tela.create_line(x0, y, x1, y, fill=cor["vermelho"], dash=(7, 4), width=2)
            tela.create_text(x1 - 3, y - 11, text=f"Limite {limite}",
                             fill=cor["vermelho"], anchor="e", font=("Arial", 9, "bold"))
        coordenadas: List[float] = []
        for ponto in pontos_desenho:
            x = coord_x(ponto.tempo_monotonico_pc)
            # Limita apenas a posicao desenhada; nunca altera os dados reais.
            y = max(y0, min(y1, coord_y(ponto.valor)))
            coordenadas.extend([x, y])
        if len(coordenadas) >= 4:
            # Fundo suavemente preenchido amplia a leitura visual sem alterar os dados.
            area = [coordenadas[0], y1] + coordenadas + [coordenadas[-2], y1]
            tela.create_polygon(*area, fill=cor["area"], outline="", stipple="gray50")
            tela.create_line(*coordenadas, fill=cor["azul"], width=2, smooth=False)
            x_final, y_final = coordenadas[-2], coordenadas[-1]
            tela.create_oval(x_final - 4, y_final - 4, x_final + 4, y_final + 4,
                             fill=cor["azul"], outline=cor["texto"], width=1)
        elif len(coordenadas) == 2:
            x, y = coordenadas
            tela.create_oval(x - 3, y - 3, x + 3, y + 3, fill=cor["azul"], outline="")
        if ampliada:
            for ponto in pontos_desenho:
                x = coord_x(ponto.tempo_monotonico_pc)
                if ponto.valor > y_max:
                    tela.create_polygon(x - 5, y0 + 9, x + 5, y0 + 9,
                                         x, y0 + 1, fill=cor["vermelho"], outline="")
                elif ponto.valor < y_min:
                    tela.create_polygon(x - 5, y1 - 9, x + 5, y1 - 9,
                                         x, y1 - 1, fill=cor["amarelo"], outline="")
        congelado = (self._ultimo is not None and
                     time.monotonic() - self._ultimo.tempo_monotonico_pc > 5.0)
        texto = (f"{len(pontos)} amostras · {self._legenda_tempo(janela)}"
                 + (" · histórico preservado (sem dados novos)" if congelado else ""))
        tela.create_text(x0, y0 - 11, text=texto,
                         anchor="w", fill=cor["suave"], font=("Arial", 9))
        tela.create_text(x1, y0 - 11, text="ADC bruto (raw)", anchor="e",
                         fill=cor["suave"], font=("Arial", 9))

    def _atualizar_estatisticas(self) -> None:
        dados = self._historico.recentes(self._janela_segundos(), agora=self._tempo_referencia())
        resumo = self._analise.estatisticas(dados)
        if resumo is None:
            for variavel in (self._media_var, self._minimo_var, self._maximo_var):
                variavel.set("—")
            self._amostras_var.set("0 amostras na janela")
            return
        self._media_var.set(f"{resumo.media:,.1f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self._minimo_var.set(f"{resumo.minimo:,}".replace(",", "."))
        self._maximo_var.set(f"{resumo.maximo:,}".replace(",", "."))
        self._amostras_var.set(f"{resumo.quantidade} amostras na janela")

    def _atualizar_lista_alertas(self) -> None:
        eventos = self._eventos_painel
        selecao = self._lista_alertas.curselection()
        indice_anterior = selecao[0] if selecao else None
        self._lista_alertas.delete(0, tk.END)
        for evento in reversed(eventos):
            try:
                hora = datetime.fromisoformat(evento.horario_pc).strftime("%H:%M:%S")
            except ValueError:
                hora = evento.horario_pc[-8:]
            simbolo = "✓" if evento.reconhecido else "!"
            self._lista_alertas.insert(
                tk.END, f"{hora} {simbolo} {evento.tipo:<11} {evento.valor:>6}")
        pendentes = sum(not evento.reconhecido and evento.tipo != "NORMALIZADO"
                        for evento in eventos)
        self._resumo_alertas_var.set(
            f"{len(eventos)} eventos • {pendentes} não reconhecidos")
        if hasattr(self, "_abas"):
            self._abas.tab(1, text=(f"HISTÓRICO DE ALERTAS ({pendentes})"
                                    if pendentes else "HISTÓRICO DE ALERTAS"))
        if indice_anterior is not None and indice_anterior < len(eventos):
            self._lista_alertas.selection_set(indice_anterior)
        else:
            self._detalhe_alerta_var.set("Selecione um evento para detalhes")

    def _selecionar_alerta(self, _evento=None) -> None:
        selecao = self._lista_alertas.curselection()
        if not selecao:
            return
        eventos = self._eventos_painel
        indice = len(eventos) - 1 - selecao[0]
        if indice < 0 or indice >= len(eventos):
            return
        evento = eventos[indice]
        self._detalhe_alerta_var.set(
            f"{evento.tipo} • {evento.valor} {evento.unidade}"
            f" • limites {evento.limite_inferior}–{evento.limite_superior}"
            f" • {evento.sensor} • {evento.origem}")

    def _reconhecer_alertas(self) -> None:
        """Reconhecimento apenas visual; nao modifica o CSV de alertas."""
        from dataclasses import replace

        quantidade = sum(not e.reconhecido and e.tipo != "NORMALIZADO"
                         for e in self._eventos_painel)
        self._eventos_painel = [
            replace(evento, reconhecido=True) if evento.tipo != "NORMALIZADO"
            else evento for evento in self._eventos_painel
        ]
        self._erro_alertas_var.set("")
        self._atualizar_lista_alertas()
        self._detalhe_alerta_var.set(
            f"{quantidade} alerta(s) reconhecido(s) neste painel. "
            "O arquivo CSV permanece inalterado."
        )

    def _limpar_alertas(self) -> None:
        """Zera somente a lista exibida; nao mexe em gravacoes nem no log CSV."""
        self._eventos_painel.clear()
        self._erro_alertas_var.set("")
        self._atualizar_lista_alertas()
        self._detalhe_alerta_var.set(
            "Painel zerado. Os alertas anteriores permanecem no CSV histórico."
        )

    def _iniciar_gravacao(self) -> None:
        arquivo = filedialog.asksaveasfilename(
            title="Escolher arquivo CSV para gravação", defaultextension=".csv",
            filetypes=[("Arquivo CSV", "*.csv")], initialfile="ky037_log.csv",
        )
        if not arquivo:
            return
        try:
            self._gravador.iniciar(arquivo)
            # Nova sessao: so apos abertura bem-sucedida do CSV de leituras.
            # Os eventos antigos continuam salvos em alertas_ky037.csv.
            self._limpar_alertas()
            self._detector_alertas.reiniciar()
            self._ultimo_csv_gravado = arquivo
            self._arquivo_var.set(f"GRAVANDO CSV: {arquivo}")
        except OSError as erro:
            messagebox.showerror("Erro ao gravar", str(erro))

    def _parar_gravacao(self) -> None:
        self._gravador.parar()
        self._arquivo_var.set("Gravação desativada")

    def _exportar_historico(self) -> None:
        pontos = self._historico.recentes(self._janela_segundos(), agora=self._tempo_referencia())
        if not pontos:
            messagebox.showinfo("Histórico vazio", "Ainda não há leituras na janela selecionada.")
            return
        destino = filedialog.asksaveasfilename(
            title="Exportar histórico atual", defaultextension=".csv",
            filetypes=[("Arquivo CSV", "*.csv")], initialfile="ky037_historico.csv",
        )
        if not destino:
            return
        try:
            self._gravador.exportar(destino, pontos)
        except OSError as erro:
            messagebox.showerror("Erro de exportação", str(erro))
            return
        self._arquivo_var.set(f"Histórico exportado: {len(pontos)} amostras para {destino}")

    def _exportar_excel(self) -> None:
        """Converte uma gravação CSV inteira em XLSX com gráfico e alertas reais.

        Os registros persistidos podem abranger várias sessões: cada evento
        recebe uma marcação indicando se pertence ao período da gravação.
        """
        caminho_sugerido = (Path(self._ultimo_csv_gravado)
                           if self._ultimo_csv_gravado else Path.cwd() / "ky037_log.csv")
        origem = filedialog.askopenfilename(
            title="Selecionar CSV gravado pela interface KY-037",
            initialdir=str(caminho_sugerido.parent), initialfile=caminho_sugerido.name,
            filetypes=[("Gravação KY-037 (.csv)", "*.csv")],
        )
        if not origem:
            return
        destino = filedialog.asksaveasfilename(
            title="Salvar relatório Excel com gráfico e alertas",
            defaultextension=".xlsx", initialfile="Relatorio_KY037.xlsx",
            filetypes=[("Planilha do Excel (.xlsx)", "*.xlsx")],
        )
        if not destino:
            return
        try:
            resultado = RelatorioExcel(self._limite_inferior, self._limite_superior).gerar(
                origem, destino, self._alertas.listar_todos())
        except (OSError, ValueError, OverflowError, zipfile.BadZipFile) as erro:
            messagebox.showerror("Falha na exportação Excel", str(erro))
            return
        self._arquivo_var.set(f"XLSX gerado: {destino}")
        messagebox.showinfo(
            "Relatório Excel criado",
            f"{resultado['amostras']} leituras e {resultado['alertas']} eventos salvos.\n"
            f"{resultado['alertas_na_gravacao']} eventos pertencem à gravação escolhida.\n\n"
            "Abas: Visao Geral, Leituras, Alertas e Serie Grafico.\n"
            "O gráfico é editável no Excel e usa os horários do computador."
        )

    def _limpar_historico(self) -> None:
        self._historico.limpar()
        self._detector_alertas.reiniciar()
        self._ultimo = None
        self._valor_var.set("—")
        self._ultima_var.set("Nenhuma leitura recebida")
        self._origem_var.set("Origem: —")

    def _fechar(self) -> None:
        self._ativo = False
        self._parar_receptor()
        self._gravador.parar()
        self._janela.destroy()


class AplicacaoInterface:
    """Ponto de entrada da aplicacao grafica; nao utiliza estado global."""

    @staticmethod
    def executar() -> int:
        argumentos = argparse.ArgumentParser(description="Central UDP KY-037 com GUI Tkinter")
        argumentos.add_argument("--porta", type=int, default=8080,
                                 help="Porta UDP do receptor (padrão: 8080)")
        configuracao = argumentos.parse_args()
        if not 1 <= configuracao.porta <= 65535:
            argumentos.error("A porta deve estar entre 1 e 65535.")
        try:
            janela = tk.Tk()
        except tk.TclError as erro:
            print(f"Não foi possível abrir a interface gráfica: {erro}")
            print("Execute em um computador com ambiente gráfico e Tkinter instalado.")
            return 1
        InterfaceMonitoramento(janela, porta=configuracao.porta)
        janela.mainloop()
        return 0


if __name__ == "__main__":
    raise SystemExit(AplicacaoInterface.executar())
