#ifndef SENSOR_SOM_HPP
#define SENSOR_SOM_HPP

#include <string>

/**
 * @brief Representa um sensor de som KY-037 lido pelo ADC da STM32MP1.
 *
 * @details A classe consulta uma entrada analógica exposta pelo subsistema
 * IIO do Linux (arquivo in_voltageX_raw). O valor retornado e uma contagem
 * bruta do ADC, e NAO uma medicao de decibeis (dB).
 * O caminho e recebido no construtor para permitir testes sem a placa.
 */
class SensorSom {
public:
    /**
     * @brief Inicializa o sensor com o arquivo de leitura do ADC.
     * @param caminhoAdc Caminho do arquivo in_voltageX_raw ou de teste.
     * @throws std::invalid_argument Se o caminho estiver vazio.
     */
    explicit SensorSom(std::string caminhoAdc);

    /**
     * @brief Le uma nova amostra bruta do ADC.
     * @return Valor inteiro nao negativo obtido do arquivo.
     * @throws std::runtime_error Se o arquivo nao puder ser aberto ou
     * se o conteudo nao representar uma leitura valida.
     */
    int lerBruto();

    /**
     * @brief Informa se ja houve uma leitura bem-sucedida.
     * @return true apos a primeira leitura valida; false caso contrario.
     */
    bool possuiLeitura() const noexcept;

    /**
     * @brief Consulta a ultima leitura obtida com sucesso.
     * @return Ultimo valor bruto lido.
     * @throws std::logic_error Se nenhuma leitura foi feita.
     */
    int obterUltimaLeitura() const;

    /**
     * @brief Informa o arquivo usado como fonte de leitura.
     * @return Referencia ao caminho configurado.
     */
    const std::string& obterCaminhoAdc() const noexcept;

private:
    std::string caminhoAdc_;  ///< Arquivo do canal ADC no Linux.
    int ultimaLeitura_ = 0;   ///< Ultima contagem bruta valida.
    bool possuiLeitura_ = false; ///< Indica se a ultimaLeitura_ e valida.
};

#endif  // SENSOR_SOM_HPP
