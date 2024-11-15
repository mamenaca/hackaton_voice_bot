class BaseDatos:
    def __init__(self):
        self.clientes = [
            {
                'id': 1,
                'nombre': 'Luis Guillermo Pardo',
                'tipologia': 'Jurídica',
                'deuda': 100,
                'fecha_nacimiento': '1980-01-01',
                'documento': '123456789',
                'telefono': '3001234567',
                'email': 'luis.pardo@ejemplo.com',
                'fecha_vencimiento': '2024-12-31',
                'estado_cuenta': 'En mora',
                'historial_pagos': [
                    {'fecha': '2024-01-15', 'monto': 50},
                    {'fecha': '2024-02-15', 'monto': 30}
                ]
            },
            {
                'id': 2,
                'nombre': 'María Rodríguez',
                'tipologia': 'Natural',
                'deuda': 500,
                'fecha_nacimiento': '1985-05-15',
                'documento': '987654321',
                'telefono': '3109876543',
                'email': 'maria.rodriguez@ejemplo.com',
                'fecha_vencimiento': '2024-11-30',
                'estado_cuenta': 'Pendiente',
                'historial_pagos': [
                    {'fecha': '2024-01-20', 'monto': 100}
                ]
            },
            {
                'id': 3,
                'nombre': 'Carlos Ramírez',
                'tipologia': 'Jurídica',
                'deuda': 1500,
                'fecha_nacimiento': '1975-08-22',
                'documento': '456789123',
                'telefono': '3158765432',
                'email': 'carlos.ramirez@ejemplo.com',
                'fecha_vencimiento': '2024-10-15',
                'estado_cuenta': 'En mora',
                'historial_pagos': [
                    {'fecha': '2024-01-10', 'monto': 200},
                    {'fecha': '2024-02-10', 'monto': 150}
                ]
            }
        ]
    
    def obtener_cliente(self, id_cliente):
        """Obtiene un cliente por su ID"""
        return next((cliente for cliente in self.clientes if cliente['id'] == id_cliente), None)
    
    def obtener_todos_clientes(self):
        """Obtiene todos los clientes"""
        return self.clientes
    
    def actualizar_estado_cuenta(self, id_cliente, nuevo_estado):
        """Actualiza el estado de cuenta de un cliente"""
        cliente = self.obtener_cliente(id_cliente)
        if cliente:
            cliente['estado_cuenta'] = nuevo_estado
            return True
        return False
    
    def registrar_pago(self, id_cliente, monto, fecha):
        """Registra un nuevo pago para un cliente"""
        cliente = self.obtener_cliente(id_cliente)
        if cliente:
            cliente['historial_pagos'].append({
                'fecha': fecha,
                'monto': monto
            })
            cliente['deuda'] -= monto
            return True
        return False

    def obtener_historial_pagos(self, id_cliente):
        """Obtiene el historial de pagos de un cliente"""
        cliente = self.obtener_cliente(id_cliente)
        return cliente['historial_pagos'] if cliente else []