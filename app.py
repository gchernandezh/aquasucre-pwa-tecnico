from flask import Flask, render_template, jsonify, request
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

def conexion():
    return psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

@app.get('/')
def inicio():
    return render_template('index.html')

@app.get('/api/tecnicos')
def tecnicos():
    with conexion() as cn, cn.cursor() as cur:
        cur.execute("SELECT id_tecnico, nombre FROM tecnicos WHERE UPPER(estado)='ACTIVO' ORDER BY nombre")
        return jsonify(cur.fetchall())

@app.get('/api/ordenes')
def ordenes():
    id_tecnico = request.args.get('id_tecnico', type=int)
    if not id_tecnico:
        return jsonify({'error':'id_tecnico requerido'}), 400
    with conexion() as cn, cn.cursor() as cur:
        cur.execute('''SELECT id_ot,id_pqr,tipo_servicio,descripcion,direccion,prioridad,estado,
                              fecha_inicio,fecha_finalizacion,diagnostico,trabajo_realizado,observaciones
                       FROM ordenes_trabajo WHERE id_tecnico=%s
                       ORDER BY fecha_creacion DESC''', (id_tecnico,))
        return jsonify(cur.fetchall())

@app.post('/api/ordenes/<int:id_ot>/iniciar')
def iniciar(id_ot):
    data=request.get_json(silent=True) or {}
    id_tecnico=data.get('id_tecnico')
    with conexion() as cn, cn.cursor() as cur:
        cur.execute("""UPDATE ordenes_trabajo SET estado='EN_PROCESO', fecha_inicio=NOW()
                       WHERE id_ot=%s AND id_tecnico=%s AND estado='ASIGNADA'
                       RETURNING id_ot,estado,fecha_inicio""", (id_ot,id_tecnico))
        fila=cur.fetchone()
        if not fila: return jsonify({'error':'No se pudo iniciar la OT'}),409
        cn.commit(); return jsonify(fila)

@app.put('/api/ordenes/<int:id_ot>/reporte')
def reporte(id_ot):
    data=request.get_json(silent=True) or {}
    with conexion() as cn, cn.cursor() as cur:
        cur.execute('''UPDATE ordenes_trabajo SET diagnostico=%s, trabajo_realizado=%s, observaciones=%s
                       WHERE id_ot=%s AND id_tecnico=%s AND estado='EN_PROCESO' RETURNING id_ot''',
                    (data.get('diagnostico'),data.get('trabajo_realizado'),data.get('observaciones'),id_ot,data.get('id_tecnico')))
        if not cur.fetchone(): return jsonify({'error':'No se pudo guardar'}),409
        cn.commit(); return jsonify({'ok':True})

@app.post('/api/ordenes/<int:id_ot>/finalizar')
def finalizar(id_ot):
    data=request.get_json(silent=True) or {}
    with conexion() as cn, cn.cursor() as cur:
        cur.execute('''UPDATE ordenes_trabajo SET diagnostico=%s, trabajo_realizado=%s, observaciones=%s,
                       estado='FINALIZADA', fecha_finalizacion=NOW()
                       WHERE id_ot=%s AND id_tecnico=%s AND estado='EN_PROCESO'
                       RETURNING id_ot,estado,fecha_finalizacion''',
                    (data.get('diagnostico'),data.get('trabajo_realizado'),data.get('observaciones'),id_ot,data.get('id_tecnico')))
        fila=cur.fetchone()
        if not fila: return jsonify({'error':'No se pudo finalizar'}),409
        cn.commit(); return jsonify(fila)

if __name__ == '__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
