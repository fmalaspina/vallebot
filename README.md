## VALLEBOT

Es un servicio de gestion de servicios profesionales a través de whatsapp diseñado para actuar como un asistente virtual del profesional. Funciona como una secretaria, maneja cobros, agendas e inscripciones, así como también, notifica al profesional del estado de situación.
Casos de uso posibles son los de médicos, masajistas, entrenadores personales, profesores, etc. que da su servicio en una ubicación o a domicilio. También pueden manejar distintos tipos de cobros según actividad: sesión o recurrente tipo clase grupal. 

El sistema detecta (o consulta si hay ambigüedad) el servicio relacionado con el cliente y relaciona el agendamiento o la informacion brindada de acuerdo al contexto.

El servicio recibe un mensaje de Whatsapp Cloud Api con un mensaje de profesional o cliente. De acuerdo al tipo de mensaje debe identificar a la persona (profesional o cliente) y recuperar todo el contexto relacionado. Luego debe categorizar el tipo de mensaje para realizar la operación solicitada. Es decir que no solo responde utilizando la información apropiada del contexto, sino que también debe dar una instrucción de bajo nivel al sistema para realizar la operación adecuada.

1. Alcance funcional (resumido y alineado)
Actor	Acciones clave (MVP)
Profesional	Definir servicios (1:1 o grupal), registrar ubicación (o “a domicilio”), ver / confirmar / cancelar reservas, ver inscriptos de clase, consultar estado de cobros básicos.
Cliente	Pedir turno / pedir inscripción a clase, consultar disponibilidad próxima, enviar comprobante de pago, cancelar / reprogramar (si política lo permite).
Sistema (Vallebot)	Identificar quién escribe (profesional / cliente), recuperar contexto (estado resumido), clasificar intención, completar slots (pedir datos faltantes), ejecutar acción (crear reserva / inscripción / marcar pago / responder info), notificar a profesional y/o cliente.

2. Principios de diseño aplicados
Core mínimo transaccional: sólo lo que requiere consistencia.

Snapshot denormalizado para respuestas rápidas y RAG (estado relación profesional‑cliente).

Embeddings auxiliares, no fuente de verdad.

Acciones = intents estructurados (no SQL generado por LLM).

Evolución incremental: se podrán añadir clases avanzadas (planes, recordatorios, lista de espera) sin romper lo existente.

3. Esquema mínimo propuesto
Tablas Core
Tabla	Propósito	Notas
profesionales	Datos básicos del profesional.	Teléfono + nombre para identificación.
clientes	Datos del cliente.	Teléfono + nombre; email opcional.
servicios	Definición de cada servicio (turno 1:1 o clase grupal).	Incluye tipo, duración, capacidad si grupal, política cancelación.
bookings	Reservas de sesiones 1:1 y ocurrencias de clases (instancias) a las que se asocian inscripciones.	Para clases repetitivas se crea booking “clase” + inscripciones.
enrollments	Inscripciones de clientes a una clase grupal (si el servicio es grupal).	Opcional para servicios tipo grupal.
payments	Pagos simples asociados a cliente (y opcionalmente a servicio/booking).	MVP: sin planes; sólo monto + estado.
messages	Log de mensajes entrantes/salientes (WhatsApp).	Para contexto y auditoría.
interpreted_actions (opcional en MVP)	Registro del JSON interpretado por el LLM (intent + slots).	Útil para mejorar prompts.
relationship_state	Snapshot resumido (profesional, cliente).	Resumen + embedding.