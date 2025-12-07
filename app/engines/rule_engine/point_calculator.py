"""
PointCalculator - Calcula puntos con multiplicadores y bonus

Responsabilidades:
- Calcular puntos base según regla
- Aplicar multiplicadores por nivel de usuario
- Aplicar bonus/penalizaciones
- Validar que los puntos no caigan por debajo del mínimo configurado
"""



class PointCalculator:
    """
    Calcula puntos para transacciones

    Usage:
        calculator = PointCalculator(min_points=0, allow_negative=True)
        final_points = calculator.calculate(
            base_points=100,
            user_level_multiplier=1.2,
            bonus_points=50
        )
    """

    def __init__(self, min_points: int = 0, allow_negative: bool = True):
        """
        Args:
            min_points: Puntos mínimos permitidos (default: 0)
            allow_negative: Si se permiten puntos negativos (penalizaciones)
        """
        self.min_points = min_points
        self.allow_negative = allow_negative

    def calculate(
        self,
        base_points: int,
        user_level_multiplier: float = 1.0,
        bonus_points: int = 0,
        penalty_points: int = 0,
    ) -> int:
        """
        Calcula puntos finales aplicando multiplicadores y bonus

        Args:
            base_points: Puntos base de la regla
            user_level_multiplier: Multiplicador por nivel (ej: 1.2 para nivel 3)
            bonus_points: Puntos adicionales (ej: bonus por velocidad)
            penalty_points: Puntos a restar (valor positivo, se restará)

        Returns:
            Puntos finales calculados
        """
        # Calcular puntos base con multiplicador
        multiplied_points = base_points * user_level_multiplier

        # Aplicar bonus/penalizaciones
        final_points = multiplied_points + bonus_points - penalty_points

        # Redondear (los puntos son enteros)
        final_points = round(final_points)

        # Validar mínimo
        if not self.allow_negative and final_points < self.min_points:
            final_points = self.min_points

        return final_points

    def calculate_from_rule(
        self, rule_points: int, user_level: int = 1, additional_bonus: int = 0
    ) -> int:
        """
        Calcula puntos desde una regla aplicando multiplicador de nivel

        Args:
            rule_points: Puntos definidos en la regla
            user_level: Nivel del usuario (1-5)
            additional_bonus: Bonus adicional a aplicar

        Returns:
            Puntos finales
        """
        multiplier = self.get_level_multiplier(user_level)
        return self.calculate(
            base_points=rule_points, user_level_multiplier=multiplier, bonus_points=additional_bonus
        )

    @staticmethod
    def get_level_multiplier(user_level: int) -> float:
        """
        Obtiene el multiplicador correspondiente a un nivel de usuario

        Args:
            user_level: Nivel del usuario (1-5)

        Returns:
            Multiplicador (1.0 - 1.5)
        """
        # Según rules.yaml progression_rules
        level_multipliers = {
            1: 1.0,  # Aprendiz de Seguridad
            2: 1.0,  # Vigilante del Código
            3: 1.1,  # Guardián DevSecOps
            4: 1.2,  # Centinela Élite
            5: 1.5,  # Maestro de la Seguridad
        }

        return level_multipliers.get(user_level, 1.0)

    @staticmethod
    def calculate_user_level(total_points: int) -> int:
        """
        Calcula el nivel de un usuario basado en sus puntos totales

        Args:
            total_points: Puntos totales acumulados

        Returns:
            Nivel (1-5)
        """
        # Según rules.yaml progression_rules
        if total_points < 500:
            return 1  # Aprendiz de Seguridad
        elif total_points < 1500:
            return 2  # Vigilante del Código
        elif total_points < 4000:
            return 3  # Guardián DevSecOps
        elif total_points < 10000:
            return 4  # Centinela Élite
        else:
            return 5  # Maestro de la Seguridad

    @staticmethod
    def get_level_info(level: int) -> dict:
        """
        Obtiene información completa de un nivel

        Args:
            level: Nivel (1-5)

        Returns:
            Dict con name, min_points, max_points, perks
        """
        levels = {
            1: {'name': 'Aprendiz de Seguridad', 'min_points': 0, 'max_points': 499, 'perks': []},
            2: {
                'name': 'Vigilante del Código',
                'min_points': 500,
                'max_points': 1499,
                'perks': ['Acceso a dashboard avanzado'],
            },
            3: {
                'name': 'Guardián DevSecOps',
                'min_points': 1500,
                'max_points': 3999,
                'perks': ['Acceso a dashboard avanzado', 'Multiplicador de puntos x1.1'],
            },
            4: {
                'name': 'Centinela Élite',
                'min_points': 4000,
                'max_points': 9999,
                'perks': [
                    'Acceso a dashboard avanzado',
                    'Multiplicador de puntos x1.2',
                    'Puede iniciar misiones de equipo',
                ],
            },
            5: {
                'name': 'Maestro de la Seguridad',
                'min_points': 10000,
                'max_points': None,
                'perks': [
                    'Acceso a dashboard avanzado',
                    'Multiplicador de puntos x1.5',
                    'Puede iniciar misiones de equipo',
                    'Reconocimiento en hall of fame',
                ],
            },
        }

        return levels.get(level, levels[1])

    @staticmethod
    def calculate_progress_to_next_level(current_points: int) -> dict:
        """
        Calcula el progreso hacia el siguiente nivel

        Args:
            current_points: Puntos actuales del usuario

        Returns:
            Dict con current_level, next_level, points_needed, progress_percentage
        """
        current_level = PointCalculator.calculate_user_level(current_points)
        current_level_info = PointCalculator.get_level_info(current_level)

        if current_level == 5:
            # Nivel máximo alcanzado
            return {
                'current_level': 5,
                'next_level': None,
                'points_needed': 0,
                'progress_percentage': 100.0,
            }

        next_level_info = PointCalculator.get_level_info(current_level + 1)
        points_needed = next_level_info['min_points'] - current_points

        # Calcular porcentaje de progreso en el nivel actual
        level_range = current_level_info['max_points'] - current_level_info['min_points'] + 1
        points_in_current_level = current_points - current_level_info['min_points']
        progress_percentage = (points_in_current_level / level_range) * 100

        return {
            'current_level': current_level,
            'next_level': current_level + 1,
            'points_needed': points_needed,
            'progress_percentage': round(progress_percentage, 2),
        }
