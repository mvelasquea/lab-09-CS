"""Ciclo de vida de la cita: patrón STATE (implementa la máquina de estados del Lab 05).

Estados: SOLICITADA -> CONFIRMADA -> ATENDIDA | NO_ASISTIO ;  SOLICITADA/CONFIRMADA -> CANCELADA.
La clase base PROHÍBE todas las transiciones; cada estado redefine SOLO las permitidas,
así una transición inválida es imposible por construcción.
"""


class EstadoCita:
    nombre = "?"

    def verificar_solicitable(self, cita):
        raise ValueError(f"No se puede solicitar una cita {self.nombre}")

    def confirmar(self, cita, cupo, codigo):
        raise ValueError(f"No se puede confirmar una cita {self.nombre}")

    def atender(self, cita):
        raise ValueError(f"No se puede atender una cita {self.nombre}")

    def marcar_no_asistio(self, cita):
        raise ValueError(f"No se puede marcar inasistencia en una cita {self.nombre}")

    def cancelar(self, cita):
        raise ValueError(f"No se puede cancelar una cita {self.nombre}")


class Solicitada(EstadoCita):
    nombre = "SOLICITADA"

    def verificar_solicitable(self, cita):
        pass

    def confirmar(self, cita, cupo, codigo):
        cita.cupo, cita.codigo = cupo, codigo
        cita.cambiar_a(Confirmada())

    def cancelar(self, cita):
        cita.cambiar_a(Cancelada())


class Confirmada(EstadoCita):
    nombre = "CONFIRMADA"

    def verificar_solicitable(self, cita):
        raise ValueError("La cita ya fue confirmada")

    def atender(self, cita):
        cita.cambiar_a(Atendida())

    def marcar_no_asistio(self, cita):
        cita.cambiar_a(NoAsistio())

    def cancelar(self, cita):
        cita.cambiar_a(Cancelada())


class Atendida(EstadoCita):
    nombre = "ATENDIDA"


class NoAsistio(EstadoCita):
    nombre = "NO_ASISTIO"


class Cancelada(EstadoCita):
    nombre = "CANCELADA"

    def verificar_solicitable(self, cita):
        raise ValueError("La cita está cancelada")
