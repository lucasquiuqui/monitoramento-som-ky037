#include "SensorSom.hpp"

#include <fstream>
#include <limits>
#include <stdexcept>
#include <utility>

SensorSom::SensorSom(std::string caminhoAdc)
    : caminhoAdc_(std::move(caminhoAdc)) {
    if (caminhoAdc_.empty()) {
        throw std::invalid_argument("O caminho do ADC nao pode estar vazio.");
    }
}

int SensorSom::lerBruto() {
    std::ifstream arquivo(caminhoAdc_);
    if (!arquivo.is_open()) {
        throw std::runtime_error("Nao foi possivel abrir o ADC: " + caminhoAdc_);
    }

    long long valor = 0;
    if (!(arquivo >> valor) || valor < 0 ||
        valor > std::numeric_limits<int>::max()) {
        throw std::runtime_error("Valor ADC invalido em: " + caminhoAdc_);
    }

    // Um arquivo sysfs/IIO de leitura bruta deve conter um unico numero.
    std::string textoExtra;
    if (arquivo >> textoExtra) {
        throw std::runtime_error("Conteudo adicional inesperado no ADC: " + caminhoAdc_);
    }

    ultimaLeitura_ = static_cast<int>(valor);
    possuiLeitura_ = true;
    return ultimaLeitura_;
}

bool SensorSom::possuiLeitura() const noexcept {
    return possuiLeitura_;
}

int SensorSom::obterUltimaLeitura() const {
    if (!possuiLeitura_) {
        throw std::logic_error("Ainda nao existe leitura valida.");
    }
    return ultimaLeitura_;
}

const std::string& SensorSom::obterCaminhoAdc() const noexcept {
    return caminhoAdc_;
}
