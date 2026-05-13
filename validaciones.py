import re

MIN_USUARIO = 3
MAX_USUARIO = 20
MIN_CLAVE = 3
MAX_CLAVE = 50
MAX_MENSAJE = 500

PALABRAS_RESERVADAS = {'admin', 'servidor', 'server', 'root', 'sistema'}

#sanitizacion
def sanitizar_usuario(usuario):
    usuario = usuario.strip()
    usuario = usuario.lower()
    usuario = re.sub(r'[^\w]', '', usuario)
    return usuario

def sanitizar_mensaje(mensaje):
    mensaje = mensaje.strip()
    mensaje = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', mensaje)
    return mensaje

#validacion
def validar_usuario(usuario):
    if len(usuario) < MIN_USUARIO:
        return False, f"Mínimo {MIN_USUARIO} caracteres"
    if len(usuario) > MAX_USUARIO:
        return False, f"Máximo {MAX_USUARIO} caracteres"
    if not re.match(r'^\w+$', usuario):
        return False, "Solo se permiten letras, números y _"
    if usuario in PALABRAS_RESERVADAS:
        return False, "Nombre de usuario reservado"
    return True, ""

def validar_clave(clave):
    if len(clave) < MIN_CLAVE:
        return False, f"Mínimo {MIN_CLAVE} caracteres"
    if len(clave) > MAX_CLAVE:
        return False, f"Máximo {MAX_CLAVE} caracteres"
    return True, ""

def validar_mensaje(mensaje):
    if not mensaje:
        return False, "Mensaje vacío"
    if len(mensaje) > MAX_MENSAJE:
        return False, f"Máximo {MAX_MENSAJE} caracteres"
    return True, ""