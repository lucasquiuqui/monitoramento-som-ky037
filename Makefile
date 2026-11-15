CXX ?= g++
ARM_CXX ?= arm-linux-gnueabihf-g++
CXXFLAGS = -std=c++17 -Wall -Wextra -Wpedantic -O2 -pthread -Iinclude
FONTES = src/SensorSom.cpp src/MonitoramentoSom.cpp src/ClienteUDP.cpp src/ProtocoloSom.cpp
HEADERS = include/SensorSom.hpp include/MonitoramentoSom.hpp include/ClienteUDP.hpp include/ProtocoloSom.hpp

.PHONY: all test test-gui test-gui-smoke gui arm docs clean
all: sensor_som

sensor_som: $(FONTES) main.cpp $(HEADERS)
	$(CXX) $(CXXFLAGS) $(FONTES) main.cpp -o $@

teste_sensor_som: src/SensorSom.cpp testes/teste_sensor_som.cpp include/SensorSom.hpp
	$(CXX) $(CXXFLAGS) src/SensorSom.cpp testes/teste_sensor_som.cpp -o $@

teste_monitoramento_som: $(FONTES) testes/teste_monitoramento_som.cpp $(HEADERS)
	$(CXX) $(CXXFLAGS) $(FONTES) testes/teste_monitoramento_som.cpp -o $@

teste_protocolo_udp: src/ClienteUDP.cpp src/ProtocoloSom.cpp testes/teste_protocolo_udp.cpp $(HEADERS)
	$(CXX) $(CXXFLAGS) src/ClienteUDP.cpp src/ProtocoloSom.cpp testes/teste_protocolo_udp.cpp -o $@

test: sensor_som teste_sensor_som teste_monitoramento_som teste_protocolo_udp
	./teste_sensor_som
	./teste_monitoramento_som
	./teste_protocolo_udp
	./sensor_som dados/leitura_exemplo.txt --amostras 3 --intervalo-ms 1
	python3 -m unittest discover -s testes -p 'teste_interface_udp.py' -v
	python3 -m unittest discover -s testes -p 'teste_melhorias_interface.py' -v
	python3 -m unittest discover -s testes -p 'teste_historico_longo.py' -v
	python3 -m unittest discover -s testes -p 'teste_relatorio_excel.py' -v
	python3 -m unittest discover -s testes -p 'teste_limpeza_alertas.py' -v

test-gui:
	python3 -m unittest discover -s testes -p 'teste_interface_udp.py' -v
	python3 -m unittest discover -s testes -p 'teste_melhorias_interface.py' -v
	python3 -m unittest discover -s testes -p 'teste_historico_longo.py' -v
	python3 -m unittest discover -s testes -p 'teste_relatorio_excel.py' -v
	python3 -m unittest discover -s testes -p 'teste_limpeza_alertas.py' -v

# Requer um ambiente grafico Tkinter; em CI Linux pode-se usar xvfb-run.
test-gui-smoke:
	python3 -m unittest discover -s testes -p 'teste_gui_smoke.py' -v
	python3 -m unittest discover -s testes -p 'teste_layout_janela.py' -v

gui:
	python3 interface_grafica.py --porta 8080

arm:
	$(ARM_CXX) $(CXXFLAGS) $(FONTES) main.cpp -o sensor_som_arm
	file sensor_som_arm

docs:
	doxygen Doxyfile

clean:
	rm -f sensor_som sensor_som_arm teste_sensor_som teste_monitoramento_som teste_protocolo_udp
