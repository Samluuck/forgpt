Módulo de Horas Extras para Odoo
Este módulo de Odoo extiende la funcionalidad del módulo de asistencia para calcular horas extras diurnas, nocturnas, en domingos/feriados, y horas nocturnas normales. Calcula las horas extras basándose en las horas de entrada y salida registradas por los empleados.

Características
Cálculo de horas extras diurnas después de una hora especificada.
Cálculo de horas extras nocturnas a partir de las 20:00.
Identificación y cálculo de horas extras en domingos y feriados.
Cálculo de horas nocturnas normales entre 17:30 y 03:30.
Instalación
Clona este repositorio o descarga el módulo en tu servidor Odoo.
Coloca el módulo en la carpeta de addons de tu instancia Odoo.
Actualiza la lista de aplicaciones desde el panel de administración de Odoo.
Busca el módulo "Módulo de Horas Extras" y haz clic en instalar.
Configuración
Una vez instalado el módulo, ve a Configuración > Ajustes (en el módulo de Asistencias) para configurar las siguientes opciones:

Horario Diurno: La hora a partir de la cual se deben calcular las horas extras diurnas (formato 24h, ej. 18:30).
Horas Nocturnas: Activar si deseas calcular horas nocturnas a partir de las 20:00.
Tolerancia Llegada Tardía: Define la cantidad de minutos de tolerancia antes de que una llegada se considere tardía.
Uso
Una vez configurado el módulo:

Los empleados registran sus horas de entrada y salida como de costumbre.
El módulo calcula automáticamente las horas extras basándose en las configuraciones definidas y las registra en los respectivos campos de horas extras en los registros de asistencia de los empleados.