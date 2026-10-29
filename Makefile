CXX ?= g++
ARM_CXX ?= $(HOME)/Downloads/arm-buildroot-linux-gnueabihf_sdk-buildroot/bin/arm-buildroot-linux-gnueabihf-g++
CXXFLAGS = -std=c++17 -Wall -Wextra -Wpedantic -O2 -pthread -Iinclude
FONTES = src/SensorSom.cpp src/MonitoramentoSom.cpp

.PHONY: all test arm docs clean
all: sensor_som

sensor_som: $(FONTES) main.cpp include/SensorSom.hpp include/MonitoramentoSom.hpp
	$(CXX) $(CXXFLAGS) $(FONTES) main.cpp -o $@

teste_sensor_som: src/SensorSom.cpp testes/teste_sensor_som.cpp include/SensorSom.hpp
	$(CXX) $(CXXFLAGS) src/SensorSom.cpp testes/teste_sensor_som.cpp -o $@

teste_monitoramento_som: $(FONTES) testes/teste_monitoramento_som.cpp include/MonitoramentoSom.hpp
	$(CXX) $(CXXFLAGS) $(FONTES) testes/teste_monitoramento_som.cpp -o $@

test: sensor_som teste_sensor_som teste_monitoramento_som
	./teste_sensor_som
	./teste_monitoramento_som
	./sensor_som dados/leitura_exemplo.txt --amostras 3 --intervalo-ms 1

arm:
	$(ARM_CXX) $(CXXFLAGS) $(FONTES) main.cpp -o sensor_som_arm
	file sensor_som_arm

docs:
	doxygen Doxyfile

clean:
	rm -f sensor_som sensor_som_arm teste_sensor_som teste_monitoramento_som
