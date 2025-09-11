{
    "name": "Regier - OCR de Facturas Proveedor (Tesseract)",
    "summary": "Crear facturas de proveedor desde PDF/PNG/JPG usando OCR local (Tesseract).",
    "version": "15.0.1.0.0",
    "author": "Regier",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "wizard/invoice_ocr_wizard.xml",
        "security/ir.model.access.csv",
    ],
    "application": False,
    "installable": True,
    "assets": {},
    "external_dependencies": {
        "python": ["pytesseract", "PIL", "dateutil"],
        "bin": ["pdftoppm", "tesseract"]
    },
}
