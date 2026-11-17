"""FACTORY METHOD (registro): crea objetos por nombre sin que el cliente conozca las clases.

Registrar un nombre nuevo es EXTENDER, no modificar (principio abierto/cerrado).
No es un Singleton: cada servicio tiene su propia fábrica, así las pruebas inyectan sus dobles.
"""


class Fabrica:
    def __init__(self, tipo: str):
        self._tipo = tipo
        self._creadores = {}

    def registrar(self, nombre: str, creador):
        self._creadores[nombre] = creador

    def crear(self, nombre: str):
        if nombre not in self._creadores:
            raise ValueError(f"{self._tipo} no soportada: {nombre}")
        return self._creadores[nombre]()
