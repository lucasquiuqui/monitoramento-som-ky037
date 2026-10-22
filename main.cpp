#include "SensorSom.hpp"

#include <exception>
#include <iostream>
#include <string>

/**
 * @brief Orquestra um teste de leitura do SensorSom.
 * @details Mantem a logica da aplicacao encapsulada em uma classe,
 * conforme a orientacao de programacao orientada a objetos.
 */
class AplicacaoSensorSom {
public:
    /**
     * @brief Executa uma leitura e apresenta seu valor bruto.
     * @param argc Quantidade de argumentos da linha de comando.
     * @param argv Argumentos (opcional: caminho do arquivo ADC).
     * @return 0 em caso de sucesso; 1 em caso de erro.
     */
    int executar(int argc, char* argv[]) const {
        if (argc > 2) {
            std::cerr << "Uso: " << argv[0] << " [caminho_adc]\n";
            return 1;
        }

        const std::string caminho = (argc == 2)
            ? argv[1]
            : "/sys/bus/iio/devices/iio:device0/in_voltage13_raw";

        try {
            SensorSom sensor(caminho);
            const int leitura = sensor.lerBruto();
            std::cout << "Fonte: " << sensor.obterCaminhoAdc() << '\n';
            std::cout << "Leitura bruta do ADC: " << leitura << '\n';
            return 0;
        } catch (const std::exception& erro) {
            std::cerr << "Erro: " << erro.what() << '\n';
            return 1;
        }
    }
};

int main(int argc, char* argv[]) {
    return AplicacaoSensorSom{}.executar(argc, argv);
}
