# Roteiro de execução — Entrega 2

Este roteiro descreve **o que executar no seu Ubuntu e na STM32**, sem substituir os testes obrigatórios com o sensor físico.

## A. Preparação no Ubuntu

1. Trabalhe na versão mais recente do repositório do GitHub. **Não extraia o ZIP por cima da pasta com alterações não enviadas.**
2. Copie/integre os arquivos desta atualização na branch escolhida e verifique `git diff`.
3. Execute `make test` e confirme os testes automatizados.
4. Execute `make arm` ou o comando completo do SDK no README.
5. Execute `file sensor_som_arm` para verificar que o executável é ARM de 32 bits.
6. Execute `make docs` para atualizar a documentação das novas classes.

## B. Preparação do hardware, SEM energia

1. Desligue USB-C e Micro-USB da STM32.
2. Confirme que o antigo jumper **A4–GND** de teste foi removido.
3. Conecte KY-037: `+ -> 3V3`, `G -> GND`, `AO -> A4`; `DO` desconectado.
4. Verifique a montagem e siga a orientação do professor (autorização de conexão direta, sem divisor; foto já encaminhada).
5. Só então energize, usando 3,3 V no sensor, nunca 5 V.

## C. Terminal serial TeraTerm na STM32

Entre como root. Verifique:

```sh
uname -m
cat /sys/bus/iio/devices/iio:device0/name
cat /sys/bus/iio/devices/iio:device0/in_voltage13_raw
ip -4 addr
```

Anote o IP da interface de rede efetivamente conectada. A placa e o Ubuntu precisam estar em rede alcançável.

## D. Transferência via Ethernet

No Ubuntu, substituindo o IP verdadeiro:

```sh
scp -O sensor_som_arm root@<IP_DA_PLACA>:/home/root/
```

Se `scp` não conseguir conectar, verifique ping, rede da VM e o SSH antes de alterar configurações. TeraTerm serve para controlar a placa; o comando `scp` é digitado no Ubuntu.

## E. Teste REAL no kit

No TeraTerm:

```sh
cd /home/root
chmod +x sensor_som_arm
./sensor_som_arm --amostras 30 --intervalo-ms 100
./sensor_som_arm --continuo --intervalo-ms 50
```

Interrompa o segundo comando com Ctrl+C. Execute com ambiente silencioso e ruído próximo ao sensor, registrando o que de fato aparecer. Uma palma pode não ser capturada devido ao intervalo de leitura do sysfs.

## F. Evidências, README e GitHub

1. Capturar o terminal **real** do kit, indicando comando e leituras, e salvar como `evidencias/entrega2_terminal_stm32.png`.
2. Completar a tabela `Resultados reais da Entrega 2` no README, sem inventar dados.
3. Registrar no README se houve variação com os sons e, se não houve, a limitação observada.
4. No Ubuntu: `git status`, `git add ...`, `git commit -m "Entrega 2: leitura periodica no STM32 e evidencias"`, `git push`.
5. Copiar o URL completo do **commit final** e entregá-lo ao professor; se o repositório for privado, certifique-se de que o professor já aceitou o convite.
