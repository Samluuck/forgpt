def migrate(cr, version):
    print("migrando:" + version)

    cr.execute("""update despacho_despacho
set (desconsolidacion,
     manifiesto,
     barcaza,
     cnu, acuerdo, fob, flete, seguro, ajuste, descuento, cif, moneda, tc,
     incoterms) = (dd.desconsolidacion, dd.manifiesto, dd.barcaza, dd.cnu, dd.acuerdo, dd.fob, dd.flete, dd.seguro,
                   dd.ajuste, dd.descuento, dd.cif, dd.moneda, dd.tc, dd.incoterms)
from despachos_datos as dd
where dd.despacho = despachos_despacho.id;""")
    cr.execute("""update despachos_documento
set despacho = datos.despacho
from despachos_datos as datos
where datos = datos.id;""")

    cr.execute("""update despachos_documento_previo
set despacho = previo.despacho
from despachos_previo as previo
where previo = previo.id;""")

    cr.execute("""update despachos_documento_previo_con_monto
set despacho = previo.despacho
from despachos_previo as previo
where previo = previo.id;""")

    cr.execute("""update despachos_documento_oficializacion
set despacho = of.despacho
from despachos_oficializacion as of
where of.id = oficializacion;""")

    cr.execute("""update despachos_despacho
set (oficial, canal, firmado, aduanero, definitivo) = (of.oficial, of.canal, of.firmado, of.aduanero, of.definitivo)
from despachos_oficializacion as of
where of.despacho = despachos_despacho.id;""")

    cr.execute("""update ir_attachment
set (res_model, res_id) = ('despacho.despacho', of.despacho)
from despachos_oficializacion as of
where res_model like 'despacho.oficializacion'
  and of.id = res_id;""")

    cr.execute(
        """update despachos_despacho set state = 'presupuestado' from despachos_presupuesto dp where despachos_despacho.id = dp.despacho;""")

    cr.execute("""update despachos_despacho set state = 'oficializado' where oficial is not null;""")
