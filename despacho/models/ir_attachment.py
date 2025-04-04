from odoo import models, fields, api, _


class Attachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """
        Sobreescribe el método _search para filtrar adjuntos
        Añade res_field=False al dominio si no está presente
        """
        # Verificar si el dominio ya incluye res_field
        has_res_field = any(
            term[0] == 'res_field'
            for term in domain
            if isinstance(term, (list, tuple)) and len(term) > 1
        )

        # Añadir filtro por defecto si no existe
        if not has_res_field:
            domain = [('res_field', '=', False)] + domain

        # Ejecutar búsqueda original
        result = super()._search(
            domain=domain,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid
        )

        # Si es superusuario, retornar todos los resultados
        if self.env.is_superuser():
            return result

        # Filtrar resultados basados en permisos
        if not result:
            return 0 if count else []

        # Para conteo, retornar el número de registros
        if count:
            return len(result)

        # Retornar lista de IDs filtrados
        return result

    def _filter_access_rules(self, operation):
        """
        Filtra los adjuntos basado en reglas de acceso
        """
        # Superusuarios pueden ver todo
        if self.env.is_superuser():
            return self

        # Aplicar filtros de acceso estándar
        return super()._filter_access_rules(operation)

    def check(self, mode, raise_exception=True):
        """
        Verifica permisos de acceso para los adjuntos
        """
        # Superusuarios tienen acceso completo
        if self.env.is_superuser():
            return True

        # Verificación estándar de permisos
        return super().check(mode, raise_exception=raise_exception)