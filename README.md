# Sensor de Som KY-037 — STM32MP1-DK1

## Objetivo
Projeto da disciplina **Programacao Aplicada a Engenharia Eletrica**: ler a saida analogica do modulo de som KY-037 no Linux embarcado da STM32MP1-DK1, por meio de uma **classe C++ encapsulada e documentada com Doxygen**.

> **Status desta entrega:** classe implementada e testada com arquivo simulado no Ubuntu. **Nao ha comprovacao de leitura real do KY-037 nesta versao.** A conexao eletrica definitiva aguarda validacao do professor. Nao energize o sensor ligado ao ADC sem conferir os limites de tensao.

## Arquivos

- `SensorSom.hpp`: declaracao da classe, atributos privados, metodos publicos e documentacao Doxygen.
- `SensorSom.cpp`: leitura de arquivo Linux IIO, tratamento de erros e armazenamento da ultima leitura valida.
- `main.cpp`: aplicacao minima que utiliza a classe; toda a logica fica encapsulada em classes.
- `testes/teste_sensor_som.cpp`: teste local com arquivo simulado e tratamento de entrada invalida.
- `dados/leitura_exemplo.txt`: valor ficticio `88` usado somente no teste.
- `Doxyfile`: configuracao do gerador Doxygen, incluindo membros privados, navegador de codigo e diagramas Graphviz.
- `DOCUMENTACAO.md`: pagina inicial da documentacao gerada.

## Ambiente

- Ubuntu: `g++` com suporte a C++17.
- Documentacao opcional gerada com `doxygen`.
- Para executar na placa: SDK/compilador cruzado `arm-buildroot-linux-gnueabihf-g++` compatível com o Linux embarcado e comunicacao serial ou SSH.

## Compilacao e teste no Ubuntu (sem hardware)

```bash
g++ -std=c++17 -Wall -Wextra -Wpedantic SensorSom.cpp main.cpp -o sensor_som
./sensor_som dados/leitura_exemplo.txt
```

Saida esperada (simulada):

```text
Fonte: dados/leitura_exemplo.txt
Leitura bruta do ADC: 88
```

Testes automatizados:

```bash
g++ -std=c++17 -Wall -Wextra -Wpedantic SensorSom.cpp testes/teste_sensor_som.cpp -o teste_sensor_som
./teste_sensor_som
```

## Compilacao cruzada para STM32 (a validar na placa)

No Ubuntu, com o SDK fornecido pelo professor extraido:

```bash
SDK="$HOME/Downloads/arm-buildroot-linux-gnueabihf_sdk-buildroot"
"$SDK/bin/arm-buildroot-linux-gnueabihf-g++" -std=c++17 -Wall -Wextra -Wpedantic SensorSom.cpp main.cpp -o sensor_som_arm
file sensor_som_arm
```

Os comandos acima geram um binario ARM. **A execucao na placa ainda precisa ser testada**; compatibilidade com bibliotecas Linux e realocacao correta do SDK nao estao confirmadas.

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
versionada no Git.

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

## Limites e proximas etapas

1. Aguardar confirmacao do professor sobre a ligacao analogica KY-037 A0 -> STM32 A4 e necessidade de protecao/adaptacao de tensao. **Nao testar a ligacao direta sem essa validacao.**
2. Confirmar funcionamento do executavel ARM diretamente na STM32.
3. Com a eletrica validada, realizar leituras reais, comparar silencio e eventos sonoros e definir processamento adequado (o numero ADC **nao representa decibeis**).
4. Documentar no README as evidencias de teste e fotos reais da montagem com a placa desligada.
5. Em entregas posteriores: transmissao UDP, interface grafica, historico, alertas, log CSV e apresentacao.

## Protocolo

Ainda nao implementado — pertence a entrega de comunicacao UDP.

## Autoria e colaboracao

Implementacao inicial disponibilizada para revisao e continuidade pelo grupo. O GitHub deve registrar os commits de cada integrante. Os resultados e fotos devem corresponder apenas a testes realmente realizados.
