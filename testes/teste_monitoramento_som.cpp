#include "../include/MonitoramentoSom.hpp"
#include "../include/SensorSom.hpp"

#include <chrono>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

/** @brief Exercita o monitor de amostras sem placa ou sensor real. */
class TesteMonitoramentoSom {
public:
    int executar() const {
        const std::string caminho = "teste_monitor_adc_temporario.txt";
        try {
            {
                std::ofstream arquivo(caminho);
                arquivo << "123\n";
            }
            SensorSom sensor(caminho);
            MonitoramentoSom monitor(sensor, std::chrono::milliseconds(1), 3);
            std::ostringstream saida;
            monitor.executar(saida);
            const std::string resultado = saida.str();

            if (resultado.find("amostra,tempo_ms,adc_bruto\n") == std::string::npos ||
                resultado.find("1,") == std::string::npos) {
                throw std::runtime_error("Cabecalho ou primeira leitura incorretos");
            }
            // O tempo de cada amostra varia com o escalonamento do SO.
            std::istringstream linhas(resultado);
            std::string linha;
            std::size_t quantidadeRegistros = 0;
            while (std::getline(linhas, linha)) {
                if (linha.find(",123") != std::string::npos) {
                    ++quantidadeRegistros;
                }
            }
            if (quantidadeRegistros != 3 || sensor.obterUltimaLeitura() != 123) {
                throw std::runtime_error("Quantidade/valor das leituras incorreto");
            }
            bool erroDetectado = false;
            try {
                MonitoramentoSom invalido(sensor, std::chrono::milliseconds(0), 1);
            } catch (const std::invalid_argument&) {
                erroDetectado = true;
            }
            if (!erroDetectado) {
                throw std::runtime_error("Intervalo nulo nao foi rejeitado");
            }
            std::remove(caminho.c_str());
            std::cout << "Teste de monitoramento: OK\n";
            return 0;
        } catch (const std::exception& erro) {
            std::remove(caminho.c_str());
            std::cerr << "Falha no monitoramento: " << erro.what() << '\n';
            return 1;
        }
    }
};

int main() {
    return TesteMonitoramentoSom{}.executar();
}
