#include "MonitoramentoSom.hpp"
#include "SensorSom.hpp"

#include <chrono>
#include <cstddef>
#include <exception>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

/**
 * @brief Interface de linha de comando da Entrega 2.
 * @details Toda a logica de configuracao fica na classe, sem variaveis globais.
 */
class AplicacaoSensorSom {
public:
    /**
     * @brief Interpreta os argumentos e inicia a coleta do KY-037.
     * @param argc Quantidade de argumentos.
     * @param argv Argumentos da linha de comando.
     * @return Zero no sucesso; um para erros de uso ou de leitura.
     */
    int executar(int argc, char* argv[]) const {
        std::string caminho = "/sys/bus/iio/devices/iio:device0/in_voltage13_raw";
        unsigned long intervaloMs = 200;
        unsigned long quantidadeAmostras = 20;
        bool caminhoConfigurado = false;
        bool quantidadeConfigurada = false;
        bool modoContinuo = false;

        try {
            for (int i = 1; i < argc; ++i) {
                const std::string argumento = argv[i];
                if (argumento == "--ajuda" || argumento == "-h") {
                    mostrarAjuda(argv[0]);
                    return 0;
                }
                if (argumento == "--arquivo") {
                    if (++i >= argc || caminhoConfigurado) {
                        throw std::invalid_argument("--arquivo exige um caminho unico.");
                    }
                    caminho = argv[i];
                    caminhoConfigurado = true;
                } else if (argumento == "--intervalo-ms") {
                    if (++i >= argc) {
                        throw std::invalid_argument("--intervalo-ms exige um inteiro.");
                    }
                    intervaloMs = lerNumero(argv[i], 1, 60000, "intervalo");
                } else if (argumento == "--amostras") {
                    if (++i >= argc || modoContinuo) {
                        throw std::invalid_argument("--amostras exige um inteiro e nao combina com --continuo.");
                    }
                    quantidadeAmostras = lerNumero(argv[i], 1, 1000000, "amostras");
                    quantidadeConfigurada = true;
                } else if (argumento == "--continuo") {
                    if (quantidadeConfigurada || modoContinuo) {
                        throw std::invalid_argument("--continuo nao combina com --amostras.");
                    }
                    quantidadeAmostras = 0;
                    modoContinuo = true;
                } else if (!argumento.empty() && argumento[0] != '-' && !caminhoConfigurado) {
                    // Compatibilidade com a Entrega 1: ./sensor_som arquivo.txt
                    caminho = argumento;
                    caminhoConfigurado = true;
                } else {
                    throw std::invalid_argument("Argumento nao reconhecido: " + argumento);
                }
            }

            SensorSom sensor(caminho);
            MonitoramentoSom monitor(
                sensor,
                std::chrono::milliseconds(intervaloMs),
                static_cast<std::size_t>(quantidadeAmostras));
            monitor.executar(std::cout);
            return 0;
        } catch (const std::exception& erro) {
            std::cerr << "Erro: " << erro.what() << '\n';
            std::cerr << "Use --ajuda para ver as opcoes.\n";
            return 1;
        }
    }

private:
    /** @brief Valida um numero decimal informado na linha de comando. */
    unsigned long lerNumero(const std::string& texto,
                            unsigned long minimo,
                            unsigned long maximo,
                            const std::string& campo) const {
        if (texto.empty()) {
            throw std::invalid_argument("Valor vazio para " + campo);
        }
        for (const char digito : texto) {
            if (digito < '0' || digito > '9') {
                throw std::invalid_argument("Numero invalido para " + campo + ": " + texto);
            }
        }
        std::size_t posicao = 0;
        const unsigned long valor = std::stoul(texto, &posicao, 10);
        if (posicao != texto.size() || valor < minimo || valor > maximo) {
            throw std::out_of_range("Fora do intervalo permitido para " + campo);
        }
        return valor;
    }

    /** @brief Exibe instrucoes de uso para a plataforma STM32 e Ubuntu. */
    void mostrarAjuda(const char* programa) const {
        std::cout << "Uso: " << programa << " [arquivo_adc] [opcoes]\n"
                  << "Opcoes:\n"
                  << "  --arquivo CAMINHO       Arquivo IIO ou de teste\n"
                  << "  --amostras N            Numero de amostras (padrao: 20)\n"
                  << "  --intervalo-ms N        Intervalo de 1 a 60000 ms (padrao: 200)\n"
                  << "  --continuo              Ler ate Ctrl+C\n"
                  << "  --ajuda                 Mostrar esta mensagem\n"
                  << "Sem arquivo: usa in_voltage13_raw do ADC1, entrada A4.\n"
                  << "Valores sao contagens brutas, nao decibeis.\n";
    }
};

int main(int argc, char* argv[]) {
    return AplicacaoSensorSom{}.executar(argc, argv);
}
