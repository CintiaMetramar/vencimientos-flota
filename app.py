import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
import io
from fpdf import FPDF  # Librería para el PDF

# Configuración de página
st.set_page_config(page_title="Gestión Flota - Metramar", page_icon="🚛", layout="wide")

# ==========================================
# 🔐 1. SEGURIDAD (LOGIN)
# ==========================================
def check_password():
    """Protege la app con contraseña."""
    if "password" not in st.secrets:
        st.error("⚠️ Error: No has configurado la contraseña en los Secrets de Streamlit.")
        return False

    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔑 Contraseña:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔑 Contraseña:", type="password", on_change=password_entered, key="password")
        st.error("❌ Contraseña incorrecta")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ==========================================
# 🛠️ FUNCIONES AUXILIARES (PDF)
# ==========================================
class PDF(FPDF):
    def header(self):
        # Título del PDF
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Reporte de Vencimientos - Flota Metramar', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        # Pie de página
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generar_pdf(dataframe):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Encabezados de tabla
    pdf.set_fill_color(200, 220, 255) # Azul clarito
    pdf.cell(30, 10, "Estado", 1, 0, 'C', 1)
    pdf.cell(40, 10, "Matricula", 1, 0, 'C', 1)
    pdf.cell(70, 10, "Conductor", 1, 0, 'C', 1)
    pdf.cell(40, 10, "Fecha Venc.", 1, 1, 'C', 1)
    
    # Filas
    for _, row in dataframe.iterrows():
        # Traducir los iconos a texto para el PDF (los emojis a veces fallan en PDFs básicos)
        estado_txt = "OK"
        if "🔴" in row['bola']: estado_txt = "VENCIDO"
        elif "🟡" in row['bola']: estado_txt = "PROXIMO"
        
        # Color del texto según estado
        if estado_txt == "VENCIDO": pdf.set_text_color(255, 0, 0)
        elif estado_txt == "PROXIMO": pdf.set_text_color(200, 150, 0)
        else: pdf.set_text_color(0, 0, 0)
            
        pdf.cell(30, 10, estado_txt, 1, 0, 'C')
        pdf.cell(40, 10, str(row['MATRICULA_KEY']), 1, 0, 'C')
        # Cortar nombre conductor si es muy largo
        cond_clean = str(row['CONDUCTOR'])[:25] 
        pdf.cell(70, 10, cond_clean, 1, 0, 'L')
        pdf.cell(40, 10, str(row['FECHA_STR']), 1, 1, 'C')
        
    return pdf.output(dest='S').encode('latin-1', 'replace')

# ==========================================
# 📂 2. ZONA DE CARGA DE ARCHIVOS
# ==========================================
st.title("🚛 Centro de Control: Flota Metramar")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    uploaded_master = st.file_uploader("1️⃣ Sube el MAESTRO (.xlsx)", type=["xlsx"])
with col2:
    uploaded_weekly = st.file_uploader("2️⃣ Sube el SEMANAL del ERP (.xls o .xlsx)", type=["xls", "xlsx"])

if not uploaded_master or not uploaded_weekly:
    st.info("👋 Esperando archivos... Sube ambos para comenzar.")
    st.stop()

# ==========================================
# 🔄 3. LÓGICA DE FUSIÓN
# ==========================================
st.write("🔄 **Procesando datos...**")

try:
    # Lectura de datos
    df_master = pd.read_excel(uploaded_master, dtype=str)
    
    if uploaded_weekly.name.endswith('.xls'):
        df_weekly = pd.read_excel(uploaded_weekly, dtype=str, engine='xlrd')
    else:
        df_weekly = pd.read_excel(uploaded_weekly, dtype=str)

    # Normalización
    df_master.columns = df_master.columns.str.strip().str.upper()
    df_weekly.columns = df_weekly.columns.str.strip().str.upper()

    # Búsqueda de claves
    KEY_M = next((c for c in df_master.columns if "MATRICULA" in c or "VEHICULO" in c), None)
    KEY_W = next((c for c in df_weekly.columns if "MATRICULA" in c or "VEHICULO" in c), None)
    DATE_M = next((c for c in df_master.columns if "VENCI" in c and "FECHA" in c), None)
    DATE_W = next((c for c in df_weekly.columns if "VENCI" in c and "FECHA" in c), None)
    
    # Búsqueda de extras para el reporte
    COL_COND = next((c for c in df_master.columns if "CONDUCTOR" in c), "CONDUCTOR")
    COL_TEL = next((c for c in df_master.columns if "TELEFONO" in c or "TELÉFONO" in c), "TELEFONO")

    if not KEY_M or not KEY_W or not DATE_M or not DATE_W:
        st.error("❌ No se encuentran las columnas clave (Matrícula/Fecha). Revisa los Excels.")
        st.stop()

    # Renombrar para merge
    df_master = df_master.rename(columns={KEY_M: "MATRICULA_KEY"})
    df_weekly = df_weekly.rename(columns={KEY_W: "MATRICULA_KEY"})

    # Fechas
    df_master[DATE_M] = pd.to_datetime(df_master[DATE_M], errors="coerce")
    df_weekly[DATE_W] = pd.to_datetime(df_weekly[DATE_W], errors="coerce")

    # Merge
    merged = pd.merge(
        df_master,
        df_weekly[["MATRICULA_KEY", DATE_W]],
        on="MATRICULA_KEY",
        how="left",
        suffixes=("", "_new")
    )
    
    # Actualización inteligente de fechas
    merged[DATE_M] = merged[f"{DATE_W}_new"].combine_first(merged[DATE_M])
    df_final = merged.drop(columns=[f"{DATE_W}_new"], errors='ignore')

