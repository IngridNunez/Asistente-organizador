import pytest

from src.agente import memoria


# La memoria vive en el proceso: sin limpiarla, lo que un test guarda para "u1"
# se colaría en el prompt de los tests siguientes.
@pytest.fixture(autouse=True)
def memoria_limpia():
    memoria.limpiar_memoria()
    yield
    memoria.limpiar_memoria()
