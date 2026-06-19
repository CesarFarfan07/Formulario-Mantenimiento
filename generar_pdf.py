# -*- coding: utf-8 -*-
"""Genera PDF explicativo del Formulario de Reporte Diario de Mantenimiento."""

import os
from fpdf import FPDF

OUTPUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "static",
    "Manual_Formulario_Mantenimiento.pdf",
)
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

pdf = FPDF(orientation="P", unit="mm", format="A4")
pdf.add_font("Cal", "", os.path.join(os.path.dirname(__file__), "backend", "app", "templates", "calibri.ttf"))
pdf.add_font("Cal", "B", os.path.join(os.path.dirname(__file__), "backend", "app", "templates", "calibrib.ttf"))

FONT = "Cal"


def title_page():
    pdf.add_page()
    pdf.ln(50)
    pdf.set_font(FONT, "B", 28)
    pdf.cell(0, 15, "Formulario de Reporte", align="C")
    pdf.ln(14)
    pdf.cell(0, 15, "Diario de Mantenimiento", align="C")
    pdf.ln(20)
    pdf.set_font(FONT, "", 14)
    pdf.cell(0, 8, "Unidad Minera Soledad", align="C")
    pdf.ln(8)
    pdf.cell(0, 8, "Inversiones Prosol Ispacas S.A.", align="C")
    pdf.ln(25)
    pdf.set_font(FONT, "", 11)
    pdf.cell(0, 6, "Sistema web para el registro, control y generacion", align="C")
    pdf.ln(6)
    pdf.cell(0, 6, "de reportes diarios de mantenimiento", align="C")
    pdf.ln(30)
    pdf.set_font(FONT, "", 9)
    pdf.cell(0, 5, "Documento version 1.0 - Junio 2026", align="C")


def section(title):
    pdf.set_font(FONT, "B", 16)
    pdf.cell(0, 10, title, align="L")
    pdf.ln(12)


def subsection(title):
    pdf.set_font(FONT, "B", 12)
    pdf.cell(0, 8, title, align="L")
    pdf.ln(9)


def body(text):
    pdf.set_font(FONT, "", 10)
    pdf.multi_cell(0, 5.5, text)
    pdf.ln(3)


def bullet(text, indent=10):
    x = pdf.get_x()
    pdf.set_x(x + indent)
    pdf.set_font(FONT, "", 10)
    pdf.cell(5, 5.5, chr(8226))
    pdf.multi_cell(0, 5.5, text)
    pdf.ln(1)


def bullet_bold(label, desc, indent=10):
    x = pdf.get_x()
    pdf.set_x(x + indent)
    pdf.cell(5, 5.5, chr(8226))
    pdf.set_font(FONT, "B", 10)
    pdf.write(5.5, label + ": ")
    pdf.set_font(FONT, "", 10)
    pdf.multi_cell(0, 5.5, desc)
    pdf.ln(1)


# ================================================================
# CONTENT
# ================================================================
title_page()

# Page 2 - Que es
pdf.add_page()
section("1.  Que es este sistema?")
body(
    "Es una aplicacion web que permite a los trabajadores de mantenimiento "
    "registrar las tareas que realizan cada dia en la mina. "
    "Imagina que es como un cuaderno digital donde, en lugar de escribir "
    "a mano en papeles que se pueden perder o arrugar, escribes en una "
    "computadora o en un celular y todo queda guardado ordenadamente."
)
body(
    "Al final del dia, el sistema puede generar automaticamente el reporte "
    "diario en Excel, exactamente con el mismo formato que la empresa usa, "
    "listo para enviar a los jefes y supervisores."
)

# Page 3 - Para que sirve
pdf.add_page()
section("2.  Para que sirve?")
body("Este sistema ayuda a:")
bullet("Registrar todos los trabajos que se hacen en el area de mantenimiento.")
bullet("Saber quien hizo cada trabajo y con que colaboradores.")
bullet("Llevar el control de horometros (horas de uso) y kilometraje de los equipos.")
bullet("Subir fotos de los trabajos realizados como evidencia.")
bullet("Generar el reporte diario en Excel con el formato oficial de la empresa.")
bullet("Tener toda la informacion ordenada y disponible para consultar en cualquier momento.")

# Page 4 - Como funciona
pdf.add_page()
section("3.  Como funciona? (Paso a paso)")

subsection("Paso 1: Ingresar al sistema")
body(
    "El trabajador abre la pagina web en su computadora o celular. "
    "Ve un formulario simple con espacios para llenar."
)

subsection("Paso 2: Datos generales")
body(
    "Primero escribe su nombre, correo, la fecha, el turno (Dia o Noche) "
    "y a que grupo de equipos pertenece el trabajo (Trackless, Convencional "
    "o Electrico)."
)

subsection("Paso 3: Registrar los trabajos")
body(
    "Luego agrega uno o varios trabajos realizados. Para cada trabajo indica:"
)
bullet("Que macroproceso se hizo (Mecanico, Electrico, Soldadura, etc.)")
bullet("Que tipo de trabajo fue (Cambio de aceite,Reparacion, etc.)")
bullet("Que accion se realizo (Preventivo, Correctivo, etc.)")
bullet("Una descripcion detallada de las actividades")
bullet("En que nivel y lugar se trabajo")
bullet("El equipo que se intervino")
bullet("Las horas de inicio y fin (si aplica)")
bullet("Las lecturas de horometro o kilometraje del equipo")
bullet("Que colaboradores participaron")
bullet("Fotos del trabajo realizado")

