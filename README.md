
# Sensor de Som KY-037 — STM32MP1-DK1

## Objetivo e estado do projeto

Projeto da disciplina **Programação Aplicada à Engenharia Elétrica**: leitura da saída analógica do KY-037 via Linux IIO na STM32MP1-DK1, usando classes C++ documentadas com Doxygen. As leituras são contagens brutas do ADC, **não decibéis (dB)**.

**Estado:** Entrega 1 (classe e Doxygen), Entrega 2 (leitura real na STM32) e Entrega 3 (transmissão UDP e receptor no computador) implementadas e testadas. A Entrega 4, com interface gráfica, permanece pendente.

## Estrutura do projeto

- `include/SensorSom.hpp`: declaração da classe, atributos privados, métodos públicos e comentários Doxygen.
- `src/SensorSom.cpp`: leitura de arquivo Linux IIO, tratamento de erros e armazenamento da última leitura válida.
- `main.cpp`: aplicação de linha de comando que configura a leitura periódica e, opcionalmente, o envio UDP; lógica encapsulada em classes.
- `testes/teste_sensor_som.cpp`: teste local com arquivo simulado e tratamento de entrada invalida.
- `dados/leitura_exemplo.txt`: valor ficticio `88` usado somente no teste.
- `Doxyfile`: configuracao do gerador Doxygen, incluindo membros privados, navegador de codigo e diagramas Graphviz.
- `DOCUMENTACAO.md`: página inicial da documentação gerada.

### Classes e métodos

- `SensorSom`: recebe o caminho do arquivo ADC no construtor. `lerBruto()` abre o arquivo, valida um inteiro não negativo e guarda a última leitura válida. `possuiLeitura()`, `obterUltimaLeitura()` e `obterCaminhoAdc()` consultam o estado sem expor os atributos privados.
- `AplicacaoSensorSom` (em `main.cpp`): configura caminho ADC, intervalo, quantidade de amostras e envio UDP opcional; executa o monitoramento e informa erros.
- `TesteSensorSom` (em `testes/teste_sensor_som.cpp`): verifica leitura simulada, estado inicial e preservação da última leitura quando a entrada é inválida.

O código C++ organiza a lógica da aplicação e dos testes em classes, sem variáveis globais.

## Dependências

- Ubuntu ou outro Linux com `g++` e suporte a C++17 para compilar e executar os testes locais.
- `doxygen` e `graphviz` (`dot`) para gerar a documentação HTML e os diagramas.
- Para compilação e execução na placa: SDK `arm-buildroot-linux-gnueabihf-g++` compatível com o Linux embarcado e acesso serial ou SSH.
- Python 3 para executar o receptor UDP no computador.

## Compilação e testes no Ubuntu (sem hardware)

```bash
make
make test
make docs
```

O `make test` executa os testes automatizados e uma aquisição simulada com `dados/leitura_exemplo.txt` (valor fictício `88`). **Esses testes não substituem as medições reais do sensor.**

Para executar apenas uma aquisição simulada:

```bash
./sensor_som dados/leitura_exemplo.txt --amostras 3 --intervalo-ms 1
```

```text
Fonte ADC: dados/leitura_exemplo.txt
amostra,tempo_ms,adc_bruto
1,0,88
2,1,88
3,2,88
```

Os tempos podem variar conforme o sistema. Sem `--arquivo` ou caminho posicional, o programa usa o ADC configurado na STM32.

## Compilação cruzada para STM32

No Ubuntu, utilizando o SDK Buildroot fornecido:

```bash
make arm ARM_CXX="$HOME/Downloads/arm-buildroot-linux-gnueabihf_sdk-buildroot/bin/arm-buildroot-linux-gnueabihf-g++"
```

Esse comando produz `sensor_som_arm`. A execução ARM com leituras reais do KY-037 já foi validada na STM32MP1-DK1; a transmissão UDP também foi demonstrada na placa (evidências abaixo).

## Canal ADC identificado no laboratorio

- Entrada fisica escolhida: **A4**.
- Dispositivo IIO: `iio:device0` (nome `48003000.adc:adc@0`).
- Canal: `in_voltage13_raw`.
- Caminho completo: `/sys/bus/iio/devices/iio:device0/in_voltage13_raw`.
- Leituras ja observadas com **A4 conectado ao GND**: `56, 88, 0, 72, 0, 0` (contagens brutas), e escala `0.038146972` com offset `0`.
- As observacoes acima **nao sao leituras do KY-037**.

A aplicacao usa esse caminho por padrao, ou outro indicado como argumento na linha de comando.

## Documentacao Doxygen

Instale Doxygen e Graphviz no Ubuntu (caso ainda nao estejam instalados):

```bash
sudo apt-get update
sudo apt-get install doxygen graphviz
```

Na raiz do projeto, execute:

```bash
doxygen --version
dot -V
doxygen Doxyfile
```

Abra `docs/html/index.html` no navegador. Confira as paginas das classes
`SensorSom` e `AplicacaoSensorSom`, os metodos, os atributos privados e os
arquivos-fonte. O arquivo `Doxyfile` ativa opcoes sugeridas nos slides da
disciplina: `EXTRACT_PRIVATE`, `EXTRACT_STATIC`, `SOURCE_BROWSER`,
`INLINE_SOURCES`, `HAVE_DOT`, `UML_LOOK` e `DOT_UML_DETAILS`.

### Evidências da Entrega 1

As imagens abaixo foram obtidas da documentação Doxygen
gerada no Ubuntu.

**Diagrama UML da classe SensorSom:**

![Diagrama UML da classe SensorSom](evidencias/doxygen_sensor_som.png)

**Documentação dos métodos:**

![Documentação dos métodos da classe SensorSom](evidencias/doxygen_metodos.png)

A documentação HTML completa pode ser gerada com
`doxygen Doxyfile`. A pasta `docs/` não é
versionada no Git: os comentários Doxygen estão nos arquivos-fonte, e o `Doxyfile` permite recriar o HTML. A saída dos testes locais está registrada acima.

## Modelo da classe

```text
SensorSom
--------------------------------
- caminhoAdc_: std::string
- ultimaLeitura_: int
- possuiLeitura_: bool
--------------------------------
+ SensorSom(caminhoAdc)
+ lerBruto(): int
+ possuiLeitura(): bool
+ obterUltimaLeitura(): int
+ obterCaminhoAdc(): const string&
```


## Resultados experimentais da Entrega 2

O programa foi executado na STM32MP1-DK1 com o sensor
KY-037 conectado à entrada analógica A4.

Foram realizadas 100 leituras em silêncio e 100 com ruído,
utilizando intervalo solicitado de 100 ms.

| Indicador | Silêncio | Ruído |
|---|---:|---:|
| Média | 4.137,13 | 5.111,61 |
| Mediana | 4.173 | 4.408,5 |
| Mínimo | 3.522 | 3.190 |
| Máximo | 4.561 | 41.204 |

O teste com ruído apresentou picos mais elevados.
Esses valores representam contagens brutas do ADC,
não níveis sonoros em decibéis.

### Evidências

![Gráfico das medições](evidencias/entrega2/ky037_comparacao_completa.png)

![Gráfico ampliado](evidencias/entrega2/ky037_comparacao_ampliada.png)

[Análise detalhada](evidencias/entrega2/ANALISE_ENTREGA2.md)

### Execução na STM32

Para executar o programa após transferi-lo para a placa:

    chmod +x /root/sensor_som_arm
    /root/sensor_som_arm --amostras 100 --intervalo-ms 100

## Entrega 3: Comunicação e Protocolo UDP

Nesta etapa, implementou-se a transmissão contínua e em tempo real dos dados do sensor KY-037 a partir do kit STM32MP1-DK1 para um servidor central no computador via socket UDP, atendendo aos requisitos de IoT do projeto.

### Arquitetura orientada a objetos (C++)