except Exception as e:
    st.error(f"❌ Error procesando archivos: {e}")
    st.stop()

# ==========================================
# 🚦 4. REPORTE VISUAL Y ACCIONES
# ==========================================
st.divider()
st.subheader("📊 Informe de Estado")

hoy = datetime.now()
margen_30 = hoy + timedelta(days=30)
margen_menos_30 = hoy - timedelta(days=30)

# Filtro: Próximos 30 días o vencidos hace menos de 30 días
mask = (df_final[DATE_M] <= margen_30) & (df_final[DATE_M] >= margen_menos_30)
df_reporte = df_final[mask].copy()

if df_reporte.empty:
    st.success("✨ ¡Todo en orden! No hay vencimientos próximos.")
else:
    # Preparar datos para visualización
    datos_visuales = []
    
    for _, row in df_reporte.iterrows():
        fecha = row[DATE_M]
        conductor = row[COL_COND] if COL_COND in df_reporte.columns and pd.notna(row[COL_COND]) else "Sin Asignar"
        telefono = str(row[COL_TEL]).replace(".0", "") if COL_TEL in df_reporte.columns and pd.notna(row[COL_TEL]) else ""
        
        # Semáforo
        if pd.isna(fecha):
            bola = "⚪"
        elif fecha < hoy:
            bola = "🔴 VENCIDO"
        elif fecha <= hoy + timedelta(days=7):
            bola = "🟡 PRÓXIMO"
        else:
            bola = "🟢 AL DÍA"

        fecha_str = fecha.strftime('%d/%m/%Y') if pd.notna(fecha) else "-"
        
        # Link WhatsApp
        link_wa = None
        if telefono:
            tel_clean = "".join(filter(str.isdigit, telefono))
            if len(tel_clean) == 9: tel_clean = "34" + tel_clean # Asumimos España
            
            if len(tel_clean) >= 9:
                msg = f"Hola {conductor}, el vehículo {row['MATRICULA_KEY']} vence el {fecha_str}. Por favor revisa la documentación."
                link_wa = f"https://wa.me/{tel_clean}?text={urllib.parse.quote(msg)}"

        datos_visuales.append({
            "bola": bola,
            "MATRICULA_KEY": row["MATRICULA_KEY"],
            "CONDUCTOR": conductor,
            "FECHA_STR": fecha_str,
            "link": link_wa
        })

    # Convertir a DataFrame temporal para facilitar manejo
    df_vis = pd.DataFrame(datos_visuales)

    # 1. MOSTRAR TABLA EN PANTALLA
    st.write(f"⚠️ Se han detectado **{len(df_vis)}** vehículos para revisar.")
    
    # Cabecera tabla
    c1, c2, c3, c4, c5 = st.columns([1, 1.5, 2, 1.5, 1.5])
    c1.markdown("**Estado**")
    c2.markdown("**Matrícula**")
    c3.markdown("**Conductor**")
    c4.markdown("**Fecha**")
    c5.markdown("**Acción**")
    st.markdown("---")

    # Filas tabla
    for d in datos_visuales:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([1, 1.5, 2, 1.5, 1.5])
            col1.write(d["bola"])
            col2.write(d["MATRICULA_KEY"])
            col3.write(d["CONDUCTOR"])
            col4.write(d["FECHA_STR"])
            
            if d["link"]:
                col5.link_button("📲 WhatsApp", d["link"])
            else:
                col5.write("-")
            st.markdown("---")

    # 2. GENERACIÓN Y DESCARGA DE PDF
    st.subheader("📥 Descargas")
    
    # Crear PDF en memoria
    pdf_bytes = generar_pdf(df_vis)
    
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        st.download_button(
            label="📄 Descargar Informe PDF",
            data=pdf_bytes,
            file_name=f"Informe_Flota_{datetime.now().strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf"
        )
        
    with col_dl2:
        # Recrear Excel del maestro actualizado
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
            df_final.to_excel(writer, index=False)
            
        st.download_button(
            label="💾 Descargar Excel Maestro",
            data=buffer_excel.getvalue(),
            file_name=f"Maestro_Actualizado_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
