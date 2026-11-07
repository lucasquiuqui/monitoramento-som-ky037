#include "ClienteUDP.hpp"
#include "MonitoramentoSom.hpp"
#include "ProtocoloSom.hpp"
#include "SensorSom.hpp"

#include <chrono>
#include <cstddef>
#include <exception>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>

/**
 * @brief Interface de linha de comando com suporte a telemetria UDP (Entrega 3).
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

        // Configuracoes UDP
        std::string ipServidor = "";
        int portaUdp = 0;
        std::string idSensor = "KY-037";
        FormatoMensagem formato = FormatoMensagem::JSON;

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
                } else if (argumento == "--ip") {
                    if (++i >= argc) {
                        throw std::invalid_argument("--ip exige um endereco IPv4.");
                    }
                    ipServidor = argv[i];
                } else if (argumento == "--porta") {
                    if (++i >= argc) {
                        throw std::invalid_argument("--porta exige um numero de porta.");
                    }
                    portaUdp = static_cast<int>(lerNumero(argv[i], 1, 65535, "porta"));
                } else if (argumento == "--id-sensor") {
                    if (++i >= argc) {
                        throw std::invalid_argument("--id-sensor exige um nome.");
                    }
                    idSensor = argv[i];
                } else if (argumento == "--formato") {
                    if (++i >= argc) {
                        throw std::invalid_argument("--formato exige 'json' ou 'csv'.");
                    }
                    const std::string fmt = argv[i];
                    if (fmt == "json" || fmt == "JSON") {
                        formato = FormatoMensagem::JSON;
                    } else if (fmt == "csv" || fmt == "CSV") {
                        formato = FormatoMensagem::CSV;
                    } else {
                        throw std::invalid_argument("Formato desconhecido: " + fmt + " (use json ou csv)");
                    }
                } else if (!argumento.empty() && argumento[0] != '-' && !caminhoConfigurado) {
                    caminho = argumento;
                    caminhoConfigurado = true;
                } else {
                    throw std::invalid_argument("Argumento nao reconhecido: " + argumento);
                }
            }

            // Validar configuracao UDP se fornecida
            if ((!ipServidor.empty() && portaUdp == 0) || (ipServidor.empty() && portaUdp != 0)) {
                throw std::invalid_argument("Para usar UDP, informe ambos: --ip <IP> e --porta <PORTA>.");
            }

            SensorSom sensor(caminho);
            MonitoramentoSom monitor(
                sensor,
                std::chrono::milliseconds(intervaloMs),
                static_cast<std::size_t>(quantidadeAmostras));

            std::unique_ptr<ClienteUDP> cliente;
            std::unique_ptr<ProtocoloSom> protocolo;

            if (!ipServidor.empty() && portaUdp > 0) {
                cliente = std::make_unique<ClienteUDP>(ipServidor, portaUdp);
                protocolo = std::make_unique<ProtocoloSom>(idSensor, "raw");
                monitor.configurarUDP(cliente.get(), protocolo.get(), formato);
            }

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
        if (valor < minimo || valor > maximo) {
            throw std::invalid_argument("Valor fora da faixa permitida para " + campo);
        }
        return valor;
    }

    /** @brief Exibe o manual de uso das opcoes da linha de comando. */
    void mostrarAjuda(const char* nomePrograma) const {
        std::cout << "Uso: " << nomePrograma << " [OPCOES] [ARQUIVO_ADC]\n\n"
                  << "Opcoes gerais:\n"
                  << "  --arquivo CAMINHO       Caminho do arquivo IIO ou texto de teste.\n"
                  << "  --intervalo-ms INT      Intervalo entre leituras em ms (padrao: 200).\n"
                  << "  --amostras INT          Quantidade de amostras a coletar (padrao: 20).\n"
                  << "  --continuo              Coleta indefinida ate Ctrl+C.\n"
                  << "  --ajuda, -h             Exibe esta mensagem.\n\n"
                  << "Opcoes de comunicacao UDP (Entrega 3):\n"
                  << "  --ip ENDERECO_IPV4      IP do servidor central receptor.\n"
                  << "  --porta PORTA           Porta UDP do servidor (1 a 65535).\n"
                  << "  --id-sensor NOME        Identificador do sensor (padrao: KY-037).\n"
                  << "  --formato json|csv      Formato da mensagem UDP (padrao: json).\n\n"
                  << "Exemplos:\n"
                  << "  " << nomePrograma << " dados/leitura_exemplo.txt --amostras 5\n"
                  << "  " << nomePrograma << " --ip 192.168.42.10 --porta 5000 --continuo --intervalo-ms 100\n";
    }
};

int main(int argc, char* argv[]) {
    AplicacaoSensorSom app;
    return app.executar(argc, argv);
}
