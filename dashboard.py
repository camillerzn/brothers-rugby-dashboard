import pandas as pd
import numpy as np
from dash import Dash, dcc, html, Input, Output, dash_table
import plotly.graph_objects as go
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import dash_auth
import os
import json

COULEURS = {
    "bleu":  "#4A90D9",
    "noir":  "#0A0A0A",
    "blanc": "#FFFFFF",
    "fonce": "#0D1B2A",
    "gris":  "#4A4A6A",
}

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def load_data():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        creds_info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(
            os.path.join(os.path.dirname(__file__), "credentials.json"), scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1thDPDieTXxL7qlnvx5BtJShPZmoON4e6KCs8uALK1-0/edit?gid=0#gid=0")
    worksheet = sheet.get_worksheet(0)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True)
    df = df.sort_values(["player", "date"]).reset_index(drop=True)
    for col in ["TD", "HSR", "SD", "top_Speed", "accel_min", "decel_min"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df = load_data()
players = sorted(df["player"].unique())
positions = sorted(df["position"].unique())
session_types = sorted(df["type"].unique())

app = Dash(__name__, title="Brothers Rugby Dashboard")
server = app.server

VALID_USERS = {
    "admin": "brothers2026",
}

auth = dash_auth.BasicAuth(app, VALID_USERS)

app.layout = html.Div(style={
    "backgroundColor": COULEURS["noir"],
    "minHeight": "100vh",
    "fontFamily": "sans-serif",
    "color": COULEURS["blanc"],
    "padding": "24px",
    "maxWidth": "1400px",
    "margin": "0 auto"
}, children=[

    html.H1("Brothers Rugby Dashboard", style={
        "color": COULEURS["bleu"],
        "fontSize": "28px",
        "marginBottom": "24px"
    }),

    html.Div(style={
        "display": "flex",
        "gap": "24px",
        "marginBottom": "24px",
        "flexWrap": "wrap"
    }, children=[

        html.Div([
            html.Label("Player", style={"color": COULEURS["gris"]}),
            dcc.Dropdown(
                id="filtre-player",
                options=[{"label": p, "value": p} for p in players],
                multi=True,
                placeholder="All players",
                style={"color": "#000", "minWidth": "200px"}
            ),
        ]),

        html.Div([
            html.Label("Position", style={"color": COULEURS["gris"]}),
            dcc.Dropdown(
                id="filtre-position",
                options=[{"label": p, "value": p} for p in positions],
                multi=True,
                placeholder="All positions",
                style={"color": "#000", "minWidth": "200px"}
            ),
        ]),

        html.Div([
            html.Label("Session type", style={"color": COULEURS["gris"]}),
            dcc.Dropdown(
                id="filtre-type",
                options=[{"label": t, "value": t} for t in session_types],
                multi=True,
                placeholder="All types",
                style={"color": "#000", "minWidth": "200px"}
            ),
        ]),

        html.Div([
            html.Label("Period", style={"color": COULEURS["gris"]}),
            dcc.DatePickerRange(
                id="filtre-date",
                min_date_allowed=df["date"].min(),
                max_date_allowed=df["date"].max(),
                start_date=df["date"].min(),
                end_date=df["date"].max(),
                display_format="DD/MM/YYYY",
            ),
        ]),

    ]),

    html.Div(id="kpis", style={
        "display": "grid",
        "gridTemplateColumns": "repeat(6, 1fr)",
        "gap": "12px",
        "marginBottom": "24px"
    }),

    html.Div(id="graphs", style={
        "display": "grid",
        "gridTemplateColumns": "1fr 1fr",
        "gap": "16px",
        "marginTop": "24px"
    }),

])

@app.callback(
    Output("kpis", "children"),
    Output("graphs", "children"),
    Input("filtre-player", "value"),
    Input("filtre-position", "value"),
    Input("filtre-type", "value"),
    Input("filtre-date", "start_date"),
    Input("filtre-date", "end_date"),
)
def update(players_sel, positions_sel, types_sel, start_date, end_date):
    dff = df.copy()

    if players_sel:
        dff = dff[dff["player"].isin(players_sel)]
    if positions_sel:
        dff = dff[dff["position"].isin(positions_sel)]
    if types_sel:
        dff = dff[dff["type"].isin(types_sel)]
    if start_date and end_date:
        dff = dff[(dff["date"] >= start_date) & (dff["date"] <= end_date)]

    def kpi_card(label, valeur, couleur=COULEURS["bleu"]):
        return html.Div(style={
            "backgroundColor": COULEURS["fonce"],
            "borderRadius": "12px",
            "padding": "16px",
            "textAlign": "center",
            "border": "1px solid " + COULEURS["gris"]
        }, children=[
            html.P(label, style={"margin": 0, "fontSize": "11px", "color": COULEURS["gris"]}),
            html.P(str(valeur), style={"margin": "6px 0 0", "fontSize": "22px", "fontWeight": "700", "color": couleur}),
        ])

    def make_graph(col, label, couleur):
        fig = go.Figure()
        for player in dff["player"].unique():
            d = dff[dff["player"] == player].sort_values("date")
            fig.add_trace(go.Bar(
                x=d["date"], y=d[col], name=player,
            ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=COULEURS["blanc"]),
            margin=dict(l=40, r=20, t=40, b=40),
            title=dict(text=label, font=dict(color=couleur)),
            xaxis=dict(gridcolor=COULEURS["gris"]),
            yaxis=dict(gridcolor=COULEURS["gris"]),
            legend=dict(orientation="h", y=-0.2),
            barmode="group",
        )
        return html.Div(style={
            "backgroundColor": COULEURS["fonce"],
            "borderRadius": "12px",
            "padding": "16px",
            "border": "1px solid " + COULEURS["gris"]
        }, children=[dcc.Graph(figure=fig, style={"height": "400px"})])

    td  = round(dff["TD"].mean(), 0) if len(dff) else 0
    hsr = round(dff["HSR"].mean(), 0) if len(dff) else 0
    sd  = round(dff["SD"].mean(), 0) if len(dff) else 0
    ts  = round(dff["top_Speed"].mean(), 2) if len(dff) else 0
    am  = round(dff["accel_min"].mean(), 2) if len(dff) else 0
    dm  = round(dff["decel_min"].mean(), 2) if len(dff) else 0

    kpis = [
        kpi_card("Total Distance (m)", int(td)),
        kpi_card("HSR (m)", int(hsr), "#4ECDC4"),
        kpi_card("Sprint Distance (m)", int(sd), "#FFE66D"),
        kpi_card("Top Speed (m/s)", ts, "#FF6B35"),
        kpi_card("Accel/min >4m/s2", am, "#C77DFF"),
        kpi_card("Decel/min >4m/s2", dm, "#FF6B6B"),
    ]

    graphs = [
        make_graph("TD", "Total Distance (m)", COULEURS["bleu"]),
        make_graph("HSR", "HSR (m)", "#4ECDC4"),
        make_graph("SD", "Sprint Distance (m)", "#FFE66D"),
        make_graph("top_Speed", "Top Speed (m/s)", "#FF6B35"),
        make_graph("accel_min", "Accel/min >4m/s2", "#C77DFF"),
        make_graph("decel_min", "Decel/min >4m/s2", "#FF6B6B"),
    ]

    return kpis, graphs

if __name__ == "__main__":
    app.run(debug=True)