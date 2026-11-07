#ifndef MONITORAMENTO_SOM_HPP
#define MONITORAMENTO_SOM_HPP

#include "ClienteUDP.hpp"
#include "ProtocoloSom.hpp"
#include "SensorSom.hpp"

#include <chrono>
#include <cstddef>
#include <iosfwd>
#include <memory>

/**
 * @brief Realiza aquisicoes periodicas da classe SensorSom no Linux embarcado.
 *
 * @details Usa o ADC via arquivos sysfs/IIO, sem acesso direto a registradores.
 * Exibe contagens brutas, sem assumir conversao para decibeis (dB).
 * Pode transmitir dados em tempo real via socket UDP para um servidor central.
 */
class MonitoramentoSom {
public:
    /**
     * @brief Configura a periodicidade e a quantidade de amostras.
     * @param sensor Referencia ao sensor de leitura, que deve permanecer valido.
     * @param intervalo Tempo solicitado entre o inicio de duas leituras.
     * @param quantidadeAmostras Numero de amostras, ou zero para modo continuo.
     * @throws std::invalid_argument Se o intervalo for menor que 1 ms.
     */
    MonitoramentoSom(SensorSom& sensor,
                    std::chrono::milliseconds intervalo,
                    std::size_t quantidadeAmostras);

    /**
     * @brief Configura a transmissao de telemetria via UDP.
     * @param cliente Referencia ao cliente UDP configurado.
     * @param protocolo Referencia ao protocolo de empacotamento.
     * @param formato Formato da mensagem (JSON ou CSV).
     */
    void configurarUDP(ClienteUDP* cliente,
                       ProtocoloSom* protocolo,
                       FormatoMensagem formato = FormatoMensagem::JSON);

    /**
     * @brief Coleta e apresenta as amostras em formato CSV simples, transmitindo por UDP se ativo.
     * @param saida Fluxo em que as leituras serao impressas.
     * @throws std::runtime_error Se a leitura do ADC falhar.
     */
    void executar(std::ostream& saida);

private:
    SensorSom& sensor_;                         ///< Leitor IIO utilizado.
    std::chrono::milliseconds intervalo_;       ///< Periodo solicitado em ms.
    std::size_t quantidadeAmostras_;            ///< Zero equivale a continuo.
    ClienteUDP* clienteUdp_;                    ///< Ponteiro para cliente UDP (nullptr se inativo).
    ProtocoloSom* protocolo_;                   ///< Gerador de pacotes do protocolo.
    FormatoMensagem formatoMensagem_;           ///< JSON ou CSV.
};

#endif  // MONITORAMENTO_SOM_HPP
