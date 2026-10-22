# Documentacao tecnica — SensorSom {#mainpage}

## Visao geral

Esta documentacao apresenta a classe `SensorSom` da Entrega 1 do projeto de
monitoramento inteligente de carga. A classe le **contagens brutas** de um
canal ADC disponibilizado pelo subsistema Linux IIO. O valor **nao e uma
medicao calibrada em decibeis (dB)**.

## Interface publica

- `SensorSom(caminhoAdc)`: informa o caminho do arquivo de leitura.
- `lerBruto()`: abre o arquivo, valida uma amostra inteira e salva seu valor.
- `possuiLeitura()`: indica se ja houve uma leitura bem-sucedida.
- `obterUltimaLeitura()`: recupera a ultima amostra valida.
- `obterCaminhoAdc()`: consulta o caminho configurado.

## Encapsulamento

O caminho do arquivo e o estado da ultima leitura sao atributos privados da
classe. Os demais componentes do programa acessam esses dados por metodos
publicos.

## Como gerar a documentacao

No diretorio do projeto:

```bash
sudo apt-get install doxygen graphviz
doxygen Doxyfile
```

Abra `docs/html/index.html`. A disponibilidade dos diagramas exige o programa
`dot` (Graphviz).

## Limites desta entrega

O codigo foi testado com dados simulados no Ubuntu. A leitura real do sensor
KY-037 pela STM32 depende da validacao da conexao eletrica e de testes no kit.
As entregas de UDP e interface grafica ainda nao fazem parte desta versao.
