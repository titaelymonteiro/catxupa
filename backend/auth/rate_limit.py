"""Limita tentativas de login falhadas por email, para dificultar ataques
de força bruta. Guardado em memória (reinicia se o servidor reiniciar) —
suficiente para uma farmácia pequena com um único processo; se um dia isto
correr com vários workers/processos, precisa de passar para algo partilhado
(ex: Redis) porque cada processo teria a sua própria contagem.
"""
import time
from collections import defaultdict

LIMITE_TENTATIVAS = 5
JANELA_SEGUNDOS = 15 * 60  # 15 minutos

_tentativas = defaultdict(list)


def _limpar_antigas(email: str):
    agora = time.time()
    _tentativas[email] = [t for t in _tentativas[email] if agora - t < JANELA_SEGUNDOS]


def esta_bloqueado(email: str) -> bool:
    _limpar_antigas(email)
    return len(_tentativas[email]) >= LIMITE_TENTATIVAS


def registar_falha(email: str):
    _limpar_antigas(email)
    _tentativas[email].append(time.time())


def limpar_tentativas(email: str):
    _tentativas.pop(email, None)


def tentativas_restantes(email: str) -> int:
    _limpar_antigas(email)
    return max(0, LIMITE_TENTATIVAS - len(_tentativas[email]))


def resetar_tudo():
    """Só para os testes automáticos — limpa todo o estado em memória."""
    _tentativas.clear()