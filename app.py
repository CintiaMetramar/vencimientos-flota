# 1. Definición exacta de columnas esperadas (Tu Estándar)
COLS_SEMANAL = [
    'Tipo Dococumento', # Ojo: Mantengo el "Dococumento" tal cual me lo pasaste (por si es error del ERP)
    'Empresa', 
    'Conductor', 
    'Vehiculo',         # Sin tilde en el semanal
    'Matricula', 
    'Marca', 
    'TipoVehiculo', 
    'Vencimiento'
]

COLS_MAESTRO = [
    'Tipo', 
    'Empresa', 
    'Conductor', 
    'Vehículo',         # Con tilde en el maestro
    'Matricula', 
    'Marca', 
    'Tipo de vehículo', 
    'Fecha de vencimiento', 
    'Telefono'
]

# 2. Diccionario de Mapeo para unificar (Semanal -> Maestro)
# Esto permite que el código trate 'Vencimiento' igual que 'Fecha de vencimiento'
MAPPING_COLUMNAS = {
    'Tipo Dococumento': 'Tipo',
    'Vehiculo': 'Vehículo',
    'TipoVehiculo': 'Tipo de vehículo',
    'Vencimiento': 'Fecha de vencimiento'
}

# Ejemplo de uso rápido al cargar:
# df_semanal = pd.read_excel("semanal.xlsx")[COLS_SEMANAL]
# df_semanal.rename(columns=MAPPING_COLUMNAS, inplace=True)
