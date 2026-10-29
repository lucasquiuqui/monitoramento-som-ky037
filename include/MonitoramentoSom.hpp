#ifndef MONITORAMENTO_SOM_HPP
#define MONITORAMENTO_SOM_HPP

#include "SensorSom.hpp"

#include <chrono>
#include <cstddef>
#include <iosfwd>

/**
 * @brief Realiza aquisicoes periodicas da classe SensorSom no Linux embarcado.
 *
 * @details Usa o ADC via arquivos sysfs/IIO, sem acesso direto a registradores.
 * Exibe contagens brutas, sem assumir conversao para decibeis (dB).
 * O uso de std::chrono::steady_clock evita depender do ajuste do relogio.
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
     * @brief Coleta e apresenta as amostras em formato CSV simples.
     * @param saida Fluxo em que as leituras serao impressas.
     * @throws std::runtime_error Se a leitura do ADC falhar.
     * @details A execucao continua pode ser encerrada com Ctrl+C.
     * Cada registro possui numero da amostra, tempo decorrido (ms) e leitura.
     */
    void executar(std::ostream& saida);

private:
    SensorSom& sensor_;                         ///< Leitor IIO utilizado.
    std::chrono::milliseconds intervalo_;       ///< Periodo solicitado em ms.
    std::size_t quantidadeAmostras_;            ///< Zero equivale a continuo.
};

#endif  // MONITORAMENTO_SOM_HPP
