"""
singleton.py - Gestión del singleton global de RuleLoader

Proporciona funciones helper para acceder al RuleLoader
de forma global en toda la aplicación.
"""

from pathlib import Path

from .loader import RuleLoader

# ============================================================================
# SINGLETON GLOBAL
# ============================================================================

_global_loader: RuleLoader | None = None


def get_rule_loader() -> RuleLoader:
    """
    Obtiene la instancia global del RuleLoader (singleton)

    Usage:
        loader = get_rule_loader()
        rule = loader.get_rule_by_id("PTS-001")

    Returns:
        Instancia del RuleLoader

    Raises:
        RuntimeError: Si el loader no ha sido inicializado
    """
    global _global_loader

    if _global_loader is None:
        # Default path
        rules_path = Path(__file__).parent.parent.parent.parent / 'config' / 'rules.yaml'
        _global_loader = RuleLoader(rules_path)
        _global_loader.load()

    return _global_loader


def init_rule_loader(rules_path: str | Path) -> RuleLoader:
    """
    Inicializa el RuleLoader global con un path específico

    Args:
        rules_path: Path al archivo rules.yaml

    Returns:
        Instancia del RuleLoader

    Raises:
        FileNotFoundError: Si el archivo no existe
        ValueError: Si el archivo tiene formato inválido
    """
    global _global_loader
    _global_loader = RuleLoader(rules_path)
    _global_loader.load()
    return _global_loader


def reset_rule_loader() -> None:
    """
    Resetea el singleton global.

    Útil principalmente para testing.
    """
    global _global_loader
    _global_loader = None


def is_loader_initialized() -> bool:
    """
    Verifica si el singleton global está inicializado

    Returns:
        True si el loader está inicializado, False en caso contrario
    """
    return _global_loader is not None and _global_loader.is_loaded
