# Quantum Key Distribution (QKD) Simulator
As part of the QSSH protocol, which allows provably-secure shell access to a remote computer, this program can be used to simulate [BB84 QKD protocol](https://medium.com/quantum-untangled/quantum-key-distribution-and-bb84-protocol-6f03cc6263c5) is used between quantum computers.
To deal with the qubit limits imposed by quantum computers, this simulator allows for multiple repetitions of the BB84 protocol, limit is set on the config file, to use fewer qubits.

Noise config breaks the encryption as privacy amplification is not applied in the protocol.



