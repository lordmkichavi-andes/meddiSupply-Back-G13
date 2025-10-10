# Microservicio de pedidos (orders)

## Estructura de carpetas 
order-tracker-ms/
├── resources/              
│   ├── schema.sql
│   └── insert_data.sql
├── src/
│   ├── domain/
│   │   ├── entities.py       # (Igual) Entidades
│   │   └── interfaces.py     # (Igual) Contratos Repository
│   ├── application/
│   │   └── use_cases.py      # (Igual) Lógica de orquestación
│   └── infrastructure/
│       ├── web/
│       │   └── flask_routes.py # (Igual) Controlador/Presentación
│       └── persistence/
│           ├── db_connector.py   # Conexión principal a PostgreSQL (creación de conexiones)
│           ├── db_initializer.py # Lógica para crear tablas e insertar datos de prueba
│           └── pg_repository.py  # Implementación real del Repositorio (usará db_connector)
├── config.py                 # Configuración de variables de entorno y DB
├── app.py                    # Punto de Entrada, Inicialización de DB y Cableado
└── requirements.txt          # Dependencias (añadimos psycopg2)