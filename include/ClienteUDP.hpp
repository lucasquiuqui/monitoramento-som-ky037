#ifndef CLIENTE_UDP_HPP
#define CLIENTE_UDP_HPP

#include <cstddef>
#include <string>

/**
 * @brief Encapsula um socket cliente UDP para envio de datagramas no Linux embarcado.
 *
 * @details Implementa o padrao RAII para gerenciamento do descritor de socket.
 * Nao utiliza variaveis globais nem expoe detalhes da API de sockets POSIX.
 */
class ClienteUDP {
public:
    /**
     * @brief Cria o socket UDP e configura o endereco de destino.
     * @param ipServidor Endereco IPv4 do servidor (ex: "192.168.42.10" ou "127.0.0.1").
     * @param porta Porta UDP do servidor (1 a 65535).
     * @throws std::invalid_argument Se o IP for invalido ou a porta estiver fora do intervalo.
     * @throws std::runtime_error Se a criacao do socket falhar.
     */
    ClienteUDP(const std::string& ipServidor, int porta);

    /**
     * @brief Fecha o descritor de socket de forma segura (RAII).
     */
    ~ClienteUDP();

    // Desabilitar copia para evitar duplicacao de descritor
    ClienteUDP(const ClienteUDP&) = delete;
    ClienteUDP& operator=(const ClienteUDP&) = delete;

    // Permitir movimentacao (move semantics)
    ClienteUDP(ClienteUDP&& outro) noexcept;
    ClienteUDP& operator=(ClienteUDP&& outro) noexcept;

    /**
     * @brief Transmite uma mensagem em texto via datagrama UDP.
     * @param mensagem Conteudo a ser enviado.
     * @return Quantidade de bytes enviados.
     * @throws std::runtime_error Em caso de falha no envio.
     */
    std::size_t enviar(const std::string& mensagem) const;

    /**
     * @brief Obtem o IP de destino configurado.
     * @return Endereco IP.
     */
    const std::string& obterIpServidor() const;

    /**
     * @brief Obtem a porta de destino configurada.
     * @return Numero da porta.
     */
    int obterPorta() const;

private:
    int descritorSocket_;       ///< Descritor do socket POSIX (-1 se fechado).
    std::string ipServidor_;    ///< IP de destino configurado.
    int porta_;                 ///< Porta UDP de destino.
};

#endif  // CLIENTE_UDP_HPP