subsection("Paso 4: Guardar el reporte")
body(
    "Al hacer clic en Guardar, toda la informacion se almacena en la base "
    "de datos. Nunca se pierde aunque se cierre la pagina."
)

subsection("Paso 5: Generar el reporte diario")
body(
    "Un supervisor o administrador puede generar el reporte diario en Excel "
    "con solo hacer clic en un boton. El sistema lo crea exactamente con el "
    "formato que la empresa ya usa, incluyendo los logos, colores y las firmas."
)

subsection("Paso 6: Descargar o consultar")
body(
    "Los reportes generados quedan disponibles para descargar en cualquier "
    "momento. Tambien se pueden consultar los reportes anteriores."
)

# Page 5 - Pantallas principales
pdf.add_page()
section("4.  Que pantallas tiene?")

subsection("A) Formulario de registro (pagina principal)")
body(
    "Es la pantalla que ven los trabajadores. Tiene un formulario bonito "
    "con colores y diseno moderno. Se puede usar tanto en computadora como "
    "en celular o tablet. Ahi se registran todos los trabajos del dia."
)

subsection("B) Panel de administracion")
body(
    "Es la pantalla para los jefes y supervisores. Permite configurar todo "
    "el sistema sin necesidad de programar:"
)
bullet("Agregar, editar o quitar grupos de equipos")
bullet("Agregar, editar o quitar macroprocesos")
bullet("Agregar, editar o quitar tipos de trabajo")
bullet("Agregar, editar o quitar acciones")
bullet("Agregar, editar o quitar colaboradores")
bullet("Agregar, editar o quitar equipos con sus horometros")
bullet("Reordenar cualquier lista con flechas (subir o bajar)")
body(
    "Todos los cambios que se hacen en el administrador se ven reflejados "
    "al instante en el formulario de registro, sin necesidad de reiniciar "
    "nada."
)

subsection("C) Busqueda y listado de reportes")
body(
    "Permite buscar reportes anteriores por fecha y ver los detalles. "
    "Tiene un boton Ver mas para cargar mas resultados sin que la pagina "
    "se ponga lenta."
)

subsection("D) Descarga de Excel")
body(
    "Desde esta seccion se puede descargar la informacion en formato Excel "
    "para analizarla o compartirla. Tambien se genera el reporte diario "
    "con el formato exacto de la empresa."
)

# Page 6 - Beneficios
pdf.add_page()
section("5.  Por que usar este sistema?")

bullet_bold("Adios al papel",
    "No mas formatos impresos que se pierden, se mojan o se arrugan. "
    "Todo queda digital y seguro.")
bullet_bold("Ahorro de tiempo",
    "El reporte diario se genera automaticamente en segundos. "
    "Antes alguien tenia que armarlo a mano.")
bullet_bold("Sin errores",
    "El sistema valida que los datos esten correctos antes de guardarlos. "
    "Por ejemplo, no permite poner un horometro menor al anterior.")
bullet_bold("Informacion ordenada",
    "Todos los trabajos quedan organizados por fecha, turno y grupo. "
    "Se puede buscar cualquier reporte del pasado rapidamente.")
bullet_bold("Fotos como evidencia",
    "Cada trabajo puede llevar fotos que quedan guardadas y organizadas "
    "por fecha.")
bullet_bold("Funciona en cualquier dispositivo",
    "Se puede usar desde una computadora, un celular o una tablet. "
    "Solo se necesita internet y un navegador.")
bullet_bold("Personalizable",
    "Los administradores pueden cambiar la configuracion cuando quieran. "
    "Agregar nuevos equipos, trabajos o colaboradores es muy facil.")
bullet_bold("Reporte con formato oficial",
    "El Excel que genera el sistema es identico al que la empresa ya "
    "usa, con logos, colores y diseno exactos.")

# Page 7 - Estructura tecnica (simple)
pdf.add_page()
section("6.  Como esta construido?")
body(
    "Aunque no necesitas saber esto para usarlo, es bueno que sepas que:"
)
bullet(
    "El sistema funciona en un servidor web al que puedes acceder "
    "con cualquier navegador (Chrome, Edge, Safari)."
)
bullet(
    "Usa una base de datos que guarda toda la informacion de forma "
    "segura y organizada."
)
bullet(
    "La pantalla que ves esta disenada con tecnologia moderna que "
    "se ve bien en cualquier dispositivo."
)
bullet(
    "No necesita instalacion. Solo abres la pagina y listo."
)
bullet(
    "Los archivos Excel y fotos se generan y guardan automaticamente "
    "en el servidor."
)

pdf.ln(10)
pdf.set_font(FONT, "B", 10)
pdf.cell(0, 6, "Para mas informacion o soporte, contactar al area de sistemas.", align="C")

pdf.output(OUTPUT)
print(f"PDF generado: {OUTPUT}")
