# Módulo: Control de Solicitud de Horas Extras

Este módulo permite gestionar las solicitudes de horas extras, integrando aprobaciones, cálculo automático de montos por hora o día, y su inclusión directa en la nómina del empleado.

## 🧩 Modelos Afectados

- **hr.overtime**: Modelo principal para registrar solicitudes de horas extras.
- **overtime.type** y **overtime.type.rule**: Definen los tipos de horas extras (remuneradas o compensadas) y las reglas de cálculo por rangos horarios.
- **hr.contract**: Se añaden campos calculados `over_day` y `over_hour` que representan salario diario y por hora.
- **hr.payslip**: Se extiende para incluir las horas extras en la generación y validación de la nómina.
- **hr.attendance**: Relacionado automáticamente con las fechas de la solicitud de horas extras.
- **hr.leave.allocation**: Si el tipo es "licencia", se genera una asignación automática de ausencia.

## ⚙️ Configuración del Módulo

1. **Salario Base del Contrato**: El campo `wage` debe estar configurado correctamente en el contrato (`hr.contract`) para calcular `over_hour` y `over_day`.
2. **Tipos de Horas Extras**:
   - Crear desde el menú `Tipo de Horas Extras`.
   - Puede ser de tipo `cash` (remunerado) o `leave` (licencia compensatoria).
   - Se puede definir reglas por tramos horarios (`from_hrs`, `to_hrs`) y tipo (`diurnal`, `nocturnal`) con multiplicadores.
3. **Asignación de Regla Salarial**: El módulo crea reglas salariales específicas para horas extras diurnas y nocturnas, ligadas a una estructura de nómina predefinida.


## Cómo Funciona el Cálculo de Horas Extras

1. **Solicitud**:
   - El empleado realiza una solicitud indicando fechas y duración (en horas o días).
   - Se valida automáticamente si el rango se solapa con otros.
   - El sistema detecta si la fecha cae en feriado o domingo.

2. **Aprobación**:
   - Puede pasar por estados: `draft → f_approve → approved`.
   - Si el tipo es `leave`, se genera automáticamente una asignación de ausencia validada.

3. **Cálculo del Monto**:
   - **Diurnas** (Ej: 50% extra): Se calculan si el horario cae dentro del tramo diurno definido (ej: 08:00–20:00).
   - **Nocturnas** (Ej: 100% extra): Se calculan si el horario cae dentro del tramo nocturno (ej: 20:00–06:00).
   - Se toma el valor `over_hour` del contrato y se aplica el multiplicador definido en las reglas.

4. **Incorporación a Nómina**:
   - Al generar el `hr.payslip`, el método `get_payslip_inputs_hook_overtime` agrega automáticamente las líneas de input `OT_DIURNAL` y `OT_NOCTURNAL`.
   - Al validar la nómina (`action_payslip_done`), las solicitudes se marcan como pagadas (`payslip_paid = True`).

## Acciones de Servidor Incluidas

- **Recalcular salario por contrato** (`action_recompute_salary`): Actualiza el valor de `over_day` y `over_hour`.
- **Indexar contratos** (`action_index_contracts`): Actualiza índices para los contratos.

## Permisos de Seguridad

- Los usuarios del grupo `base.group_user` tienen acceso completo a los modelos principales (`hr.overtime`, `overtime.type`, `overtime.type.rule`).
- Los permisos más avanzados (aprobación/rechazo) están restringidos al grupo `hr_holidays.group_hr_holidays_user`.

## 📂 Vistas y Navegación

- Menú principal: `Solicitud de Horas Extras`
  - Submenú: `Tipo de Horas Extras`
- Formulario amigable con pestañas:
  - Descripción, asistencia, horario, feriados, horas detalladas.
- Botones según estado: registrar, aprobar, rechazar, volver a borrador.

## Dependencias

- Módulos requeridos:
  - `hr`, `hr_contract`, `hr_attendance`, `hr_holidays`, `hr_payroll`, `project`, `hr_documenta`
- Dependencia externa:
  - `pandas` (para procesamiento de fechas y rangos)

## 📝 Notas Técnicas

- Todos los cálculos se ajustan automáticamente si se cruza medianoche.
- Incluye lógica para determinar si las fechas caen en feriado o domingo.
- La acción de creación asigna automáticamente las asistencias (`hr.attendance`) del empleado según las fechas.

---

