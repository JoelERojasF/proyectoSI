import socket
import threading
import os

# Configuracion
HOST = '0.0.0.0'
TCP_PORT = 50000
UDP_PORT = 50001
BUFFER_SIZE = 1024
MAX_CONEXIONES = 10

# Estructuras para clientes
clientes_tcp = []  # Lista de sockets TCP
clientes_udp = []  # Lista de direcciones UDP
usuarios_conectados = {}  # {addr: (usuario, socket_o_udp)}

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

def broadcast(mensaje, protocolo, origen=None):
    """Envia un mensaje a todos los clientes del protocolo especificado"""
    if protocolo == 'tcp':
        for cliente in clientes_tcp[:]:
            try:
                if cliente != origen:
                    cliente.sendall(f"SERVIDOR: {mensaje}\n".encode())
            except:
                clientes_tcp.remove(cliente)
    elif protocolo == 'udp':
        for addr in clientes_udp[:]:
            try:
                if addr != origen:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.sendto(f"SERVIDOR: {mensaje}\n".encode(), addr)
            except:
                clientes_udp.remove(addr)

def enviar_privado(mensaje, usuario_destino):
    """Envia un mensaje privado a un usuario especifico"""
    for addr, (usuario, sock) in usuarios_conectados.items():
        if usuario == usuario_destino:
            try:
                if isinstance(sock, socket.socket):  # TCP
                    sock.sendall(f"PRIVADO: {mensaje}\n".encode())
                else:  # UDP
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.sendto(f"PRIVADO: {mensaje}\n".encode(), addr)
                return True
            except:
                return False
    return False

def manejar_mensaje_tcp(mensaje, addr):
    """Procesa mensajes TCP (publicos/privados)"""
    usuario = usuarios_conectados.get(addr, ["Anonimo"])[0]
    
    if mensaje.startswith('@'):  # Mensaje privado
        partes = mensaje.split(maxsplit=1)
        if len(partes) > 1:
            destino, msg = partes
            destino = destino[1:]  # Quitar @
            if enviar_privado(f"{usuario} te dice: {msg}", destino):
                print(f"[TCP] {usuario} -> {destino}: {msg}")
            else:
                usuarios_conectados[addr][1].sendall(b"Usuario no encontrado\n")
    else:  # Mensaje publico
        print(f"[TCP] {usuario}: {mensaje}")
        broadcast(f"{usuario}: {mensaje}", 'tcp', usuarios_conectados[addr][1])

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

        if usuario in usuarios_validos and usuarios_validos[usuario] == clave:
            conn.sendall(b"Autenticado correctamente\n")
            clientes_tcp.append(conn)
            usuarios_conectados[addr] = (usuario, conn)
            print(f"[TCP] {usuario} conectado desde {addr}")
            broadcast(f"{usuario} se ha conectado (TCP)", 'tcp', conn)
            
            while True:
                data = conn.recv(BUFFER_SIZE)
                if not data or data.decode().strip().lower() == 'salir':
                    break
                manejar_mensaje_tcp(data.decode().strip(), addr)
        else:
            conn.sendall(b"Autenticacion fallida\n")
    except ConnectionResetError:
        print(f"[TCP] {addr} cerro la conexion abruptamente")
    finally:
        if addr in usuarios_conectados:
            usuario = usuarios_conectados[addr][0]
            broadcast(f"{usuario} se ha desconectado", 'tcp')
            print(f"[TCP] {usuario} desconectado")
            del usuarios_conectados[addr]
        if conn in clientes_tcp:
            clientes_tcp.remove(conn)
        conn.close()

def servidor_udp(usuarios_validos):
    """Inicia el servidor UDP"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST, UDP_PORT))
        print(f"[UDP] Servidor escuchando en {HOST}:{UDP_PORT}")
        
        while True:
            data, addr = s.recvfrom(BUFFER_SIZE)
            
            if addr not in clientes_udp:
                # Autenticacion UDP
                credenciales = data.decode().strip().split(':', 1)
                if len(credenciales) == 2:
                    usuario, clave = credenciales
                    if usuario in usuarios_validos and usuarios_validos[usuario] == clave:
                        s.sendto(b"Autenticado correctamente", addr)
                        clientes_udp.append(addr)
                        usuarios_conectados[addr] = (usuario, addr)
                        print(f"[UDP] {usuario} conectado desde {addr}")
                        broadcast(f"{usuario} se ha conectado (UDP)", 'udp', addr)
                    else:
                        s.sendto(b"Autenticacion fallida", addr)
                else:
                    s.sendto(b"Formato incorrecto. Usa usuario:clave", addr)
            else:
                # Manejo de mensajes UDP
                usuario = usuarios_conectados.get(addr, ["Anonimo"])[0]
                mensaje = data.decode().strip()
                
                if mensaje.lower() == 'salir':
                    print(f"[UDP] {usuario} se desconecto")
                    clientes_udp.remove(addr)
                    if addr in usuarios_conectados:
                        broadcast(f"{usuario} se ha desconectado", 'udp')
                        del usuarios_conectados[addr]
                elif mensaje.startswith('@'):  # Privado UDP
                    partes = mensaje.split(maxsplit=1)
                    if len(partes) > 1:
                        destino, msg = partes
                        destino = destino[1:]
                        if enviar_privado(f"{usuario} te dice: {msg}", destino):
                            print(f"[UDP] {usuario} -> {destino}: {msg}")
                else:  # Publico UDP
                    print(f"[UDP] {usuario}: {mensaje}")
                    broadcast(f"{usuario}: {mensaje}", 'udp', addr)

def input_servidor():
    """Permite al servidor enviar mensajes globales/privados"""
    print("\nModo servidor activo. Comandos:")
    print("- [tcp/udp/all] mensaje (broadcast)")
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
                broadcast("El servidor se cierra. Desconectando...", 'udp')
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
                    print("Formato: [tcp/udp/all] mensaje")
                    continue
                    
                destino, mensaje = partes
                destino = destino.lower()
                
                if destino == 'tcp':
                    broadcast(mensaje, 'tcp')
                elif destino == 'udp':
                    broadcast(mensaje, 'udp')
                elif destino == 'all':
                    broadcast(mensaje, 'tcp')
                    broadcast(mensaje, 'udp')
                else:
                    print("Destino invalido. Usa: tcp, udp o all")
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    print("=== INICIANDO SERVIDOR ===")
    usuarios = cargar_usuarios()
    if usuarios:
        print(f"Usuarios cargados: {len(usuarios)}")
        threading.Thread(target=servidor_tcp, args=(usuarios,), daemon=True).start()
        threading.Thread(target=servidor_udp, args=(usuarios,), daemon=True).start()
        threading.Thread(target=input_servidor, daemon=True).start()
        
        try:
            while True: pass
        except KeyboardInterrupt:
            print("\nCerrando servidor...")
            os._exit(0)
    else:
        print("[ERROR] No se pudieron cargar usuarios")