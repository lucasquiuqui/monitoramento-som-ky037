# Documentação técnica — Sensor KY-037 {#mainpage}

## Objetivo

Monitorar a saída analógica AO do KY-037 em espaço de usuário Linux da STM32MP1-DK1. O valor lido é uma **contagem bruta** do ADC IIO e **não mede decibéis (dB)**.

## Classes e encapsulamento

- `SensorSom`: leitura de um arquivo `in_voltageX_raw`, tratamento de erros e retenção da última leitura válida.
- `MonitoramentoSom`: realiza leituras periódicas usando `SensorSom` e apresenta amostra, tempo decorrido (ms) e contagem bruta.
- `AplicacaoSensorSom`: interpreta argumentos e inicia o monitoramento; `main()` só delega a execução.
- `ProtocoloSom`: monta as mensagens de telemetria JSON ou CSV.
- `ClienteUDP`: envia os datagramas para o computador e fecha o socket ao final.

Os estados internos ficam protegidos por atributos privados. Não existem variáveis globais.

## Aquisição e comunicação

Canal identificado: `/sys/bus/iio/devices/iio:device0/in_voltage13_raw` (A4). O programa aceita tanto este arquivo quanto dados simulados para testes no Ubuntu.

No kit, executar `./sensor_som_arm --amostras 30 --intervalo-ms 100`, ou usar `--continuo` para interromper com Ctrl+C. As medições reais e a análise estão em `evidencias/entrega2/`. Com `--ip` e `--porta`, cada leitura também é transmitida por UDP; as capturas da placa e do receptor estão em `evidencias/entrega3/`. O `README.md` na raiz reúne as instruções de uso e os diagramas.

## Gerar a documentação

```sh
doxygen Doxyfile
```

Abrir `docs/html/index.html`. Diagramas dependem do Graphviz (`dot`).

## Limites

O acesso pelo sysfs não garante uma frequência de amostragem adequada para reconstruir áudio. A intensidade sonora em dB não é calculada. A interface gráfica ainda não foi implementada.
