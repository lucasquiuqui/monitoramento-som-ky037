#include "ProtocoloSom.hpp"

#include <chrono>
#include <sstream>
#include <utility>

ProtocoloSom::ProtocoloSom(std::string idSensor, std::string unidade)
    : idSensor_(std::move(idSensor)), unidade_(std::move(unidade)) {
    if (idSensor_.empty()) {
        idSensor_ = "KY-037";
    }
    if (unidade_.empty()) {
        unidade_ = "raw";
    }
}

std::string ProtocoloSom::empacotar(int valor, FormatoMensagem formato) const {
    const auto agora = std::chrono::system_clock::now();
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        agora.time_since_epoch()).count();
    return empacotarComTimestamp(valor, ms, formato);
}

std::string ProtocoloSom::empacotarComTimestamp(int valor,
                                                std::int64_t timestampMs,
                                                FormatoMensagem formato) const {
    std::ostringstream oss;
    if (formato == FormatoMensagem::JSON) {
        // Formato JSON padrao:
        // {"sensor":"KY-037","valor":4120,"unidade":"raw","timestamp":1730817200123}
        oss << "{\"sensor\":\"" << idSensor_
            << "\",\"valor\":" << valor
            << ",\"unidade\":\"" << unidade_
            << "\",\"timestamp\":" << timestampMs
            << "}";
    } else {
        // Formato CSV compacto:
        // KY-037,4120,raw,1730817200123
        oss << idSensor_ << ',' << valor << ',' << unidade_ << ',' << timestampMs;
    }
    return oss.str();
}

const std::string& ProtocoloSom::obterIdSensor() const {
    return idSensor_;
}

const std::string& ProtocoloSom::obterUnidade() const {
    return unidade_;
}
