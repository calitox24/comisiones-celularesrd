import streamlit as st
import pandas as pd
import datetime

def calcular_comisiones(file_path, sustitutas):
    # Alias de correos a nombres
    alias_vendedores = {
        "jelianyrs1607@gmail.com": "Jelianys",
        "venusfrias95@icloud.com": "Venus",
        "perlamasieltamares65@gmail.com": "Perla",
        "delossantoslaury@hotmail.com": "Laury",
        "celularesrd@gmail.com": "Tienda",
        "desire": "Desire"
    }

    # Leer archivo
    df = pd.read_excel(file_path, sheet_name="Sheet1")
    df["VendedorNombre"] = df["Vendedor"].apply(lambda x: alias_vendedores.get(str(x).lower(), str(x)))
    df["Fecha de Compra"] = pd.to_datetime(df["Fecha de Compra"])

    # Filtrar solo ventas KRECE (Monto financiado > 0)
    df = df[df["Monto Financiado"] > 0]

    # Semana de corte (ejemplo: semana pasada)
    today = datetime.date.today()
    last_monday = today - datetime.timedelta(days=today.weekday()+7)
    last_sunday = last_monday + datetime.timedelta(days=6)
    df = df[(df["Fecha de Compra"] >= pd.to_datetime(last_monday)) & (df["Fecha de Compra"] <= pd.to_datetime(last_sunday))]

    # Mapear días
    dias_map = {"Monday": "Lunes","Tuesday": "Martes","Wednesday": "Miércoles",
                "Thursday": "Jueves","Friday": "Viernes","Saturday": "Sábado","Sunday": "Domingo"}
    df["DiaSemana"] = df["Fecha de Compra"].dt.day_name().map(dias_map)

    # Variables acumuladoras
    detalle_vendedores = {}
    comision_desire, comision_sustitutas = 0, {}

    # Procesar fila por fila
    for _, row in df.iterrows():
        vendedor = row["VendedorNombre"]
        fecha = row["Fecha de Compra"].date()
        dia = row["DiaSemana"]

        if vendedor.lower() == "desire":
            comision_v = 250
            comision_desire += 250
        else:
            comision_v = 150
            if dia == "Jueves":
                sustituta = sustitutas.get(str(fecha), "Laury")  # valor elegido en el select
                comision_sustitutas[sustituta] = comision_sustitutas.get(sustituta, 0) + 100
            else:
                comision_desire += 100

        # acumular vendedor
        if vendedor not in detalle_vendedores:
            detalle_vendedores[vendedor] = {"ventas": 0, "comision": 0}
        detalle_vendedores[vendedor]["ventas"] += 1
        detalle_vendedores[vendedor]["comision"] += comision_v

    # Crear DataFrames
    df_vendedores = pd.DataFrame([
        {"Vendedor": v, "Ventas KRECE": data["ventas"], "Comisión Venta": data["comision"]}
        for v, data in detalle_vendedores.items()
    ])

    df_redes = pd.DataFrame(
        [{"Asignado": "Desire", "Comisión Redes": comision_desire - (detalle_vendedores.get("Desire", {"comision":0})["comision"])}] +
        [{"Asignado": s, "Comisión Redes": c} for s, c in comision_sustitutas.items()]
    )

    df_resumen = pd.DataFrame(
        [{"Concepto": "Total Comisión Desire", "Monto": comision_desire}] +
        [{"Concepto": f"Total Comisión Sustituta ({s})", "Monto": c} for s, c in comision_sustitutas.items()]
    )

    # Totales combinados (ventas + redes)
    totales_combinados = {}
    for v, data in detalle_vendedores.items():
        totales_combinados[v] = data["comision"]
    totales_combinados["Desire"] = totales_combinados.get("Desire", 0) + comision_desire
    for s, c in comision_sustitutas.items():
        totales_combinados[s] = totales_combinados.get(s, 0) + c

    df_totales = pd.DataFrame([
        {"Vendedor": v, "Total Semana (ventas + redes)": total}
        for v, total in totales_combinados.items()
    ])

    return df_vendedores, df_redes, df_resumen, df_totales


# ==============================
# 📊 Streamlit UI
# ==============================
st.title("📊 Calculadora de Comisiones – CELULARES RD")

uploaded_file = st.file_uploader("Sube el archivo de ventas (.xlsx)", type=["xlsx"])

if uploaded_file:
    with open("temp.xlsx", "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Detectar todos los jueves en el archivo
    df_preview = pd.read_excel("temp.xlsx", sheet_name="Sheet1")
    df_preview["Fecha de Compra"] = pd.to_datetime(df_preview["Fecha de Compra"])
    df_preview["DiaSemana"] = df_preview["Fecha de Compra"].dt.day_name()
    jueves_fechas = df_preview[df_preview["DiaSemana"] == "Thursday"]["Fecha de Compra"].dt.date.unique()

    st.subheader("📌 Selecciona sustituta para cada jueves")
    sustitutas = {}
    for fecha in jueves_fechas:
        sustitutas[str(fecha)] = st.selectbox(
            f"Sustituta para el jueves {fecha}",
            ["Laury", "Perla", "Jelianys", "Desire"],
            key=str(fecha)
        )

    # 🚀 Botón único para calcular
    if st.button("Calcular Comisiones"):
        df_vendedores, df_redes, df_resumen, df_totales = calcular_comisiones("temp.xlsx", sustitutas=sustitutas)

        st.subheader("📌 Detalle por Vendedor")
        st.dataframe(df_vendedores)

        st.subheader("📌 Detalle Redes Sociales")
        st.dataframe(df_redes)

        st.subheader("📌 Resumen Especial")
        st.dataframe(df_resumen)

        st.subheader("📌 Totales Combinados")
        st.dataframe(df_totales)

        # ======================
        # 📥 Exportar a Excel
        # ======================
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"comisiones_semanales_{timestamp}.xlsx"

        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            df_vendedores.to_excel(writer, sheet_name="Detalle Vendedor", index=False)
            df_redes.to_excel(writer, sheet_name="Detalle Redes", index=False)
            df_resumen.to_excel(writer, sheet_name="Resumen Especial", index=False)
            df_totales.to_excel(writer, sheet_name="Totales Combinados", index=False)

        with open(output_file, "rb") as f:
            st.download_button("⬇ Descargar Excel con Comisiones", f, file_name=output_file)
