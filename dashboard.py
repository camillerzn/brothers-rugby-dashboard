import pandas as pd
import numpy as np
from dash import Dash, dcc, html, Input, Output, callback_context
import plotly.graph_objects as go
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import dash_auth
import os
import json
import base64
import tempfile
from weasyprint import HTML as WeasyHTML

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

POSITION_PAR_JOUEUR = {
    "D.Fraser":   "Forwards",
    "Tieli":      "Forwards",
    "W.Wilson":   "Forwards",
    "B.Hemps":    "Forwards",
    "Clifty":     "Forwards",
    "Leo":        "Forwards",
    "Remi":       "Forwards",
    "George":     "Forwards",
    "Noah":       "Forwards",
    "Fus":        "Forwards",
    "Jeremiah":   "Forwards",
    "Prass":      "Backs",
    "Della":      "Backs",
    "Athen":      "Backs",
    "Kaelan":     "Backs",
    "H.Grant":    "Backs",
    "G.Urquhart": "Backs",
    "Henry":      "Backs",
    "Guido":      "Backs",
}

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
    df["player"] = df["player"].str.replace("*", "", regex=False).str.strip()
    df["position"] = df["player"].map(POSITION_PAR_JOUEUR).fillna("Unknown")
    return df

df = load_data()
players = sorted(df["player"].unique())
positions = sorted(df["position"].unique())
session_types = sorted(df["type"].unique())

app = Dash(__name__, title="Brothers Rugby Dashboard")
server = app.server

VALID_USERS = {"admin": "brothers2026"}
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

    html.H3("Acute:Chronic Workload Ratio (7d / 28d)", style={
        "color": COULEURS["gris"],
        "fontSize": "13px",
        "marginBottom": "8px",
        "marginTop": "0"
    }),
    html.Div(id="kpis-acwr", style={
        "display": "grid",
        "gridTemplateColumns": "repeat(4, 1fr)",
        "gap": "12px",
        "marginBottom": "16px"
    }),

    html.H3("Session averages", style={
        "color": COULEURS["gris"],
        "fontSize": "13px",
        "marginBottom": "8px",
    }),
    html.Div(id="kpis", style={
        "display": "grid",
        "gridTemplateColumns": "repeat(6, 1fr)",
        "gap": "12px",
        "marginBottom": "24px"
    }),

    html.Div(style={"marginBottom": "16px", "display": "flex", "gap": "16px", "flexWrap": "wrap", "alignItems": "flex-end"}, children=[
        html.Div([
            html.Button(
                "Export Weekly Report (PDF)",
                id="btn-rapport",
                style={
                    "backgroundColor": COULEURS["bleu"],
                    "color": COULEURS["blanc"],
                    "border": "none",
                    "borderRadius": "8px",
                    "padding": "10px 20px",
                    "cursor": "pointer",
                    "fontSize": "14px",
                    "fontWeight": "600",
                }
            ),
            dcc.Download(id="download-rapport"),
        ]),
        html.Div([
            html.Label("Comparison Report — reference week", style={"color": COULEURS["gris"], "fontSize": "12px", "display": "block", "marginBottom": "6px"}),
            html.Div(style={"display": "flex", "gap": "12px", "alignItems": "center"}, children=[
                dcc.DatePickerSingle(
                    id="date-comparaison",
                    min_date_allowed=df["date"].min(),
                    max_date_allowed=df["date"].max(),
                    date=df["date"].max(),
                    display_format="DD/MM/YYYY",
                ),
                html.Button(
                    "Export Comparison Report (PDF)",
                    id="btn-comparaison",
                    style={
                        "backgroundColor": "#C77DFF",
                        "color": COULEURS["blanc"],
                        "border": "none",
                        "borderRadius": "8px",
                        "padding": "10px 20px",
                        "cursor": "pointer",
                        "fontSize": "14px",
                        "fontWeight": "600",
                    }
                ),
                dcc.Download(id="download-comparaison"),
            ]),
        ]),
    ]),

    html.Div(id="graphs", style={
        "display": "grid",
        "gridTemplateColumns": "1fr 1fr",
        "gap": "16px",
        "marginTop": "24px"
    }),
])

