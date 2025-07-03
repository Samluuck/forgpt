# Módulo de Generación de Archivos Bancarios para Nóminas

Este módulo permite generar archivos TXT y EXCEL con la información de nóminas para su envío al banco.

## Requisitos Previos

- Módulo `hr_payroll` instalado
- Configuración correcta de:
  - Empleados (con identificación)
  - Estructuras salariales
  - Lotes de nómina

## Campos Obligatorios

Para que la generación de archivos funcione correctamente, deben completarse los siguientes campos:

### 1. En la Empresa (Configuración)
- **Número de Cuenta Bancaria**: `nro_cuenta`  
  Ubicación: `Configuración → Empresa → Pestaña "Contabilidad"`  
  Ejemplo: `12345678901234567890`

### 2. En los Empleados
- **Número de Identificación**: `identification_id`  
  Ubicación: `Recursos Humanos → Empleados → Pestaña "Información Personal"`  
  Ejemplo: `1234567890`

### 3. En las Estructuras Salariales
- **Es Aguinaldo**: `es_aguinaldo` (checkbox)  
  Ubicación: `Nómina → Configuración → Estructuras Salariales`  
  Ejemplo: Marcar si es para aguinaldos

## Proceso de Generación

1. **Crear un lote de nóminas**:
   - Ir a `Nómina → Lotes de Nómina → Crear`
   - Completar los datos requeridos y confirmar

2. **Generar archivos**:
   - Dentro del lote de nómina, hacer clic en "Generar Archivo Bancario"
   - Seleccionar entre:
     - **TXT**: Genera un archivo plano con formato para el banco
     - **EXCEL**: Genera una hoja de cálculo con los mismos datos

3. **Descargar archivos**:
   - El sistema mostrará una vista previa con el botón "Descargar"
   - El nombre del archivo será:
     - `Archivo_Banco.txt` para el formato TXT
     - `Archivo_Banco.xlsx` para el formato EXCEL

## Estructura del Archivo Generado

Los archivos contendrán las siguientes columnas en el orden indicado:

1. **Número de CI**: Identificación del empleado
2. **Cuenta Débito**: Número de cuenta de la empresa
3. **Concepto**: "Nomina de [Mes Año]"
4. **Importe**: Monto neto a pagar
5. **Aguinaldo**: Indicador SI/NO si es pago de aguinaldo

### Ejemplo de Contenido TXT

00078200713   1758530   1758530                Sanchez Gutman             Christian AlfredoE30   3027600 52025     3027600

### Ejemplo de Contenido EXCEL
| Numero de CI | Cuenta Debito        | Concepto            | Importe  | Aguinaldo |
|--------------|----------------------|---------------------|----------|-----------|
| 1234567890   | 12345678901234567890 | Nomina de Mayo 2023 | 2500000  |    NO     |
| 9876543210   | 12345678901234567890 | Nomina de Mayo 2023 | 1800000  |    SI     |

## Notas Importantes

- El módulo usa el monto de la regla con codigo NETO o NET de la nómina. Si no existe, usará ANT (anticipo)
- Si no se encuentra ninguna regla salarial válida, el importe será 0
- Los archivos se generan temporalmente en el sistema antes de ser descargados
- Para problemas técnicos, revisar los logs de Odoo donde se registra el proceso
