# Entrega 4 — Procedimento de reprodução e inventário das evidências REAIS

**Situação:** a interface Tkinter foi executada no Windows recebendo UDP da STM32MP1-DK1 com KY-037 real. As capturas da GUI, do terminal e dos relatórios foram realizadas e seus arquivos estão em `evidencias/entrega4/`. **Este documento é um roteiro de reprodução; as capturas anexadas não são simulações.**

## Inventário das evidências

| Arquivo | Conteúdo |
|---|---|
| `entrega4_terminal_stm32.png` | Leitura contínua de amostras ADC no Tera Term; o comando completo do transmissor não está visível nesta imagem. |
| `entrega4_interface_monitoramento.png` | GUI recebendo UDP real: IP 192.168.42.2, porta 8080, valor atual, gráfico de 60 s e estatísticas. |
| `entrega4_interface_alertas.png` | Eventos reais `ACIMA` e `NORMALIZADO` com limite superior 4400 ADC raw. |
| `entrega4_excel_grafico.png` | Captura do gráfico no relatório Excel. |
| `entrega4_excel_alertas.png` | Captura da aba de alertas no Excel. |
| `ky037_log1231.csv` | CSV real da sessão com 357 leituras em 35,598 segundos. |
| `Relatorio_KY037_1231.xlsx` | Relatório Excel com gráfico editável, todas as leituras e alertas históricos com sinalização de pertinência à sessão. |

## Resultados verificados com os arquivos da gravação

- 357 leituras válidas de `KY-037`, unidade `raw`, origem `192.168.42.2`.
- Horários do PC: 14/11/2026, de 23:41:28.837 a 23:42:04.435 (UTC−03:00).
- Média 3939,48, mínimo 3313, máximo 14381 contagens brutas ADC.
- 16 leituras acima do limite experimental de 4400.
- No Excel, 152 eventos históricos persistidos e 32 eventos marcados como pertencentes ao período dessa gravação (16 ultrapassagens + 16 normalizações).
- O contador de pacotes da captura de interface reflete outra aquisição/intervalo, não os 357 registros deste CSV.

## Reprodução do teste

1. Com a placa **desligada** para qualquer alteração na fiação, conecte KY-037 `+` a 3,3 V, `G` a GND e `AO` à entrada A4 da STM32MP1-DK1; saída `DO` sem uso.
2. Ligue o Linux na placa e configure Ethernet. No ensaio: STM32 `192.168.42.2/24`, PC Windows `192.168.42.1/24`.
3. Abra o PowerShell na pasta que contém os módulos Python e execute: `py -3 interface_grafica.py --porta 8080`.
4. Configure o limite experimental, clique **Aplicar limites** e inicie **Gravar CSV** com um nome novo.
5. No Tera Term, execute: `/root/sensor_som_arm --ip 192.168.42.1 --porta 8080 --continuo --intervalo-ms 100 --id-sensor KY-037 --formato json`.
6. Observe a atualização dos valores, gráfico, contador e transições de alertas. Encerre a transmissão com **Ctrl+C** no Tera Term e depois **Parar gravação** na interface.
7. Para o relatório, clique **Relatório Excel**, selecione o CSV e salve o `.xlsx`. Confira as abas `Visao Geral`, `Leituras`, `Alertas` e `Serie Grafico`.
8. Ao iniciar uma **nova** gravação, o painel de alertas é zerado visualmente; **o CSV persistido `alertas_ky037.csv` não é apagado**. Preserve as gravações antigas.

## Cuidados de interpretação

- Os valores são contagens ADC brutas, **não dB**; limite experimental não comprova violação da carga.
- UDP não assegura entrega. O gráfico usa relógio do PC; o timestamp da placa pode estar desajustado.
- As opções de 5/10/30 minutos são suportadas e testadas por software, mas o conjunto de evidências anexadas não demonstra uma coleta física ininterrupta de 30 minutos.
- Na entrega acadêmica original, as capturas deveriam constar no README. Nesta organização de portfólio, as cinco imagens estão no [histórico das entregas](../../docs/historico-entregas.md), com caminhos relativos; o README principal exibe uma seleção.
- O arquivo `alertas_ky037.csv` original pode conter histórico de várias sessões e não deve ser alterado apenas para gerar evidências.
