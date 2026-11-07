#include "ClienteUDP.hpp"

#include <arpa/inet.h>
#include <cstring>
#include <netinet/in.h>
#include <stdexcept>
#include <sys/socket.h>
#include <unistd.h>
#include <utility>

ClienteUDP::ClienteUDP(const std::string& ipServidor, int porta)
    : descritorSocket_(-1), ipServidor_(ipServidor), porta_(porta) {
    if (porta_ < 1 || porta_ > 65535) {
        throw std::invalid_argument("Porta invalida: deve estar entre 1 e 65535.");
    }

    descritorSocket_ = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (descritorSocket_ < 0) {
        throw std::runtime_error("Falha ao criar socket UDP: " + std::string(std::strerror(errno)));
    }

    // Validar se o endereco IP eh valido
    sockaddr_in enderecoTeste{};
    if (::inet_pton(AF_INET, ipServidor_.c_str(), &enderecoTeste.sin_addr) <= 0) {
        ::close(descritorSocket_);
        descritorSocket_ = -1;
        throw std::invalid_argument("Endereco IPv4 invalido: " + ipServidor_);
    }
}

ClienteUDP::~ClienteUDP() {
    if (descritorSocket_ >= 0) {
        ::close(descritorSocket_);
        descritorSocket_ = -1;
    }
}

ClienteUDP::ClienteUDP(ClienteUDP&& outro) noexcept
    : descritorSocket_(outro.descritorSocket_),
      ipServidor_(std::move(outro.ipServidor_)),
      porta_(outro.porta_) {
    outro.descritorSocket_ = -1;
}

ClienteUDP& ClienteUDP::operator=(ClienteUDP&& outro) noexcept {
    if (this != &outro) {
        if (descritorSocket_ >= 0) {
            ::close(descritorSocket_);
        }
        descritorSocket_ = outro.descritorSocket_;
        ipServidor_ = std::move(outro.ipServidor_);
        porta_ = outro.porta_;
        outro.descritorSocket_ = -1;
    }
    return *this;
}

std::size_t ClienteUDP::enviar(const std::string& mensagem) const {
    if (descritorSocket_ < 0) {
        throw std::runtime_error("Socket UDP nao esta aberto.");
    }

    sockaddr_in enderecoDestino{};
    std::memset(&enderecoDestino, 0, sizeof(enderecoDestino));
    enderecoDestino.sin_family = AF_INET;
    enderecoDestino.sin_port = htons(static_cast<uint16_t>(porta_));

    if (::inet_pton(AF_INET, ipServidor_.c_str(), &enderecoDestino.sin_addr) <= 0) {
        throw std::runtime_error("Erro de conversao de IP: " + ipServidor_);
    }

    const ssize_t bytesEnviados = ::sendto(
        descritorSocket_,
        mensagem.data(),
        mensagem.size(),
        0,
        reinterpret_cast<const sockaddr*>(&enderecoDestino),
        sizeof(enderecoDestino));

    if (bytesEnviados < 0) {
        throw std::runtime_error("Falha no envio UDP: " + std::string(std::strerror(errno)));
    }

    return static_cast<std::size_t>(bytesEnviados);
}

const std::string& ClienteUDP::obterIpServidor() const {
    return ipServidor_;
}

int ClienteUDP::obterPorta() const {
    return porta_;
}
