import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
import io
from fpdf import FPDF

# ==========================================
# 🚛 CONFIGURACIÓN Y ESTÁNDARES
# ==========================================
st.set_page_config(page_title="Gestión Flota - Metramar", page_icon="🚛", layout="wide")

COLS_SEMANAL = ['Tipo Dococumento', 'Empresa', 'Conductor', 'Vehiculo', 'Matricula', 'Marca', 'TipoVehiculo', 'Vencimiento']
COLS_MAESTRO = ['Tipo', 'Empresa', 'Conductor', 'Vehículo', 'Matricula', 'Marca', 'Tipo de vehículo', 'Fecha de vencimiento', 'Telefono']
MAPEO_A_MAESTRO = {'Tipo Dococumento': 'Tipo', 'Vehiculo': 'Vehículo', 'TipoVehiculo': 'Tipo de vehículo', 'Vencimiento': 'Fecha de vencimiento'}

# ==========================================
# 🔐 1. SEGURIDAD
# ==========================================
def check_password():
    if "password_correct" not in st.session_state:
        st.text_input("🔑 Contraseña:", type="password", on_change=lambda: st.session_state.update({"password_correct": st.session_state["password"] == st.secrets["password"]}), key="password")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.stop()

# ==========================================
# 🛠️ FUNCIONES AUXILIARES (PDF)
# ==========================================
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Reporte de Vencimientos - Metramar', 0, 1, 'C')
        self.ln(5)

