/* ═══════════════════════════════════════════════════════════════════════════
   REPORTE MANTENIMIENTO — LENGUAJE M MEJORADO
   ═══════════════════════════════════════════════════════════════════════════

   Cambios clave respecto al original:
   • fnEstandarizarHora: maneja más edge cases (formato 24h, hhmmss, "n", "t")
   • fnLimpiarActividades: diccionario ampliado + limpieza de dobles espacios
   • Separación robusta de colaboradores (soporta ; , y mezclas)
   • Cálculo Minutos Interv. simplificado y sin duplicación
   • Equipo: extrae solo el código entre paréntesis, sin la marca
   • SKU: usa el Id del reporte (consistente entre exportaciones)
   • Tipado explícito para evitar errores de conversión
   • Eliminadas columnas redundantes y pasos innecesarios
   ======================================================================== */

let

    // ═══════════════════════════════════════════════════════════════════════
    // 1.  FUNCIONES AUXILIARES
    // ═══════════════════════════════════════════════════════════════════════

    // ── Estandariza cualquier formato de hora a tipo time ────────────────
    fnEstandarizarHora = (val as any) as nullable time =>
        if val = null or (try Text.Trim(Text.From(val)) otherwise "") = "" then null
        else if val is time then val
        else if val is datetime then DateTime.Time(val)
        else let
            texto = Text.Trim(Text.Lower(Text.From(val)), {" ", "."}),
            // Traducciones
            paso1 = Text.Replace(Text.Replace(Text.Replace(TextoBajo, 
                "cinco y media", "5:30 pm"), "diez de mañana", "10:00 am"), "mediodía", "12:00 pm"),
            // "3ppm" → "3pm", "o8" → "08"
            paso2 = Text.Replace(Text.Replace(paso1, "ppm", "pm"), "o", "0"),
            // Quitar puntos en am/pm → "a.m." → "am"
            paso3 = Text.Replace(Text.Replace(paso2, "a.m.", "am"), "p.m.", "pm"),
            paso4 = Text.Replace(Text.Replace(paso3, "a. m.", "am"), "p. m.", "pm"),
            // Quitar espacio antes de meridiano → "8: am" → "8:am"
            paso5 = Text.Replace(Text.Replace(paso4, " am", "am"), " pm", "pm"),
            paso6 = Text.Replace(Text.Replace(paso5, ": ", ":"), ". ", "."),
            // Separadores varios → ":"
            paso7 = Text.Replace(Text.Replace(Text.Replace(paso6, "y", ":"), ".", ":"), ";", ":"),
            // Si falta minuto → "2:pm" → "2:00pm"
            paso8 = Text.Replace(Text.Replace(paso7, ":am", ":00am"), ":pm", ":00pm"),
            // Espacio entre dígitos → "08 30pm" → "08:30pm"  (pero NO "08:30 pm")
            paso9 = Text.Replace(paso8, " ", ":"),
            // Si solo número → "8" → "8:00", "13" → "13:00"
            esNumero = List.AllTrue(List.Transform(Text.ToList(paso9), each Character.IsDigit(_))),
            paso10 = if esNumero then paso9 & ":00" else paso9,
            // Si tiene am/pm sin ":" → "3pm" → "3:00pm"
            tieneMeridiano = Text.Contains(paso10, "am") or Text.Contains(paso10, "pm"),
            tieneDosPuntos = Text.Contains(paso10, ":"),
            paso11 = if tieneMeridiano and not tieneDosPuntos then 
                        Text.Replace(Text.Replace(paso10, "am", ":00am"), "pm", ":00pm") 
                     else paso10,
            // Espacio antes de am/pm para Time.FromText
            conEspacio = Text.Replace(Text.Replace(paso11, "am", " am"), "pm", " pm"),
            final = Text.Trim(conEspacio),
            // Intentar formatos: "HH:MM am/pm", "HH:MM", "HH:MM:SS"
            resultado = try Time.FromText(final, "es-PE") 
                        otherwise try Time.FromText(final)
                        otherwise try Time.FromText(Text.Replace(final, " am", "")) 
                        otherwise try Time.FromText(Text.Replace(final, " pm", ""))
                        otherwise null
        in resultado,

    // ── Limpia y corrige ortografía de descripciones ─────────────────────
    fnLimpiarActividades = (val as any) as nullable text =>
        if val = null or Text.Trim(Text.From(val)) = "" then null
        else let
            limpio = Text.Clean(Text.Trim(Text.From(val))),
            // Quitar caracteres de checklist
            sinSimbolos = Text.Remove(limpio, {"-", "✓", "*", "●", ".", "•"}),
            sinEspaciosMultiples = Text.Trim(Text.Replace(sinSimbolos, "  ", " ")),
            // Diccionario de correcciones (minúscula → corregido)
            dict = {
                {"valbula", "válvula"}, {"balbula", "válvula"},
                {"valvulas", "válvulas"}, {"balbulas", "válvulas"},
                {"reparasion", "reparación"}, {"reparacion", "reparación"},
                {"reparasiones", "reparaciones"},
                {"manteimiento", "mantenimiento"}, {"mantenimento", "mantenimiento"},
                {"mantto", "mantenimiento"}, {"mant.", "mantenimiento"},
                {"limpiesa", "limpieza"}, {"limpia", "limpieza"},
                {"instalasion", "instalación"}, {"instalacion", "instalación"},
                {"instalaciones", "instalaciones"},
                {"inspeccion", "inspección"}, {"inspecion", "inspección"},
                {"inspecciones", "inspecciones"},
                {"electrico", "eléctrico"}, {"mecanico", "mecánico"},
                {"hidraulico", "hidráulico"}, {"hidroneumatico", "hidroneumático"},
                {"bateria", "batería"}, {"lubricacion", "lubricación"},
                {"lubricasion", "lubricación"}, {"lub", "lubricación"},
                {"sitema", "sistema"}, {"revision", "revisión"}, {"revisio", "revisión"},
                {"calibracion", "calibración"}, {"calibrasion", "calibración"},
                {"diagnostico", "diagnóstico"},
                {"prosedimiento", "procedimiento"},
                {"correccion", "corrección"}, {"correcion", "corrección"},
                {"soldadura", "soldadura"}, {"soldar", "soldadura"},
                {"cambio", "cambio"}, {"cambiar", "cambio"},
                {"verificar", "verificación"}, {"revisar", "revisión"},
                {"cortocircuito", "cortocircuito"}, {"corto circuito", "cortocircuito"},
            },
            // Aplicar correcciones (minúscula + mayúscula inicial)
            corregido = List.Accumulate(dict, sinEspaciosMultiples, (estado, par) =>
                let
                    minOrig = par{0},  minReemp = par{1},
                    mayOrig = Text.Proper(minOrig), mayReemp = Text.Proper(minReemp)
                in
                    Text.Replace(Text.Replace(estado, minOrig, minReemp), mayOrig, mayReemp)
            ),
            // Capitalizar primera letra de cada oración (split por punto)
            oraciones = Text.Split(corregido, "."),
            capitalizadas = List.Transform(oraciones, each 
                let t = Text.Trim(_)
                in if t <> "" and Text.Length(t) > 0 then Text.Upper(Text.At(t, 0)) & Text.Range(t, 1) else ""
            ),
            resultado = Text.Combine(capitalizadas, ". ")
        in Text.Trim(resultado),


    // ═══════════════════════════════════════════════════════════════════════
    // 2.  CARGA Y TRANSFORMACIONES
    // ═══════════════════════════════════════════════════════════════════════

    Origen = Excel.CurrentWorkbook(){[Name="ReportMantt"]}[Content],

    // ── Tipado inicial ────────────────────────────────────────────────────
    #"Tipo cambiado" = Table.TransformColumnTypes(Origen,{
        {"Id", Int64.Type}, {"Fecha", type date}, {"Turno de trabajo", type text},
        {"¿A que Grupo de Trabajo Perteneces?", type text},
        {"Colaboradores Eq. Trackless", type text},
        {"Colaboradores Eq. Convencional", type text},
        {"Colabores Eq. Electrico", type text},
        {"Tipo de Servicio", type text}, {"Descripcion de Servicio", type text},
        {"Tipo de Accion", type text},
        {"Describa todas las actividades realizadas", type text},
        {"Nivel donde se trabajo", type text},
        {"Labor o lugar donde realizaste el trabajo", type text},
        {"Hora Inicio Int.", type any}, {"Hora Termino Int.", type any},
        {"¿Cuánto tiempo demoraste en la actividad?", Int64.Type},
        {"Equipo Interv.", type text},
        {"Horometro Motor", type number}, {"Horómetro Eléctrico", type number},
        {"Horómetro de Percusión", type number}, {"Kilometraje", type number},
        {"Blanco", type any}
    }),

    // ── Dividir colaboradores por ";" o "," en columnas individuales ──────
    //    (soporta mezcla de delimitadores)
    #"Dividir Trackless" = Table.SplitColumn(#"Tipo cambiado", 
        "Colaboradores Eq. Trackless", 
        Splitter.SplitTextByAnyDelimiter({";", ","}, QuoteStyle.Csv),
        {"Tr.1", "Tr.2", "Tr.3", "Tr.4"}),
    #"Dividir Convencional" = Table.SplitColumn(#"Dividir Trackless", 
        "Colaboradores Eq. Convencional",
        Splitter.SplitTextByAnyDelimiter({";", ","}, QuoteStyle.Csv),
        {"Co.1", "Co.2", "Co.3", "Co.4"}),
    #"Dividir Electrico" = Table.SplitColumn(#"Dividir Convencional",
        "Colabores Eq. Electrico",
        Splitter.SplitTextByAnyDelimiter({";", ","}, QuoteStyle.Csv),
        {"El.1", "El.2", "El.3", "El.4"}),

    // ── Limpiar espacios y estandarizar nombres ───────────────────────────
    #"Limpiar nombres" = Table.TransformColumns(#"Dividir Electrico",
        List.Combine({{"Tr.1","Tr.2","Tr.3","Tr.4"}, {"Co.1","Co.2","Co.3","Co.4"}, {"El.1","El.2","El.3","El.4"}}),
        each try Text.Proper(Text.Trim(_)) otherwise null, type text
    ),

    // ── Consolidar trabajadores por orden (1 al 4) ────────────────────────
    //    Toma el primer nombre disponible en cada slot (Trackless → Conv → Elec)
    #"Trabajador N° 01" = Table.AddColumn(#"Limpiar nombres", "Trabajador N° 01",
        each [Tr.1] ?? [Co.1] ?? [El.1], type text),
    #"Trabajador N° 02" = Table.AddColumn(#"Trabajador N° 01", "Trabajador N° 02",
        each [Tr.2] ?? [Co.2] ?? [El.2], type text),
    #"Trabajador N° 03" = Table.AddColumn(#"Trabajador N° 02", "Trabajador N° 03",
        each [Tr.3] ?? [Co.3] ?? [El.3], type text),
    #"Trabajador N° 04" = Table.AddColumn(#"Trabajador N° 03", "Trabajador N° 04",
        each [Tr.4] ?? [Co.4] ?? [El.4], type text),

    // ── Eliminar columnas auxiliares de colaboradores ─────────────────────
    #"Quitar aux colab" = Table.RemoveColumns(#"Trabajador N° 04",
        {"Tr.1","Tr.2","Tr.3","Tr.4","Co.1","Co.2","Co.3","Co.4","El.1","El.2","El.3","El.4"}),

    // ── Extraer código de equipo (texto dentro del último "()") ───────────
    //    "Jumbo Komatsu ZJ21 (JM-01)" → "JM-01"
    #"Equipo Agregado" = Table.AddColumn(#"Quitar aux colab", "Equipo", each 
        let
            texto = Text.From([#"Equipo Interv."] otherwise ""),
            entre = try Text.BetweenDelimiters(texto, "(", ")")
        in
            if entre <> null and entre <> "" then Text.Trim(entre) else texto,
        type text
    ),

    // ── Estandarizar horas ────────────────────────────────────────────────
    #"Horas Estandarizadas" = Table.TransformColumns(#"Equipo Agregado", {
        {"Hora Inicio Int.", fnEstandarizarHora, type time},
        {"Hora Termino Int.", fnEstandarizarHora, type time}
    }),

    // ── Limpiar y corregir descripción de actividades ─────────────────────
    #"Actividades Limpias" = Table.TransformColumns(#"Horas Estandarizadas", {
        {"Describa todas las actividades realizadas", fnLimpiarActividades, type text}
    }),

    // ── Calcular Tiempo Hr (duración en horas) ───────────────────────────
    #"Tiempo Hr" = Table.AddColumn(#"Actividades Limpias", "Tiempo Hr", each
        let
            dur = [#"¿Cuánto tiempo demoraste en la actividad?"]
        in
            if dur <> null and dur > 0 then Number.Round(dur / 60, 2) else null,
        type number
    ),

    // ── Calcular Minutos Interv. con cruce de medianoche ──────────────────
    #"Minutos Interv." = Table.AddColumn(#"Tiempo Hr", "Minutos Interv.", each
        let
            inicio = [#"Hora Inicio Int."],
            termino = [#"Hora Termino Int."],
            turno = Text.Lower(Text.Trim(Text.From([#"Turno de trabajo"]))),
            esNoche = Text.Contains(turno, "noche") or turno = "n" or Text.StartsWith(turno, "n"),
            durDeclarada = [#"¿Cuánto tiempo demoraste en la actividad?"]
        in
            if inicio = null or termino = null then
                if durDeclarada <> null then durDeclarada else null
            else
                let
                    rawMin = Duration.TotalMinutes(termino - inicio),
                    ajustado = if rawMin < 0 then
                        if esNoche then (if rawMin < -720 then rawMin + 1440 else rawMin + 720)
                        else rawMin + 720
                    else rawMin
                in
                    Number.Round(if ajustado > 0 then ajustado else (durDeclarada ?? ajustado), 1),
        type number
    ),

    // ── SKU (basado en Id, consistente entre exportaciones) ──────────────
    #"SKU" = Table.AddColumn(#"Minutos Interv.", "SKU", each 
        "Rep-" & Text.PadStart(Text.From([Id]), 4, "0"),
        type text
    ),

    // ── Limpiar vacíos en trabajadores 02-04 ──────────────────────────────
    #"Trabajadores vacíos a null" = Table.ReplaceValue(#"SKU", "", null,
        Replacer.ReplaceValue, {"Trabajador N° 02", "Trabajador N° 03", "Trabajador N° 04"}),

    // ── Reordenar columnas finales ────────────────────────────────────────
    #"Columnas finales" = Table.ReorderColumns(#"Trabajadores vacíos a null", {
        "Id", "SKU", "Fecha",
        "Trabajador N° 01", "Trabajador N° 02", "Trabajador N° 03", "Trabajador N° 04",
        "¿A que Grupo de Trabajo Perteneces?", "Turno de trabajo",
        "Tipo de Servicio", "Descripcion de Servicio", "Tipo de Accion",
        "Describa todas las actividades realizadas",
        "Nivel donde se trabajo", "Labor o lugar donde realizaste el trabajo",
        "Hora Inicio Int.", "Hora Termino Int.", "Minutos Interv.",
        "Equipo Interv.", "Equipo",
        "Horometro Motor", "Horómetro Eléctrico", "Horómetro de Percusión",
        "Kilometraje", "Tiempo Hr"
    }),

    // ── Ordenar por SKU ascendente ────────────────────────────────────────
    #"Ordenado" = Table.Sort(#"Columnas finales", {{"SKU", Order.Ascending}})

in
    #"Ordenado"
