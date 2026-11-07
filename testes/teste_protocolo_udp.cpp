#include "ClienteUDP.hpp"
#include "ProtocoloSom.hpp"

#include <arpa/inet.h>
#include <cassert>
#include <chrono>
#include <cstring>
#include <iostream>
#include <netinet/in.h>
#include <string>
#include <sys/socket.h>
#include <thread>
#include <unistd.h>

/**
 * @brief Servidor UDP de teste para verificacao em loopback (127.0.0.1).
 */
class ServidorUDPTeste {
public:
    explicit ServidorUDPTeste(int porta) : descritor_(-1), porta_(porta) {
        descritor_ = ::socket(AF_INET, SOCK_DGRAM, 0);
        assert(descritor_ >= 0 && "Falha ao criar socket do servidor de teste");

        // Timeout de recepcao para o teste nao travar
        timeval timeout{};
        timeout.tv_sec = 2;
        timeout.tv_usec = 0;
        ::setsockopt(descritor_, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));

        sockaddr_in endereco{};
        std::memset(&endereco, 0, sizeof(endereco));
        endereco.sin_family = AF_INET;
        endereco.sin_port = htons(static_cast<uint16_t>(porta_));
        endereco.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

        const int resultadoBind = ::bind(
            descritor_, reinterpret_cast<const sockaddr*>(&endereco), sizeof(endereco));
        assert(resultadoBind == 0 && "Falha no bind do servidor de teste");
    }

    ~ServidorUDPTeste() {
        if (descritor_ >= 0) {
            ::close(descritor_);
        }
    }

    std::string receberMensagem() {
        char buffer[1024];
        std::memset(buffer, 0, sizeof(buffer));
        const ssize_t recebidos = ::recvfrom(descritor_, buffer, sizeof(buffer) - 1, 0, nullptr, nullptr);
        if (recebidos < 0) {
            return "";
        }
        return std::string(buffer, static_cast<std::size_t>(recebidos));
    }

private:
    int descritor_;
    int porta_;
};

int main() {
    std::cout << "Iniciando testes do Protocolo e Cliente UDP...\n";

    // 1. Teste de formatacao do Protocolo (JSON e CSV)
    {
        ProtocoloSom proto("KY-037", "raw");
        assert(proto.obterIdSensor() == "KY-037");
        assert(proto.obterUnidade() == "raw");

        const std::string json = proto.empacotarComTimestamp(4120, 1730810000000LL, FormatoMensagem::JSON);
        assert(json == "{\"sensor\":\"KY-037\",\"valor\":4120,\"unidade\":\"raw\",\"timestamp\":1730810000000}");

        const std::string csv = proto.empacotarComTimestamp(4120, 1730810000000LL, FormatoMensagem::CSV);
        assert(csv == "KY-037,4120,raw,1730810000000");
    }

    // 2. Teste de envio e recepcao UDP em loopback
    {
        const int portaTeste = 15432;
        ServidorUDPTeste servidor(portaTeste);
        ClienteUDP cliente("127.0.0.1", portaTeste);

        ProtocoloSom proto("TESTE_SOM", "raw");
        const std::string msgOriginal = proto.empacotarComTimestamp(3500, 123456789LL, FormatoMensagem::JSON);

        const std::size_t bytesEnviados = cliente.enviar(msgOriginal);
        assert(bytesEnviados == msgOriginal.size());

        const std::string msgRecebida = servidor.receberMensagem();
        assert(msgRecebida == msgOriginal);
    }

    std::cout << "Testes de Protocolo e UDP: OK\n";
    return 0;
}