@app.callback(
    Output("kpis-acwr", "children"),
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

    dff_games = dff[dff["type"].isin(["Game 1st Half", "Game 2nd Half"])].copy()
    dff_training = dff[~dff["type"].isin(["Game 1st Half", "Game 2nd Half"])].copy()

    palette = px.colors.qualitative.Plotly
    tous_les_joueurs = sorted(dff["player"].unique())
    couleur_joueur = {player: palette[i % len(palette)] for i, player in enumerate(tous_les_joueurs)}

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

        for player in sorted(dff_training["player"].unique()):
            d = dff_training[dff_training["player"] == player].sort_values("date")
            fig.add_trace(go.Bar(
                x=d["date"], y=d[col],
                name=player,
                legendgroup=player,
                marker_color=couleur_joueur[player],
                showlegend=True,
            ))

        for player in sorted(dff_games["player"].unique()):
            d1 = dff_games[(dff_games["player"] == player) & (dff_games["type"] == "Game 1st Half")].sort_values("date")
            d2 = dff_games[(dff_games["player"] == player) & (dff_games["type"] == "Game 2nd Half")].sort_values("date")
            has_training = player in dff_training["player"].unique()
            fig.add_trace(go.Bar(
                x=d1["date"], y=d1[col],
                name=f"{player} 1st half",
                legendgroup=player,
                marker_color=couleur_joueur[player],
                opacity=1.0,
                marker_line=dict(color="white", width=2),
                showlegend=not has_training,
            ))
            fig.add_trace(go.Bar(
                x=d2["date"], y=d2[col],
                name=f"{player} 2nd half",
                legendgroup=player,
                marker_color=couleur_joueur[player],
                opacity=0.5,
                marker_line=dict(color="white", width=2),
                showlegend=False,
            ))

        moyenne_par_poste = (
            dff.groupby(["date", "position"])[col]
            .mean()
            .reset_index()
            .sort_values("date")
        )
        moyenne_par_poste[col] = (
            moyenne_par_poste.groupby("position")[col]
            .transform(lambda x: x.rolling(window=3, min_periods=1).mean())
        )

        couleurs_postes = {
            "Forwards": "#FF6B35",
            "Backs": "#4ECDC4",
        }

        for poste in sorted(dff["position"].unique()):
            d_poste = moyenne_par_poste[moyenne_par_poste["position"] == poste]
            fig.add_trace(go.Scatter(
                x=d_poste["date"],
                y=d_poste[col],
                name=f"Avg {poste}",
                mode="lines+markers",
                line=dict(width=2, dash="dash", color=couleurs_postes.get(poste, "white")),
                marker=dict(size=6),
                yaxis="y2",
            ))

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=COULEURS["blanc"]),
            margin=dict(l=40, r=60, t=40, b=40),
            title=dict(text=label, font=dict(color=couleur)),
            xaxis=dict(gridcolor=COULEURS["gris"]),
            yaxis=dict(gridcolor=COULEURS["gris"]),
            yaxis2=dict(
                overlaying="y",
                side="right",
                showgrid=False,
                title=dict(text="Avg by position", font=dict(color="white")),
                tickfont=dict(color="white"),
            ),
            legend=dict(orientation="h", y=-0.2),
            barmode="stack",
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

    today = dff["date"].max()
    aigu_window = today - pd.Timedelta(days=7)
    chronique_window = today - pd.Timedelta(days=28)

    def acwr(col):
        aigu = dff[dff["date"] >= aigu_window][col].mean()
        chronique = dff[dff["date"] >= chronique_window][col].mean()
        if chronique and chronique > 0:
            ratio = round(aigu / chronique, 2)
        else:
            ratio = 0
        if ratio < 0.8 or ratio > 1.3:
            c = "#FF6B6B"
        elif 0.8 <= ratio <= 1.1:
            c = "#4ECDC4"
        else:
            c = "#FFE66D"
        return ratio, c

    td_ratio, td_rc   = acwr("TD")
    hsr_ratio, hsr_rc = acwr("HSR")
    sd_ratio, sd_rc   = acwr("SD")
    ts_ratio, ts_rc   = acwr("top_Speed")

    kpis_acwr = [
        kpi_card("ACWR Total Distance", td_ratio, td_rc),
        kpi_card("ACWR HSR", hsr_ratio, hsr_rc),
        kpi_card("ACWR Sprint Distance", sd_ratio, sd_rc),
        kpi_card("ACWR Top Speed", ts_ratio, ts_rc),
    ]

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

    return kpis_acwr, kpis, graphs