def generar_pdf(dataframe):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.set_fill_color(200, 220, 255)
    cols = [("Estado", 30), ("Matricula", 40), ("Conductor", 70), ("Vencimiento", 40)]
    for txt, w in cols: pdf.cell(w, 10, txt, 1, 0, 'C', 1)
    pdf.ln()
    for _, row in dataframe.iterrows():
        estado = "VENCIDO" if "🔴" in row['bola'] else ("PROXIMO" if "🟡" in row['bola'] else "OK")
        pdf.cell(30, 10, estado, 1)
        pdf.cell(40, 10, str(row['Matricula']), 1)
        pdf.cell(70, 10, str(row['Conductor'])[:25], 1)
        pdf.cell(40, 10, str(row['Fecha_Str']), 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1', 'replace')

# ==========================================
# 📂 2. CARGA Y PROCESAMIENTO
# ==========================================
st.title("🚛 Centro de Control: Metramar")

col1, col2 = st.columns(2)
with col1:
    uploaded_master = st.file_uploader("1️⃣ Fichero MAESTRO", type=["xlsx"])
with col2:
    uploaded_weekly = st.file_uploader("2️⃣ Fichero SEMANAL ERP", type=["xls", "xlsx"])

if uploaded_master and uploaded_weekly:
    df_final = pd.DataFrame() # Inicializar
    
    try:
        df_m = pd.read_excel(uploaded_master)
        if uploaded_weekly.name.endswith('.xls'):
            df_s = pd.read_excel(uploaded_weekly, engine='xlrd')
        else:
            df_s = pd.read_excel(uploaded_weekly)

        # Validar columnas
        missing_s = [c for c in COLS_SEMANAL if c not in df_s.columns]
        missing_m = [c for c in COLS_MAESTRO if c not in df_m.columns]

        if missing_s or missing_m:
            st.error(f"❌ Error de columnas. Faltan en Semanal: {missing_s} | Faltan en Maestro: {missing_m}")
            st.stop()

        # Fusión
        df_s_clean = df_s[COLS_SEMANAL].rename(columns=MAPEO_A_MAESTRO)
        df_m['Matricula_Match'] = df_m['Matricula'].astype(str).str.strip().str.upper()
        df_s_clean['Matricula_Match'] = df_s_clean['Matricula'].astype(str).str.strip().str.upper()

        merged = pd.merge(df_m, df_s_clean[['Matricula_Match', 'Fecha de vencimiento']], on='Matricula_Match', how='left', suffixes=('_old', '_new'))
        merged['Fecha de vencimiento'] = merged['Fecha de vencimiento_new'].fillna(merged['Fecha de vencimiento_old'])
        df_final = merged.drop(columns=['Matricula_Match', 'Fecha de vencimiento_new', 'Fecha de vencimiento_old'], errors='ignore')
        df_final['Fecha de vencimiento'] = pd.to_datetime(df_final['Fecha de vencimiento'], errors='coerce')

    except Exception as e:
        st.error(f"⚠️ Error en el procesado: {e}")
        st.stop()

    # ==========================================
    # 🚦 3. INFORME Y ALERTAS (DENTRO DEL IF)
    # ==========================================
    st.subheader("📊 Análisis de Vencimientos Próximos")
    
    hoy = datetime.now()
    rango_alerta = hoy + timedelta(days=30)
    df_alertas = df_final[df_final['Fecha de vencimiento'] <= rango_alerta].copy()

    if df_alertas.empty:
        st.success("✅ Todo al día. No hay vencimientos en los próximos 30 días.")
    else:
        resumen = []
        for _, row in df_alertas.iterrows():
            fecha_venc = row['Fecha de vencimiento']
            conductor = row.get('Conductor', 'Sin Asignar')
            matricula = row.get('Matricula', 'S/M')
            
            if pd.isna(fecha_venc): bola = "⚪"
            elif fecha_venc < hoy: bola = "🔴 VENCIDO"
            elif fecha_venc <= hoy + timedelta(days=7): bola = "🟡 URGENTE"
            else: bola = "🟢 AVISAR"

            fecha_str = fecha_venc.strftime('%d/%m/%Y') if pd.notna(fecha_venc) else "S/D"
            
            # TU MENSAJE PERSONALIZADO
            texto = (
                f"🚨 *AVISO DE VENCIMIENTO* 🚨\n"
                f"📌 Tipo: {row.get('Tipo','')}\n"
                f"🏢 Empresa: {row.get('Empresa','')}\n"
                f"👤 Conductor: {conductor}\n"
                f"🚛 Vehículo: {row.get('Vehículo','')}\n"
                f"🔖 Matrícula: {matricula}\n"
                f"📅 Fecha: {fecha_str}\n"
            )

            if pd.notna(fecha_venc):
                if fecha_venc < hoy:
                    texto += "⚠️ Este documento ya ha vencido. Por favor, si no lo has hecho ya, sube la documentación a la oficina para su actualización.\n"
                else:
                    texto += "✅ Por favor, pase por taller a programar la *revisión Pre-ITV* o coordine con su responsable la cita para la *ITV/Tacógrafo*, Si llevas remolque, por favor comprueba la documentación. Las tractoras y remolques pueden aumentar su MMA, pedir en oficina la autorización.\n"

            texto += "\n📩 Si ya no llevas este camión responde a este mensaje con la matrícula del camión que llevas actualmente."

            wa_link = None
            tel = str(row.get('Telefono', '')).replace(".0", "").strip()
            if tel and tel != "nan" and tel != "":
                tel_clean = "".join(filter(str.isdigit, tel))
                if len(tel_clean) == 9: tel_clean = "34" + tel_clean
                wa_link = f"https://wa.me/{tel_clean}?text={urllib.parse.quote(texto)}"

            resumen.append({"bola": bola, "Matricula": matricula, "Conductor": conductor, "Fecha_Str": fecha_str, "link": wa_link})

        for r in resumen:
            c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
            c1.write(r["bola"])
            c2.write(r["Matricula"])
            c3.write(r["Conductor"])
            c4.write(r["Fecha_Str"])
            if r["link"]: c5.link_button("📲 Enviar", r["link"])
            else: c5.write("🚫 S/T")
            st.divider()

        # Descargas
        st.subheader("📥 Exportar Resultados")
        col_a, col_b = st.columns(2)
        with col_a:
            pdf_bytes = generar_pdf(pd.DataFrame(resumen))
            st.download_button("📄 Descargar PDF", pdf_bytes, "informe.pdf", "application/pdf")
        with col_b:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False)
            st.download_button("💾 Descargar Maestro Actualizado", output.getvalue(), "maestro_final.xlsx")
