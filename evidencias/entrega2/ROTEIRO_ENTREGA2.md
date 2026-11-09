# Roteiro de reprodução — Entrega 2

Este roteiro descreve a aquisição no computador e na STM32. Os resultados já medidos estão em [ANALISE_ENTREGA2.md](ANALISE_ENTREGA2.md), com os CSVs e gráficos nesta pasta.

## 1. Compilar e testar no computador

Na raiz do repositório, execute `make test`. Para gerar o binário da placa, use `make arm ARM_CXX=CAMINHO_DO_COMPILADOR`, apontando para o compilador do SDK Buildroot. O [README](../../README.md#compilação-cruzada-para-stm32) traz um exemplo completo. Confira a arquitetura com `file sensor_som_arm`.

## 2. Preparar a montagem

Com a placa desligada, remova qualquer jumper de teste entre A4 e GND. Ligue o KY-037 com `+` em **3,3 V**, `G` em **GND** e `AO` em **A4**; deixe `DO` desconectado. Confira as conexões antes de energizar.

## 3. Conferir o ADC na placa

No terminal da STM32, verifique o canal e o endereço de rede:

```sh
cat /sys/bus/iio/devices/iio:device0/name
cat /sys/bus/iio/devices/iio:device0/in_voltage13_raw
ip -4 addr
```

O caminho IIO pode variar conforme a configuração do Linux. Se variar, informe o novo caminho com `--arquivo` ao executar o programa.

## 4. Transferir e executar

Com SSH disponível, no computador, substitua o IP de exemplo pelo endereço atual da placa:

```sh
scp -O sensor_som_arm root@192.168.42.2:/home/root/
```

No terminal da STM32:

```sh
cd /home/root
chmod +x sensor_som_arm
./sensor_som_arm --amostras 100 --intervalo-ms 100
```

Para uma coleta contínua, use `./sensor_som_arm --continuo --intervalo-ms 100` e interrompa com `Ctrl+C`. Registre condições silenciosas e com ruído próximo ao microfone. Eventos muito curtos podem ocorrer entre amostras.

## 5. Evidências disponíveis

Os arquivos [silencio.csv](silencio.csv) e [ruido.csv](ruido.csv) contêm 100 amostras por condição; a [análise](ANALISE_ENTREGA2.md) inclui estatísticas e gráficos. As capturas dos terminais da STM32 e do computador durante a transmissão UDP estão em [Entrega 3](../entrega3/).