- `include/ClienteUDP.hpp` e `src/ClienteUDP.cpp`: classe encapsulada com RAII para gerenciamento do socket UDP POSIX (`socket`, `sendto`, `close`), tratamento de exceções e sem variáveis globais no código C++.
- `include/ProtocoloSom.hpp` e `src/ProtocoloSom.cpp`: classe responsável pela formatação e montagem dos pacotes nos formatos JSON (padrão) e CSV.
- `include/MonitoramentoSom.hpp` e `src/MonitoramentoSom.cpp`: integração do laço temporal de aquisição com o envio UDP concorrente à exibição local.
- `main.cpp`: expansão da CLI com os parâmetros `--ip`, `--porta`, `--id-sensor`  e `--formato`.
- `servidor_udp.py`: receptor em Python para validação e recepção no computador do operador.
- `testes/teste_protocolo_udp.cpp`: testes unitários de serialização e envio/recepção em loopback (`127.0.0.1`).

### Especificação do Protocolo de Mensagens

O protocolo transmite datagramas UDP com os campos `sensor`, `valor` e `unidade`, além de `timestamp` (opcional no enunciado, incluído nesta implementação):

| Campo | Tipo | Descrição | Exemplo |
| :--- | :--- | :--- | :--- |
| `sensor` | `string` | Identificador único do sensor/grupo | `"KY-037"` |
| `valor` | `inteiro` | Leitura bruta do ADC (`in_voltage13_raw`) | `3857` |
| `unidade` | `string` | Unidade da grandeza lida | `"raw"` |
| `timestamp` | `inteiro (ms)`| Tempo Unix em milissegundos da leitura, quando presente | `946686107619` |


#### Formato JSON (Pádrão adotado):
```json
{"sensor":"KY-037","valor":3857,"unidade":"raw","timestamp":946686107619}
```


#### Formato CSV (alternativo):
```text
KY-037,3857,raw,946686107619
```


### Instruções de execução

Confira o endereço IPv4 do computador conectado à STM32 (no Windows, `ipconfig`). Esse endereço deve ser informado em `--ip`, e a porta UDP deve ser a mesma nos dois lados.

1. **No computador (servidor receptor):**
   ```bash
   python servidor_udp.py 8080
   ```

2. **Na STM32MP1-DK1 (transmissor):**
   ```bash
   cd /home/root
   chmod +x sensor_som_arm
   ./sensor_som_arm --ip 192.168.42.10 --porta 8080 --amostras 30 --intervalo-ms 100
   ```

No teste documentado, o computador utilizou `192.168.42.10`; substitua-o pelo IP atual do receptor, caso seja diferente.

**Observação:** na captura do teste, o relógio da STM32 não estava sincronizado; o `timestamp` demonstra o formato do pacote, mas não corresponde à data real da aquisição.

### Evidências da Execução Real no Kit STM32

Os testes foram realizados conectando a STM32MP1-DK1 (`192.168.42.2`) ao computador (`192.168.42.10`) via cabo Ethernet:

**1. Execução no terminal da STM32MP1-DK1 (TeraTerm via Serial):**

![Execução na STM32](evidencias/entrega3/terminal_stm32_udp.png)

**2. Recepção em tempo real no servidor central (PC:)**

![Servidor Receptor UDP no PC](evidencias/entrega3/servidor_udp_pc.jpg)

Na execução documentada, o servidor recebeu 30 mensagens enviadas pela STM32. O UDP não garante a entrega de todos os pacotes em qualquer condição de rede.


## Próxima etapa — Entrega 4

Implementar a interface gráfica com visualização em tempo real, histórico das leituras, alertas e registro em arquivo. As medições continuam sendo contagens brutas do ADC, não níveis calibrados em dB.

## Autoria e colaboracao

Implementacao inicial disponibilizada para revisao e continuidade pelo grupo. O GitHub deve registrar os commits de cada integrante. Os resultados e fotos devem corresponder apenas a testes realmente realizados.
