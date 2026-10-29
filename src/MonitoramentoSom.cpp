#include "MonitoramentoSom.hpp"

#include <chrono>
#include <ostream>
#include <stdexcept>
#include <thread>

MonitoramentoSom::MonitoramentoSom(
    SensorSom& sensor,
    std::chrono::milliseconds intervalo,
    std::size_t quantidadeAmostras)
    : sensor_(sensor), intervalo_(intervalo), quantidadeAmostras_(quantidadeAmostras) {
    if (intervalo_.count() < 1) {
        throw std::invalid_argument("O intervalo deve ser de pelo menos 1 ms.");
    }
}

void MonitoramentoSom::executar(std::ostream& saida) {
    using Relogio = std::chrono::steady_clock;
    const auto inicio = Relogio::now();
    auto proximaLeitura = inicio;

    saida << "Fonte ADC: " << sensor_.obterCaminhoAdc() << '\n';
    saida << "amostra,tempo_ms,adc_bruto\n";
    saida.flush();

    std::size_t contador = 0;
    while (quantidadeAmostras_ == 0 || contador < quantidadeAmostras_) {
        const int valor = sensor_.lerBruto();
        const auto instante = Relogio::now();
        const auto tempoMs = std::chrono::duration_cast<std::chrono::milliseconds>(
            instante - inicio).count();

        ++contador;
        saida << contador << ',' << tempoMs << ',' << valor << '\n';
        saida.flush();

        // Sleep ate o proximo periodo; evita acumular atraso se o IIO for lento.
        proximaLeitura += intervalo_;
        if (proximaLeitura < Relogio::now()) {
            proximaLeitura = Relogio::now();
        }
        if (quantidadeAmostras_ == 0 || contador < quantidadeAmostras_) {
            std::this_thread::sleep_until(proximaLeitura);
        }
    }
}
