from odoo import models, fields, api

class AntuxDataHubManual(models.Model):
    _name = 'antux.datahub.manual'
    _description = 'Manual de Uso Antux Data Hub'

    name = fields.Char(string='Título', default='Manual de Uso', required=True)
    content = fields.Html(string='Contenido', required=True)

    @api.model
    def load_manual(self):
        """ Retorna la acción para abrir el manual (singleton) """
        manual = self.search([], limit=1)
        
    @api.model
    def load_manual(self):
        """ Retorna la acción para abrir el manual (singleton) """
        manual = self.search([], limit=1)
        
        html_content = """
<div class="container-fluid" style="font-family: 'Inter', sans-serif; color: #334155; line-height: 1.6;">
    <div class="row justify-content-center">
        <div class="col-12 col-lg-10">
            <!-- HEADER -->
            <div class="text-center py-5 mb-5" style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
                <h1 style="font-weight: 800; letter-spacing: -0.025em; margin-bottom: 0.5rem; color: white !important;">Antux Data Hub</h1>
                <p class="lead" style="opacity: 0.95;">Guía Completa de Usuario y Reportes</p>
            </div>

            <!-- INTRODUCCIÓN -->
            <div class="card border-0 shadow-sm mb-4" style="border-radius: 12px;">
                <div class="card-body p-4">
                    <h2 class="h4 text-primary mb-3"><i class="fa fa-info-circle mr-2"></i>1. Introducción</h2>
                    <p>
                        <strong>Antux Data Hub</strong> es la solución centralizada para la gestión de planillas de RRHH. 
                        Permite transformar archivos externos en registros normalizados, asegurando la integridad de los datos 
                        y facilitando el cumplimiento de las normativas vigentes (MTESS, IPS).
                    </p>
                </div>
            </div>

            <!-- CONFIGURACIÓN -->
            <div class="card border-0 shadow-sm mb-4" style="border-radius: 12px;">
                <div class="card-body p-4">
                    <h2 class="h4 text-primary mb-3"><i class="fa fa-cog mr-2"></i>2. Configuración Crítica</h2>
                    <div class="row">
                        <div class="col-md-6">
                            <h3 class="h6 font-weight-bold">Mapeo de Columnas</h3>
                            <p class="small">Configure los alias de las columnas para que el sistema reconozca automáticamente los encabezados de sus archivos Excel.</p>
                        </div>
                        <div class="col-md-6">
                            <h3 class="h6 font-weight-bold">Períodos</h3>
                            <p class="small">Defina los meses de trabajo antes de procesar cualquier lote. Es la base para la consolidación de datos.</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- PROCESO DE IMPORTACIÓN -->
            <div class="card border-0 shadow-sm mb-4" style="border-radius: 12px;">
                <div class="card-body p-4">
                    <h2 class="h4 text-primary mb-3"><i class="fa fa-upload mr-2"></i>3. Proceso de Importación</h2>
                    <div class="steps-container">
                        <div class="d-flex mb-3">
                            <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center mr-3" style="width: 32px; height: 32px; flex-shrink: 0;">1</div>
                            <div><strong>Crear Lote:</strong> Inicie un nuevo registro en "Planillas Procesadas".</div>
                        </div>
                        <div class="d-flex mb-3">
                            <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center mr-3" style="width: 32px; height: 32px; flex-shrink: 0;">2</div>
                            <div><strong>Importar:</strong> Use el botón <span class="badge badge-warning">Importar Planilla</span> y suba su archivo XLSX.</div>
                        </div>
                        <div class="d-flex">
                            <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center mr-3" style="width: 32px; height: 32px; flex-shrink: 0;">3</div>
                            <div><strong>Validar:</strong> El sistema verificará duplicados por CI automáticamente.</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- REPORTES DISPONIBLES -->
            <div class="card border-0 shadow-sm mb-4" style="border-radius: 12px;">
                <div class="card-body p-4">
                    <h2 class="h4 text-primary mb-4"><i class="fa fa-file-text mr-2"></i>4. Catálogo de Reportes</h2>
                    <div class="table-responsive">
                        <table class="table table-hover border-0">
                            <thead class="bg-light">
                                <tr>
                                    <th class="border-0">Reporte</th>
                                    <th class="border-0">Descripción</th>
                                    <th class="border-0">Formato</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td><strong>IPS</strong></td>
                                    <td>Formato requerido por el Instituto de Previsión Social.</td>
                                    <td><span class="badge badge-info">Excel</span></td>
                                </tr>
                                <tr>
                                    <td><strong>Empleados Obreros</strong></td>
                                    <td>Planilla oficial para el Ministerio de Trabajo (MTESS).</td>
                                    <td><span class="badge badge-info">Excel</span></td>
                                </tr>
                                <tr>
                                    <td><strong>Sueldos y Jornales</strong></td>
                                    <td>Resumen detallado de remuneraciones por período.</td>
                                    <td><span class="badge badge-info">Excel</span></td>
                                </tr>
                                <tr>
                                    <td><strong>Vacaciones</strong></td>
                                    <td>Registro de días gozados y remuneración de vacaciones.</td>
                                    <td><span class="badge badge-info">Excel</span></td>
                                </tr>
                                <tr>
                                    <td><strong>Resumen General</strong></td>
                                    <td>Consolidado de todos los datos del lote para control interno.</td>
                                    <td><span class="badge badge-info">Excel</span></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- RECIBOS SALARIALES -->
            <div class="card border-0 shadow-sm mb-4" style="border-radius: 12px; background-color: #f8fafc; border-left: 4px solid #10b981;">
                <div class="card-body p-4">
                    <h2 class="h4 text-success mb-3"><i class="fa fa-file-pdf-o mr-2"></i>5. Recibos Salariales (Especial)</h2>
                    <p>El sistema permite generar recibos oficiales con el formato legal vigente. Al imprimir, tiene dos opciones críticas:</p>
                    <div class="row mt-3">
                        <div class="col-md-6 mb-3">
                            <div class="p-3 bg-white rounded shadow-sm h-100">
                                <h4 class="h6 font-weight-bold text-dark"><i class="fa fa-file-pdf-o mr-2"></i>Archivo Único (PDF)</h4>
                                <p class="small text-muted">Genera un solo documento PDF que contiene todos los recibos, uno tras otro. Ideal para impresión masiva física.</p>
                            </div>
                        </div>
                        <div class="col-md-6 mb-3">
                            <div class="p-3 bg-white rounded shadow-sm h-100">
                                <h4 class="h6 font-weight-bold text-dark"><i class="fa fa-file-archive-o mr-2"></i>Archivo Comprimido (ZIP)</h4>
                                <p class="small text-muted">Genera un archivo ZIP con archivos PDF individuales para cada trabajador, nombrados como <code>CI_Periodo.pdf</code>. Ideal para envío digital.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- NOTAS FINALES -->
            <div class="alert alert-warning border-0 shadow-sm" style="border-radius: 12px;">
                <h4 class="h6 font-weight-bold"><i class="fa fa-exclamation-triangle mr-2"></i>Importante</h4>
                <p class="small mb-0">
                    Recuerde que el sistema utiliza la <strong>Cédula de Identidad (CI)</strong> como identificador único. 
                    Cualquier duplicidad en el mismo lote será bloqueada para evitar errores en los reportes consolidados.
                </p>
            </div>
        </div>
    </div>
</div>
        """

        if not manual:
            manual = self.create({
                'content': html_content
            })
        else:
            # Actualizamos el contenido si es el mensaje por defecto o si queremos forzar la actualización
            # Para asegurar que el usuario vea el manual completo, lo actualizamos.
            manual.write({'content': html_content})
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Manual de Uso',
            'res_model': 'antux.datahub.manual',
            'res_id': manual.id,
            'view_mode': 'form',
            'target': 'current',
        }
