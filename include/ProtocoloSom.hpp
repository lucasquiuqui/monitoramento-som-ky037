#ifndef PROTOCOLO_SOM_HPP
#define PROTOCOLO_SOM_HPP

#include <cstdint>
#include <string>

/**
 * @brief Formato de serializacao das mensagens do protocolo UDP.
 */
enum class FormatoMensagem {
    JSON,   ///< Mensagem em formato JSON (padrao IoT).
    CSV     ///< Mensagem em formato CSV compacto.
};

/**
 * @brief Responsavel pela formatacao e encapsulamento dos pacotes de telemetria do KY-037.
 *
 * @details Atende estritamente aos requisitos do projeto de Programacao Aplicada:
 * - Identificador do sensor/grupo
 * - Valor atual lido
 * - Unidade de medida
 * - Timestamp em milissegundos
 */
class ProtocoloSom {
public:
    /**
     * @brief Cria um construtor de pacotes configurando o identificador do sensor.
     * @param idSensor Nome ou identificador do sensor (padrao: "KY-037").
     * @param unidade Unidade do dado transmitido (padrao: "raw").
     */
    explicit ProtocoloSom(std::string idSensor = "KY-037", std::string unidade = "raw");

    /**
     * @brief Monta a mensagem serializada contendo os dados da leitura.
     * @param valor Valor numerico lido do sensor (ex: contagem bruta do ADC).
     * @param formato Formato desejado (JSON ou CSV).
     * @return String contendo a mensagem formatada.
     */
    std::string empacotar(int valor, FormatoMensagem formato = FormatoMensagem::JSON) const;

    /**
     * @brief Monta a mensagem serializada com timestamp explicito.
     * @param valor Valor numerico lido do sensor.
     * @param timestampMs Timestamp em milissegundos desde a epoca UNIX.
     * @param formato Formato desejado (JSON ou CSV).
     * @return String contendo a mensagem formatada.
     */
    std::string empacotarComTimestamp(int valor,
                                      std::int64_t timestampMs,
                                      FormatoMensagem formato = FormatoMensagem::JSON) const;

    /**
     * @brief Obtem o identificador configurado.
     */
    const std::string& obterIdSensor() const;

    /**
     * @brief Obtem a unidade configurada.
     */
    const std::string& obterUnidade() const;

private:
    std::string idSensor_;  ///< Identificador do sensor/grupo.
    std::string unidade_;   ///< Unidade de medida dos dados.
};

#endif  // PROTOCOLO_SOM_HPP
