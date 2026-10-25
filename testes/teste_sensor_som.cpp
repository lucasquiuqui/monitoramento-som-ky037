#include "../include/SensorSom.hpp"

#include <cstdio>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

/** @brief Executa testes automatizados basicos da classe SensorSom. */
class TesteSensorSom {
public:
    int executar() const {
        const std::string caminho = "teste_adc_temporario.txt";
        try {
            {
                std::ofstream arquivo(caminho);
                arquivo << "88\n";
            }
            SensorSom sensor(caminho);
            if (sensor.possuiLeitura()) {
                throw std::runtime_error("Estado inicial incorreto");
            }
            if (sensor.lerBruto() != 88 ||
                !sensor.possuiLeitura() ||
                sensor.obterUltimaLeitura() != 88) {
                throw std::runtime_error("Leitura ou memoria incorreta");
            }
            {
                std::ofstream arquivo(caminho);
                arquivo << "invalido\n";
            }
            bool erroDetectado = false;
            try {
                sensor.lerBruto();
            } catch (const std::runtime_error&) {
                erroDetectado = true;
            }
            if (!erroDetectado || sensor.obterUltimaLeitura() != 88) {
                throw std::runtime_error("Tratamento de erro incorreto");
            }
            std::remove(caminho.c_str());
            std::cout << "Testes locais: OK\n";
            return 0;
        } catch (const std::exception& erro) {
            std::remove(caminho.c_str());
            std::cerr << "Falha no teste: " << erro.what() << '\n';
            return 1;
        }
    }
};

int main() {
    return TesteSensorSom{}.executar();
}
