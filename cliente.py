import socket
import threading
import sys
import hashlib
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from validaciones import sanitizar_usuario, sanitizar_mensaje, validar_usuario, validar_clave, validar_mensaje

# Configuración
HOST = "127.0.0.1"  # Cambiar por IP del servidor
TCP_PORT = 50000
BUFFER_SIZE = 1024

class ClienteChat:
    def __init__(self):
        self.usuario_actual = ""
        self.tcp_active = False

    def recibir_tcp(self, conn):
        while self.tcp_active:
            try:
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    print("\n[Servidor] Conexión cerrada")
                    break
                print(f"\n{data.decode()}", end='')
                print(f"{self.usuario_actual}> ", end='', flush=True)
            except:
                print("\n[Error] Conexión TCP perdida")
                break

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def cifrar(self, public_key, texto):
        return public_key.encrypt(
            texto.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def cliente_tcp(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((HOST, TCP_PORT))
                public_pem = b''
                while b"-----END PUBLIC KEY-----" not in public_pem:
                    public_pem += s.recv(1024)
                public_key = serialization.load_pem_public_key(public_pem)
                self.tcp_active = True
                print("Conexión TCP establecida")

                # Autenticación
                #usuario
                print(s.recv(BUFFER_SIZE).decode(), end='')
                while True:
                    usuario_raw = input().strip()
                    usuario = sanitizar_usuario(usuario_raw)
                    valido, motivo = validar_usuario(usuario)
                    if valido:
                        break
                    print(f"[Error] {motivo}. Intenta de nuevo: ", end='')

                self.usuario_actual = usuario
                s.sendall(self.cifrar(public_key, self.usuario_actual))

                #contraseña
                print(s.recv(BUFFER_SIZE).decode(), end='')

                while True:
                    clave_raw = input().strip()
                    valido, motivo = validar_clave(clave_raw)
                    if valido:
                        break
                    print(f"[Error] {motivo}. Intenta de nuevo: ", end='')

                clave_hasheada = self.hash_password(clave_raw)
                s.sendall(self.cifrar(public_key, clave_hasheada))


                respuesta = s.recv(BUFFER_SIZE).decode()
                print(respuesta)

                if "Autenticado" in respuesta:
                    threading.Thread(target=self.recibir_tcp, args=(s,), daemon=True).start()

                    #mensaje
                    while self.tcp_active:
                        msg_raw = input(f"{self.usuario_actual}> ")
                        if msg_raw.lower() == 'salir':
                            s.sendall(self.cifrar(public_key, 'salir'))
                            self.tcp_active = False
                            break

                        msg = sanitizar_mensaje(msg_raw)
                        valido, motivo = validar_mensaje(msg)
                        if not valido:
                            print(f"[Error] {motivo}")
                            continue

                        s.sendall(self.cifrar(public_key, msg))

            except ConnectionRefusedError:
                print("[Error] Servidor no disponible")
            except Exception as e:
                print(f"[Error TCP] {e}")
            finally:
                self.tcp_active = False

    def iniciar(self):
        print("=== CLIENTE DE CHAT (TCP) ===")
        print(f"Conectando a {HOST}")
        self.cliente_tcp()

if __name__ == "__main__":
    cliente = ClienteChat()
    try:
        cliente.iniciar()
    except KeyboardInterrupt:
        print("\nCliente terminado")
        sys.exit(0)