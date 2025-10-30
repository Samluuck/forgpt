# Informe de Rendimiento

Módulo para Odoo 15 EE que genera reportes de rendimiento de proyectos basados en horas trabajadas.

## Características

- **Filtros por rango de fechas**: Selecciona el período para analizar
- **Selección de empleados**: Filtra por empleados específicos o incluye todos
- **Filtro de proyectos**: Muestra solo proyectos con horas cargadas o todos
- **Exportación a Excel**: Genera un archivo Excel con estructura personalizada

## Estructura del Reporte

El reporte Excel generado contiene:

1. **Fila 1**: Encabezados con nombres de empleados, seguidos de columnas HONORARIOS, COSTOS y DIFERENCIA
2. **Fila 2**: Costo por hora de cada empleado
3. **Filas 3+**: Proyectos con las horas trabajadas por cada empleado
4. **Última fila**: Totales

## Cálculos

- **Costo por hora**: Se obtiene del campo `timesheet_cost` del empleado
- **Costos**: Suma de (horas trabajadas × costo por hora) por proyecto
- **Honorarios**: Por ahora se establece en 0 (a personalizar según necesidad)
- **Diferencia**: Honorarios - Costos

## Instalación

1. Copiar el módulo en la carpeta de addons custom
2. Actualizar lista de aplicaciones
3. Instalar el módulo "Informe de Rendimiento"

## Uso

1. Ir a **Parte de Horas > Informe de Rendimiento**
2. Seleccionar los filtros deseados
3. Hacer clic en **Generar Reporte**
4. Descargar el archivo Excel generado

## Dependencias

- `base`
- `hr`
- `hr_timesheet`
- `project`
- Python: `xlsxwriter`

## Notas

- El módulo requiere que los empleados tengan configurado el costo por hora en su ficha
- Las horas se obtienen del módulo de Parte de Horas (hr_timesheet)
