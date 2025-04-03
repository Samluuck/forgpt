from odoo import models, fields, api, _


class Attachment(models.Model):

    _inherit = "ir.attachment"

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        # add res_field=False in domain if not present; the arg[0] trick below
        # works for domain items and '&'/'|'/'!' operators too
        if not any(arg[0] in ('id', 'res_field') for arg in args):
            args.insert(0, ('res_field', '=', False))

        ids = super(models.Model, self)._search(args, offset=offset, limit=limit, order=order,
                                                count=False, access_rights_uid=access_rights_uid)

        if self.env.is_superuser():
            # rules do not apply for the superuser
            return len(ids) if count else ids

        if not ids:
            return 0 if count else []

        # Work with a set, as list.remove() is prohibitive for large lists of documents
        # (takes 20+ seconds on a db with 100k docs during search_count()!)
        orig_ids = ids
        ids = set(ids)

        result = [id for id in orig_ids if id in ids]

        return len(result) if count else list(result)

