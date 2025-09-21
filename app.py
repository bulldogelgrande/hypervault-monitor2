"""
Microservicio Flask para exponer la capacidad del vault HYPE en Hypervault.

Este servidor importa la función `obtener_capacidad_hype` del módulo
`scrape_hype` y la usa para devolver un JSON con los valores de
capacidad usada, total y restante. El objetivo es que otras
aplicaciones (por ejemplo, Make) puedan consultar este endpoint para
automatizar tareas de monitorización y alertas.

Para ejecutar localmente, puedes hacer `python app.py` y acceder a
`http://localhost:5000/hype`. En producción, Render ejecutará este
archivo al iniciar el contenedor.
"""

from flask import Flask, jsonify
from scrape_hype import obtener_capacidad_hype


app = Flask(__name__)


@app.route("/hype")
def hype_capacity():
    """
    Endpoint HTTP que devuelve un JSON con la capacidad del vault HYPE.

    El JSON contiene tres campos:
    - used: capacidad ya utilizada
    - total: capacidad total disponible
    - remaining: capacidad restante (total - used)

    Si por algún motivo el scraping no obtiene datos, los valores se
    devolverán como 0.0.
    """
    usado, total, restante = obtener_capacidad_hype()
    return jsonify({
        "used": usado,
        "total": total,
        "remaining": restante,
    })


if __name__ == "__main__":
    # Ejecuta el servidor en el puerto 5000 accesible externamente.
    app.run(host="0.0.0.0", port=5000)