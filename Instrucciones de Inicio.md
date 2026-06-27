**Cuando realices cambios en el sistema: Primero de manera local y luego subirlo al render**

Comandos para ejecutar en CMD o PowerShell

**Cuando solo cambias configuración (admin)**

    cd "C:\\Users\\admin\\OneDrive\\TRABAJO\\08 U.M. Soledad\\15 Automatizaciones\\01 Codigo\\03 Formulario"
    python backend\export_config.py
    git add -A
    git commit -m "update config"
    git push

**Cuando cambias código + configuración**

    cd "C:\\Users\\admin\\OneDrive\\TRABAJO\\08 U.M. Soledad\\15 Automatizaciones\\01 Codigo\\03 Formulario"
    python backend\export_config.py && git add -A && git commit -m "update" && git push

