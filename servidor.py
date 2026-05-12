import socket
import threading
import os
from datetime import datetime
import hashlib
import logging

# Configuración del log
logging.basicConfig(filename="chat.log", level=logging.INFO)

# Configuracion
HOST = '0.0.0.0'
TCP_PORT = 50000
BUFFER_SIZE = 1024
MAX_CONEXIONES = 5

# Estructura para clientes
clientes_tcp = {}  # {usuario: conn}
usuarios_conectados = {}  # {addr: (usuario, conn)}


def hash_password(password):
    """Genera el hash SHA-256 de una contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def formatear_mensaje(usuario, mensaje):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{usuario}] {timestamp}: {mensaje}"

def cargar_usuarios():
    """Carga usuarios desde el archivo usuarios.txt"""
    usuarios = {}
    try:
        with open('usuarios.txt', 'r') as f:
            for linea in f:
                if ':' in linea:
                    usuario, clave = linea.strip().split(':', 1)
                    usuarios[usuario] = clave
    except FileNotFoundError:
        print("[ERROR] Archivo usuarios.txt no encontrado")
    return usuarios

def broadcast(mensaje, origen=None):
    """Envía un mensaje a todos los clientes TCP"""
    for usuario, conn in list(clientes_tcp.items()):
        try:
            if conn != origen:
                conn.sendall(f"SERVIDOR: {mensaje}\n".encode())
        except:
            del clientes_tcp[usuario]

def enviar_privado(mensaje, usuario_destino):
    """Envia un mensaje privado a un usuario especifico"""
    for addr, (usuario, sock) in usuarios_conectados.items():
        if usuario == usuario_destino:
            try:
                if isinstance(sock, socket.socket):  # TCP
                    sock.sendall(f"PRIVADO: {mensaje}\n".encode())
            except:
                return False
    return False

def manejar_mensaje_tcp(mensaje, usuario, conn):
    if mensaje.startswith('@'):
        partes = mensaje.split(maxsplit=1)
        if len(partes) > 1:
            destino, msg = partes
            destino = destino[1:]
            if enviar_privado(formatear_mensaje(usuario, msg), destino):
                print(f"[TCP] {usuario} -> {destino}: {msg}")
            else:
                conn.sendall(b"Usuario no encontrado\n")
    else:
        print(f"[TCP] {usuario}: {mensaje}")
        broadcast(formatear_mensaje(usuario, mensaje), conn)

def servidor_tcp(usuarios_validos):
    """Inicia el servidor TCP"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, TCP_PORT))
        s.listen(MAX_CONEXIONES)
        print(f"[TCP] Servidor escuchando en {HOST}:{TCP_PORT}")
        
        while True:
            conn, addr = s.accept()
            threading.Thread(target=autenticar_tcp, args=(conn, addr, usuarios_validos), daemon=True).start()

def autenticar_tcp(conn, addr, usuarios_validos):
    """Autentica clientes TCP"""
    try:
        conn.sendall(b"Usuario: ")
        usuario = conn.recv(BUFFER_SIZE).decode().strip()
        conn.sendall(b"Clave: ")
        clave = conn.recv(BUFFER_SIZE).decode().strip()

        # Validar credenciales con hash
        if usuario in usuarios_validos and usuarios_validos[usuario] == hash_password(clave):
            # Verificar usuario único
            if usuario in clientes_tcp:
                conn.sendall(b"Usuario ya conectado\n")
                conn.close()
                return

            # Verificar límite de conexiones
            if len(clientes_tcp) >= MAX_CONEXIONES:
                conn.sendall(b"Servidor lleno\n")
                conn.close()
                return

            # Autenticación exitosa
            conn.sendall(b"Autenticado correctamente\n")
            clientes_tcp[usuario] = conn
            usuarios_conectados[addr] = (usuario, conn)
            print(f"[TCP] {usuario} conectado desde {addr}")
            logging.info(f"{usuario} conectado desde {addr}")
            broadcast(f"{usuario} se ha conectado", conn)

            # Manejo de mensajes
            while True:
                data = conn.recv(BUFFER_SIZE)
                if not data or data.decode().strip().lower() == 'salir':
                    break
                mensaje = data.decode().strip()
                manejar_mensaje_tcp(mensaje, usuario, conn)
                logging.info(f"{usuario} envió: {mensaje}")

        else:
            conn.sendall(b"Autenticacion fallida\n")

    except ConnectionResetError:
        print(f"[TCP] {addr} cerró la conexión abruptamente")
    finally:
        if addr in usuarios_conectados:
            usuario = usuarios_conectados[addr][0]
            broadcast(f"{usuario} se ha desconectado")
            print(f"[TCP] {usuario} desconectado")
            logging.info(f"{usuario} se desconectó")
            del usuarios_conectados[addr]
        if usuario in clientes_tcp:
            del clientes_tcp[usuario]
        conn.close()

def input_servidor():
    """Permite al servidor enviar mensajes globales/privados"""
    print("\nModo servidor activo. Comandos:")
    print("- [tcp/all] mensaje (broadcast)")
    print("- @usuario mensaje (privado)")
    print("- shutdown (apagar servidor)")
    
    while True:
        try:
            entrada = input("Servidor> ").strip()
            if not entrada:
                continue
                
            if entrada.lower() == 'shutdown':
                print("Cerrando servidor...")
                broadcast("El servidor se cierra. Desconectando...", 'tcp')
                os._exit(0)
                
            if entrada.startswith('@'):  # Privado desde servidor
                partes = entrada.split(maxsplit=1)
                if len(partes) > 1:
                    destino, msg = partes
                    destino = destino[1:]
                    if enviar_privado(f"SERVIDOR: {msg}", destino):
                        print(f"Enviado a {destino}")
                    else:
                        print("Usuario no encontrado")
            else:  # Broadcast
                partes = entrada.split(maxsplit=1)
                if len(partes) < 2:
                    print("Formato: [tcp/all] mensaje")
                    continue
                    
                destino, mensaje = partes
                destino = destino.lower()
                
                if destino == 'tcp' or destino == "all":
                    broadcast(mensaje)
                else:
                    print("Destino invalido. Usa: tcp o all")
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    print("=== INICIANDO SERVIDOR ===")
    usuarios = cargar_usuarios()
    if usuarios:
        print(f"Usuarios cargados: {len(usuarios)}")
        threading.Thread(target=servidor_tcp, args=(usuarios,), daemon=True).start()
        threading.Thread(target=input_servidor, daemon=True).start()
        
        try:
            while True: pass
        except KeyboardInterrupt:
            print("\nCerrando servidor...")
            os._exit(0)
    else:
        print("[ERROR] No se pudieron cargar usuarios")