@app.callback(
    Output("download-rapport", "data"),
    Input("btn-rapport", "n_clicks"),
    Input("filtre-player", "value"),
    Input("filtre-position", "value"),
    Input("filtre-type", "value"),
    Input("filtre-date", "start_date"),
    Input("filtre-date", "end_date"),
    prevent_initial_call=True,
)
def export_pdf(n_clicks, players_sel, positions_sel, types_sel, start_date, end_date):
    if not callback_context.triggered or callback_context.triggered[0]["prop_id"] != "btn-rapport.n_clicks":
        return None

    dff = df.copy()
    if players_sel:
        dff = dff[dff["player"].isin(players_sel)]
    if positions_sel:
        dff = dff[dff["position"].isin(positions_sel)]
    if types_sel:
        dff = dff[dff["type"].isin(types_sel)]
    if start_date and end_date:
        dff = dff[(dff["date"] >= start_date) & (dff["date"] <= end_date)]

    start_label = pd.to_datetime(start_date).strftime("%d/%m/%Y")
    end_label   = pd.to_datetime(end_date).strftime("%d/%m/%Y")

    def acwr_val(col):
        today = dff["date"].max()
        aigu = dff[dff["date"] >= today - pd.Timedelta(days=7)][col].mean()
        chronique = dff[dff["date"] >= today - pd.Timedelta(days=28)][col].mean()
        if chronique and chronique > 0:
            ratio = round(aigu / chronique, 2)
        else:
            ratio = 0
        if ratio < 0.8 or ratio > 1.3:
            color = "#FF6B6B"
        elif 0.8 <= ratio <= 1.1:
            color = "#4ECDC4"
        else:
            color = "#FFE66D"
        return ratio, color

    def zone_label(ratio):
        if ratio < 0.8:
            return "Under-load"
        elif ratio <= 1.1:
            return "Optimal"
        elif ratio <= 1.3:
            return "Caution"
        else:
            return "Overload"

    td_r, td_c   = acwr_val("TD")
    hsr_r, hsr_c = acwr_val("HSR")
    sd_r, sd_c   = acwr_val("SD")
    ts_r, ts_c   = acwr_val("top_Speed")

    team_rows = ""
    for col, label in [("TD", "Total Distance (m)"), ("HSR", "HSR (m)"),
                        ("SD", "Sprint Distance (m)"), ("top_Speed", "Top Speed (m/s)"),
                        ("accel_min", "Accel/min"), ("decel_min", "Decel/min")]:
        fwd = round(dff[dff["position"] == "Forwards"][col].mean(), 1)
        bck = round(dff[dff["position"] == "Backs"][col].mean(), 1)
        avg = round(dff[col].mean(), 1)
        team_rows += f"""
        <tr>
            <td>{label}</td>
            <td>{avg}</td>
            <td>{fwd}</td>
            <td>{bck}</td>
        </tr>"""

    acwr_rows = ""
    for label, ratio, color in [
        ("Total Distance", td_r, td_c),
        ("HSR", hsr_r, hsr_c),
        ("Sprint Distance", sd_r, sd_c),
        ("Top Speed", ts_r, ts_c),
    ]:
        acwr_rows += f"""
        <tr>
            <td>{label}</td>
            <td style="color:{color}; font-weight:700">{ratio}</td>
            <td style="color:{color}">{zone_label(ratio)}</td>
        </tr>"""

    player_cards = ""
    for player in sorted(dff["player"].unique()):
        dp = dff[dff["player"] == player]
        position = dp["position"].iloc[0]
        poste_avg = dff[dff["position"] == position]

        rows = ""
        for col, label in [("TD", "Total Distance (m)"), ("HSR", "HSR (m)"),
                            ("SD", "Sprint Distance (m)"), ("top_Speed", "Top Speed (m/s)"),
                            ("accel_min", "Accel/min"), ("decel_min", "Decel/min")]:
            val     = round(dp[col].mean(), 1)
            avg_pos = round(poste_avg[col].mean(), 1)
            diff    = round(val - avg_pos, 1)
            diff_color = "#2e7d32" if diff >= 0 else "#c62828"
            diff_str = f"+{diff}" if diff >= 0 else str(diff)
            rows += f"""
            <tr>
                <td>{label}</td>
                <td>{val}</td>
                <td>{avg_pos}</td>
                <td style="color:{diff_color}; font-weight:600">{diff_str}</td>
            </tr>"""

        player_cards += f"""
        <div class="player-card">
            <h3>{player} <span class="position-badge">{position}</span></h3>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Player avg</th>
                        <th>Position avg</th>
                        <th>Diff</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>"""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; background: #fff; color: #111; padding: 32px; font-size: 13px; }}
        h1 {{ color: #4A90D9; font-size: 22px; margin-bottom: 4px; }}
        h2 {{ color: #4A90D9; font-size: 16px; margin-top: 28px; border-bottom: 2px solid #4A90D9; padding-bottom: 4px; }}
        h3 {{ font-size: 14px; margin: 0 0 8px 0; }}
        .subtitle {{ color: #666; font-size: 12px; margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
        th {{ background: #4A90D9; color: white; padding: 8px; text-align: left; font-size: 12px; }}
        td {{ padding: 7px 8px; border-bottom: 1px solid #eee; }}
        tr:nth-child(even) {{ background: #f7f9fc; }}
        .position-badge {{ background: #4A90D9; color: white; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: normal; margin-left: 8px; }}
        .player-card {{ margin-bottom: 28px; page-break-inside: avoid; }}
    </style>
    </head>
    <body>
        <h1>Brothers Rugby — Weekly Report</h1>
        <p class="subtitle">Period: {start_label} → {end_label}</p>
        <h2>Team Summary</h2>
        <table>
            <thead><tr><th>Metric</th><th>Team avg</th><th>Forwards avg</th><th>Backs avg</th></tr></thead>
            <tbody>{team_rows}</tbody>
        </table>
        <h2>Acute:Chronic Workload Ratio</h2>
        <table>
            <thead><tr><th>Metric</th><th>Ratio</th><th>Zone</th></tr></thead>
            <tbody>{acwr_rows}</tbody>
        </table>
        <h2>Individual Player Reports</h2>
        {player_cards}
    </body>
    </html>
    """

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        WeasyHTML(string=html_content).write_pdf(f.name)
        with open(f.name, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()

    filename = f"brothers_rugby_{start_label.replace('/', '-')}_{end_label.replace('/', '-')}.pdf"
    return dcc.send_bytes(pdf_bytes, filename)


@app.callback(
    Output("download-comparaison", "data"),
    Input("btn-comparaison", "n_clicks"),
    Input("date-comparaison", "date"),
    prevent_initial_call=True,
)
def export_comparison_pdf(n_clicks, ref_date):
    if not callback_context.triggered or callback_context.triggered[0]["prop_id"] != "btn-comparaison.n_clicks":
        return None

    ref = pd.to_datetime(ref_date)

    def get_day(reference, weekday):
        days_ahead = weekday - reference.weekday()
        if days_ahead > 0:
            days_ahead -= 7
        return reference + pd.Timedelta(days=days_ahead)

    tue_this  = get_day(ref, 1)
    thu_this  = get_day(ref, 3)
    tue_prev  = tue_this - pd.Timedelta(weeks=1)
    thu_prev  = thu_this - pd.Timedelta(weeks=1)

    def get_session(date):
        return df[df["date"] == date].copy()

    d_tue_this = get_session(tue_this)
    d_thu_this = get_session(thu_this)
    d_tue_prev = get_session(tue_prev)
    d_thu_prev = get_session(thu_prev)

    metrics = [
        ("TD", "Total Distance (m)"),
        ("HSR", "HSR (m)"),
        ("SD", "Sprint Distance (m)"),
        ("top_Speed", "Top Speed (m/s)"),
        ("accel_min", "Accel/min"),
        ("decel_min", "Decel/min"),
    ]

    def build_session_table(d_this, d_prev, session_label, date_this, date_prev):
        if d_this.empty and d_prev.empty:
            return f"<p>No data found for {session_label}.</p>"

        all_players = sorted(set(d_this["player"].tolist() + d_prev["player"].tolist()))

        header = f"""
        <h3>{session_label} — {date_this.strftime('%d/%m/%Y')} vs {date_prev.strftime('%d/%m/%Y')}</h3>
        <table>
            <thead>
                <tr>
                    <th>Player</th>
                    <th>Position</th>
                    {''.join(f'<th>{label}<br><small>This week</small></th><th>{label}<br><small>Prev week</small></th><th>Diff</th>' for _, label in metrics)}
                </tr>
            </thead>
            <tbody>"""

        rows = ""
        for player in all_players:
            p_this = d_this[d_this["player"] == player]
            p_prev = d_prev[d_prev["player"] == player]
            position = POSITION_PAR_JOUEUR.get(player, "Unknown")

            cells = ""
            for col, _ in metrics:
                val_this = round(p_this[col].mean(), 1) if not p_this.empty else "-"
                val_prev = round(p_prev[col].mean(), 1) if not p_prev.empty else "-"

                if val_this != "-" and val_prev != "-":
                    diff = round(val_this - val_prev, 1)
                    diff_color = "#2e7d32" if diff >= 0 else "#c62828"
                    diff_str = f"+{diff}" if diff >= 0 else str(diff)
                else:
                    diff_color = "#666"
                    diff_str = "-"

                cells += f"""
                    <td>{val_this}</td>
                    <td>{val_prev}</td>
                    <td style="color:{diff_color}; font-weight:600">{diff_str}</td>"""

            rows += f"""
            <tr>
                <td><strong>{player}</strong></td>
                <td>{position}</td>
                {cells}
            </tr>"""

        return header + rows + "</tbody></table>"

    tuesday_table  = build_session_table(d_tue_this, d_tue_prev, "Tuesday", tue_this, tue_prev)
    thursday_table = build_session_table(d_thu_this, d_thu_prev, "Thursday", thu_this, thu_prev)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; background: #fff; color: #111; padding: 32px; font-size: 11px; }}
        h1 {{ color: #4A90D9; font-size: 20px; margin-bottom: 4px; }}
        h2 {{ color: #4A90D9; font-size: 15px; margin-top: 28px; border-bottom: 2px solid #4A90D9; padding-bottom: 4px; }}
        h3 {{ font-size: 13px; margin: 20px 0 8px 0; color: #333; }}
        .subtitle {{ color: #666; font-size: 11px; margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 10px; }}
        th {{ background: #4A90D9; color: white; padding: 6px 4px; text-align: center; font-size: 9px; }}
        td {{ padding: 5px 4px; border-bottom: 1px solid #eee; text-align: center; }}
        td:first-child, td:nth-child(2) {{ text-align: left; }}
        tr:nth-child(even) {{ background: #f7f9fc; }}
    </style>
    </head>
    <body>
        <h1>Brothers Rugby — Week Comparison Report</h1>
        <p class="subtitle">Reference week ending: {ref.strftime('%d/%m/%Y')}</p>
        <h2>Tuesday Session</h2>
        {tuesday_table}
        <h2>Thursday Session</h2>
        {thursday_table}
    </body>
    </html>
    """

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        WeasyHTML(string=html_content).write_pdf(f.name)
        with open(f.name, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()

    filename = f"brothers_rugby_comparison_{ref.strftime('%d-%m-%Y')}.pdf"
    return dcc.send_bytes(pdf_bytes, filename)


if __name__ == "__main__":
    app.run(debug=True)