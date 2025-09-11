# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64, subprocess, tempfile, os, re, json
from datetime import datetime
from dateutil.parser import parse as dtparse
import requests
import logging
_logger = logging.getLogger(__name__)

try:
    import pytesseract
except Exception:
    pytesseract = None

from PIL import Image, ImageFilter, ImageOps, ImageEnhance


class InvoiceOCRWizard(models.TransientModel):
    _name = "invoice.ocr.wizard"
    _description = "OCR de Facturas (Tesseract)"

    input_file = fields.Binary(string="PDF o Imagen", required=True)
    filename = fields.Char()
    avg_confidence = fields.Float(string="Confianza OCR (%)", readonly=True)
    ocr_text = fields.Text(readonly=True)
    result_json = fields.Text(readonly=True)
    preview_html = fields.Html(readonly=True, sanitize=False)
    move_id = fields.Many2one("account.move", string="Borrador creado", readonly=True)

    # ====== Helpers de dependencias y tipos ======
    def _ensure_deps(self):
        if pytesseract is None:
            raise UserError(_("Falta el paquete Python 'pytesseract'. Instálalo en tu entorno de Odoo."))
        for exe in ("pdftoppm", "tesseract"):
            if subprocess.call(["which", exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
                raise UserError(_("%s no está instalado. Instala 'poppler-utils' y 'tesseract-ocr'." % exe))

    @staticmethod
    def _is_pdf(path: str) -> bool:
        return (os.path.splitext(path)[1] or "").lower() == ".pdf"

    # ====== PDF → PNGs ======
    def _pdf_to_pngs(self, pdf_path, dpi=350):
        out_prefix = os.path.join(tempfile.gettempdir(), f"ocr_{self.env.uid}_{int(datetime.now().timestamp())}")
        cmd = ["pdftoppm", "-r", str(dpi), "-png", pdf_path, out_prefix]
        subprocess.check_call(cmd)
        folder = os.path.dirname(out_prefix)
        base = os.path.basename(out_prefix)
        imgs = sorted([os.path.join(folder, f) for f in os.listdir(folder) if f.startswith(base) and f.endswith(".png")])
        if not imgs:
            raise UserError(_("No se generaron imágenes desde el PDF."))
        return imgs

    # ====== Pre-proceso de imagen ======
    @staticmethod
    def _preprocess_pil(img: Image.Image) -> Image.Image:
        w, h = img.size
        if max(w, h) < 1500:
            ratio = 1500 / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        img = img.convert("L")  # escala de grises
        img = ImageEnhance.Contrast(img).enhance(1.6)
        img = ImageEnhance.Brightness(img).enhance(1.05)
        img = ImageOps.autocontrast(img)
        img = img.filter(ImageFilter.MedianFilter(size=3))
        # umbral simple
        img = img.point(lambda x: 255 if x > 190 else 0, mode="1")
        return img.convert("L")

    @staticmethod
    def _save_temp_image(pil_img: Image.Image) -> str:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        pil_img.save(tmp.name, format="PNG", optimize=True)
        return tmp.name

    def _pngs_from_input(self, tmp_path):
        if self._is_pdf(tmp_path):
            return self._pdf_to_pngs(tmp_path, dpi=350)
        # imagen suelta
        with Image.open(tmp_path) as im:
            im = self._preprocess_pil(im)
            return [self._save_temp_image(im)]

    # ====== OCR con fallback y confianza ======
    def _ocr_with_fallback(self, img_path) -> (str, float):
        """Devuelve (texto, confianza_promedio)."""
        lang = "spa+eng"
        psms = ["6", "4", "11"]  # normal, columnas, texto disperso
        best_text, best_conf = "", -1.0

        for psm in psms:
            cfg = f"--oem 1 --psm {psm}"
            # medir confianza con image_to_data
            data = pytesseract.image_to_data(Image.open(img_path), lang=lang, config=cfg, output_type='dict')
            confs = [int(c) for c in data.get("conf", []) if c not in ("-1", -1)]
            avg_conf = sum(confs) / len(confs) if confs else 0.0
            # obtener texto con el mismo cfg
            text = pytesseract.image_to_string(Image.open(img_path), lang=lang, config=cfg)
            if avg_conf > best_conf:
                best_conf, best_text = avg_conf, text
            if avg_conf >= 70:  # umbral razonable para no seguir probando
                break
        return best_text, best_conf

    def _run_ocr(self, img_paths):
        texts, confs = [], []
        for p in img_paths:
            t, c = self._ocr_with_fallback(p)
            texts.append(t)
            confs.append(c)
        return "\n".join(texts), (sum(confs) / len(confs) if confs else 0.0)

    # ====== Regex de extracción (ajustables) ======
    _RUC = re.compile(r"\bRUC[:\s]*([0-9\.\-]+)", re.IGNORECASE)
    _TIMBRADO = re.compile(r"\bTimbrad[oa][: \t]*([0-9]{6,10})", re.IGNORECASE)
    _NUMERO = re.compile(r"\b(?:N[°º]|Nro\.?|Factura)[:\s\-]*([0-9][0-9\.\-]{5,})", re.IGNORECASE)
    _FECHA = re.compile(r"\b(?:Fecha|Emisi[oó]n)[:\s]*([0-3]?\d[\/\-\.][0-1]?\d[\/\-\.](?:\d{2}|\d{4}))", re.IGNORECASE)
    _TOTAL_APAGAR = re.compile(r"Total\s*a\s*pagar.*?([\d\.\,]+)", re.IGNORECASE)
    _TOTAL_GENERIC = re.compile(r"\bTotal\b[^\n\r]*?([\d\.\,]+)", re.IGNORECASE)
    _IVA10 = re.compile(r"\bIVA\s*10%[:\s]*([\d\.\,]+)", re.IGNORECASE)  # monto del impuesto
    _IVA5  = re.compile(r"\bIVA\s*5%[:\s]*([\d\.\,]+)", re.IGNORECASE)   # monto del impuesto

    @staticmethod
    def _to_float(s):
        try:
            return float(s.replace(".", "").replace(",", "."))
        except Exception:
            return 0.0

    @staticmethod
    def _clean_vat(v):
        return (v or "").replace(".", "").replace("-", "").replace(" ", "")

    def _parse_text(self, text):
        data = {}

        m = self._RUC.search(text);      data["ruc"] = self._clean_vat(m.group(1)) if m else ""
        m = self._TIMBRADO.search(text); data["timbrado"] = m.group(1) if m else ""
        m = self._NUMERO.search(text);   data["numero"] = m.group(1) if m else ""
        m = self._FECHA.search(text);    data["fecha"] = m.group(1) if m else ""

        # Total a pagar (preferencia)
        m = self._TOTAL_APAGAR.search(text)
        if m:
            data["total"] = self._to_float(m.group(1))
        else:
            # Buscar un "Total" genérico (cuidado con IVAs totales intermedios)
            m2 = self._TOTAL_GENERIC.findall(text)
            if m2:
                # usa el último número capturado tras "Total" (suele ser el total final)
                data["total"] = self._to_float(m2[-1])
            else:
                data["total"] = 0.0

        m = self._IVA10.search(text);    data["iva10"] = self._to_float(m.group(1)) if m else 0.0
        m = self._IVA5.search(text);     data["iva5"]  = self._to_float(m.group(1)) if m else 0.0

        # Normalizar fecha a ISO
        if data.get("fecha"):
            try:
                data["fecha_iso"] = dtparse(data["fecha"], dayfirst=True).date().isoformat()
            except Exception:
                data["fecha_iso"] = fields.Date.context_today(self)
        else:
            data["fecha_iso"] = fields.Date.context_today(self)

        return data

    # ====== Búsquedas auxiliares ======
    def _find_partner(self, vat_clean):
        if not vat_clean:
            return self.env["res.partner"]
        return self.env["res.partner"].search([("vat", "=", vat_clean)], limit=1)

    def _default_purchase_journal(self):
        return self.env["account.journal"].search([("type", "=", "purchase")], limit=1)

    # ====== Acción principal ======
    def action_process(self):
        self._ensure_deps()
        if not self.input_file:
            raise UserError(_("Necesitas adjuntar un archivo."))

        # Guardar temporal
        suffix = os.path.splitext(self.filename or "scan.pdf")[1] or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(base64.b64decode(self.input_file))
            tmp_path = f.name

        # Unificar a lista de PNGs
        imgs = self._pngs_from_input(tmp_path)

        # OCR
        text, avg_conf = self._run_ocr(imgs)
        data = self._parse_text(text)

        # Búsqueda de proveedor por RUC
        partner = self._find_partner(data.get("ruc"))

        # Diario de compras
        journal = self._default_purchase_journal()
        if not journal:
            raise UserError(_("No hay un Diario de Compras configurado."))

        # Impuestos (compra) a 10% y 5%
        iva10_tax = self.env["account.tax"].search([("type_tax_use", "=", "purchase"), ("amount", "=", 10)], limit=1)
        iva5_tax  = self.env["account.tax"].search([("type_tax_use", "=", "purchase"), ("amount", "=", 5)], limit=1)

        # Si el OCR capturó IVA10/IVA5 como IMPORTE DE IMPUESTO:
        base10 = round(data["iva10"] / 0.10, 2) if data["iva10"] else 0.0
        base5  = round(data["iva5"]  / 0.05,  2) if data["iva5"]  else 0.0

        # Exentas = Total - (base10 + IVA10 + base5 + IVA5)
        exentas = 0.0
        if data.get("total"):
            exentas = data["total"] - (base10 + data["iva10"] + base5 + data["iva5"])
            if exentas < 0:
                exentas = 0.0
            exentas = round(exentas, 2)

        lines = []

        def add_line(desc, base, tax):
            if base and base > 0.0:
                lines.append((0, 0, {
                    "name": desc,
                    "quantity": 1.0,
                    "price_unit": base,
                    "tax_ids": [(6, 0, [tax.id])] if tax else False,
                }))

        add_line("Base IVA 10%", base10, iva10_tax if iva10_tax else False)
        add_line("Base IVA 5%",  base5,  iva5_tax  if iva5_tax  else False)
        if exentas > 0:
            add_line("Exentas", exentas, False)

        if not lines:
            # Si no hay información suficiente, crear una línea única con el total como monto bruto
            lines = [(0, 0, {"name": "Factura OCR", "quantity": 1.0, "price_unit": data.get("total", 0.0) or 0.0})]

        move_vals = {
            "move_type": "in_invoice",
            "invoice_date": fields.Date.context_today(self),  # por ahora manual
            "partner_id": partner.id or False,
            "journal_id": journal.id,
            "invoice_line_ids": lines,
            "invoice_origin": f"OCR-Azure {data.get('numero') or (self.filename or '')}",
            "ref": data.get("numero", ""),
            "currency_id": self.env.company.currency_id.id,
            "suc": data.get("suc"),
            "sec": data.get("sec"),
            "nro": data.get("nro"),
            "tipo_comprobante": tipo_doc.id if tipo_doc else False,
        }

        move = self.env["account.move"].create(move_vals)

        # Vista previa / diagnóstico
        conf_hint = f"Confianza OCR: {avg_conf:.1f}%"

        # Normalizar fecha a string por si llega como date
        fecha_iso = data.get("fecha_iso")
        try:
            from datetime import date, datetime
            if isinstance(fecha_iso, (date, datetime)):
                fecha_iso = fecha_iso.isoformat()
        except Exception:
            pass

        preview = {
            "ruc": data.get("ruc"),
            "timbrado": data.get("timbrado"),
            "numero": data.get("numero"),
            "fecha": fecha_iso,
            "iva10_imp": data.get("iva10"),
            "iva5_imp": data.get("iva5"),
            "base10_calc": base10,
            "base5_calc": base5,
            "exentas_calc": exentas,
            "total_ocr": data.get("total"),
            "partner_id": partner.id if partner else None,
            "journal_id": journal.id if journal else None,
        }

        self.write({
            "avg_confidence": avg_conf,
            "ocr_text": f"{conf_hint}\n\n{text}",
            "result_json": json.dumps(preview, ensure_ascii=False, indent=2, default=str),
            "preview_html": f"<b>{conf_hint}</b><pre>{json.dumps(preview, ensure_ascii=False, indent=2, default=str)}</pre>",
            "move_id": move.id,
        })

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    # Botón para abrir la factura creada
    def action_open_move(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_("Aún no se generó una factura."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "target": "current",
        }
    
    ##### OCR VIA AZURE #####

    def action_process_azure(self):
        """Procesar PDF/Imagen con Azure Form Recognizer (prebuilt-invoice + regex PY)."""
        if not self.input_file:
            raise UserError(_("Necesitas adjuntar un archivo."))

        endpoint = self.env['ir.config_parameter'].sudo().get_param("azure_form_endpoint")
        key = self.env['ir.config_parameter'].sudo().get_param("azure_form_key")
        if not endpoint or not key:
            raise UserError(_("Configura 'azure_form_endpoint' y 'azure_form_key' en Parámetros del sistema."))

        # Guardar archivo temporal
        suffix = os.path.splitext(self.filename or "scan.pdf")[1] or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(base64.b64decode(self.input_file))
            tmp_path = f.name

        # Enviar a Azure (inicia el análisis)
        model_id = self.env['ir.config_parameter'].sudo().get_param("azure_form_model_id", "prebuilt-invoice")
        url = f"{endpoint}formrecognizer/documentModels/{model_id}:analyze?api-version=2023-07-31"

        ext = suffix.lower()
        ctype = "application/pdf" if ext == ".pdf" else ("image/jpeg" if ext in (".jpg", ".jpeg") else "image/png")

        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": ctype,
        }
        with open(tmp_path, "rb") as f:
            response = requests.post(url, headers=headers, data=f)

        if response.status_code not in (200, 202):
            raise UserError(_("Error Azure (POST): %s - %s") % (response.status_code, response.text[:500]))

        # Polling: consultar hasta que termine el análisis
        operation_url = response.headers.get("Operation-Location")
        if not operation_url:
            raise UserError(_("Azure no devolvió Operation-Location."))

        import time
        result = {}
        for _ in range(10):  # 10 intentos máx
            poll = requests.get(operation_url, headers={"Ocp-Apim-Subscription-Key": key})
            if poll.status_code != 200:
                raise UserError(_("Error Azure (GET): %s - %s") % (poll.status_code, poll.text[:500]))
            result = poll.json()
            status = result.get("status")
            if status in ("succeeded", "failed"):
                break
            time.sleep(1)

        if result.get("status") != "succeeded":
            raise UserError(_("Azure no pudo procesar el documento: %s") % result)

        # ========= PARTE 1: Datos de Azure (modelo custom entrenado) =========
        data = {}
        documents = result.get("analyzeResult", {}).get("documents", [])
        doc_fields = documents[0].get("fields", {}) if documents else {}

        data["numero"] = doc_fields.get("NumeroFactura", {}).get("value", "")
        data["ruc"] = doc_fields.get("RUCProveedor", {}).get("value", "")
        data["total"] = doc_fields.get("Total", {}).get("value", 0.0)
        data["timbrado"] = doc_fields.get("Timbrado", {}).get("value", "")

        # separar suc, sec, nro
        if data["numero"] and "-" in data["numero"]:
            parts = data["numero"].split("-")
            if len(parts) == 3:
                data["suc"], data["sec"], data["nro"] = parts


        # ========= PARTE 2: Texto plano con regex paraguayo =========
        try:
            import fitz  # PyMuPDF (mejor que OCR para PDFs nativos)
            text = ""
            with fitz.open(tmp_path) as doc:
                for page in doc:
                    text += page.get_text()
        except Exception:
            # fallback simple si no está PyMuPDF
            text = ""
            try:
                from pdf2image import convert_from_path
                pages = convert_from_path(tmp_path, dpi=300)
                for im in pages:
                    text += pytesseract.image_to_string(im, lang="spa")
            except Exception:
                pass

        # Regex Paraguay
        RUC = re.search(r"RUC[:\s]*([0-9\-]+)", text, re.IGNORECASE)
        TIMBRADO = re.search(r"Timbrad[oa][: \t]*([0-9]{6,10})", text, re.IGNORECASE)
        NUMERO = re.search(r"\d{3}-\d{3}-\d{7}", text)

        if RUC:
            data["ruc"] = RUC.group(1)
        if TIMBRADO:
            data["timbrado"] = TIMBRADO.group(1)
        if NUMERO and not data.get("numero"):
            data["numero"] = NUMERO.group(0)

        # ========= PARTE 3: Crear factura =========
        partner = self.env["res.partner"]
        if data.get("ruc"):
            partner = self.env["res.partner"].search([("vat", "=", data["ruc"].replace("-", ""))], limit=1)

        journal = self.env["account.journal"].search([("type", "=", "purchase")], limit=1)
        if not journal:
            raise UserError(_("No hay Diario de Compras configurado."))
        
        # Tipo de comprobante (factura)
        tipo_doc = self.env["ruc.tipo.documento"].search([("codigo_hechauka", "=", "1")], limit=1)

        # Cuenta de gasto por defecto (fallback cuando no hay product_id)
        expense_account = self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('user_type_id.type', '=', 'expense'),
        ], limit=1)
        if not expense_account:
            raise UserError(_("No se encontró una cuenta de gasto en la compañía. Configure una cuenta de gasto."))

        # Helper: buscar producto por código o nombre
        def _match_product(desc):
            Product = self.env['product.product']
            # 1) Intento por código interno entre corchetes: [COD]
            m = re.search(r"\[([A-Za-z0-9\-\._]+)\]", desc or "")
            if m:
                p = Product.search([('default_code', '=', m.group(1))], limit=1)
                if p:
                    return p
            # 2) Intento por default_code directo (palabras tipo IA271, FURN_123, etc.)
            tokens = re.findall(r"[A-Za-z0-9\-\._]{3,}", desc or "")
            if tokens:
                p = Product.search([('default_code', 'in', tokens)], limit=1)
                if p:
                    return p
            # 3) Intento por nombre aproximado
            if desc:
                p = Product.search([('name', 'ilike', desc[:60])], limit=1)
                if p:
                    return p
            return self.env['product.product']


        lines = []
        line_items = doc_fields.get("LineItems", {}).get("valueArray", [])

        for item in line_items:
            val = item.get("valueObject", {})
            desc = (val.get("Descripcion", {}) or {}).get("value", "") or "Línea Azure"
            qty = (val.get("Cantidad", {}) or {}).get("value", 1.0) or 1.0
            price_unit = (val.get("PrecioUnitario", {}) or {}).get("value", 0.0) or 0.0

            product = _match_product(desc)

            if product:
                # Con product_id: Odoo toma cuentas/impuestos del producto/categoría
                lines.append((0, 0, {
                    "name": desc,
                    "product_id": product.id,
                    "quantity": qty,
                    "price_unit": price_unit,
                }))
            else:
                # Sin product_id: solo name + cuenta de gasto para evitar error contable
                lines.append((0, 0, {
                    "name": desc,
                    "quantity": qty,
                    "price_unit": price_unit,
                    "account_id": expense_account.id,
                }))

        # Si no vino nada desde Azure, línea fallback con cuenta de gasto
        if not lines:
            lines = [(0, 0, {
                "name": "Factura Azure",
                "quantity": 1.0,
                "price_unit": data.get("total", 0.0) or 0.0,
                "account_id": expense_account.id,
            })]

        move_vals = {
            "move_type": "in_invoice",
            "invoice_date": fields.Date.context_today(self),  # por ahora manual
            "partner_id": partner.id or False,
            "journal_id": journal.id,
            "invoice_line_ids": lines,
            "invoice_origin": f"OCR-Azure {data.get('numero') or (self.filename or '')}",
            "ref": data.get("numero", ""),
            "currency_id": self.env.company.currency_id.id,
            "suc": data.get("suc"),
            "sec": data.get("sec"),
            "nro": data.get("nro"),
            "tipo_comprobante": tipo_doc.id if tipo_doc else False,
        }

        move = self.env["account.move"].create(move_vals)

        # Guardar en wizard
        self.write({
            "ocr_text": text[:5000],
            "result_json": json.dumps(data, ensure_ascii=False, indent=2),
            "preview_html": f"<pre>{json.dumps(data, ensure_ascii=False, indent=2)}</pre>",
            "move_id": move.id,
        })

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }
