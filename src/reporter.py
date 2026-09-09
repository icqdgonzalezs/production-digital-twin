"""Generación de informes profesionales: dashboard HTML, PNG resumen, Excel."""
from __future__ import annotations

from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.subplots as sp

from src.bottleneck import compute_cp_cpk
from src.exceptions import ReporterError
from src.logging_config import get_logger
from src.models import ReplicationResult

logger = get_logger(__name__)

# Paleta corporativa profesional
COLOR_OEE = "#264653"  # azul acero oscuro (gráfico 1: OEE por estación)
COLOR_DIST = "#2a9d8f"  # verde azulado (gráfico 2: distribución)
COLOR_UTIL = "#7f7f7f"  # gris medio
COLOR_THROUGHPUT = "#2ca02c"  # verde apagado
HEATMAP_SCALE = [[0, "#f3e8f7"], [1, "#6a4c93"]]  # púrpura (gráfico 3: heatmap)
COLOR_WORK = "#1f77b4"
COLOR_FAIL = "#d62728"
COLOR_BLOCK = "#ff7f0e"
COLOR_STARVE = "#7f7f7f"
COLOR_CP = "#9467bd"
COLOR_CPK = "#17becf"
COLOR_WORLDCLASS = "#e63946"  # rojo, línea de referencia World-Class OEE


# ---------------------------------------------------------------------------
# Dashboard HTML interactivo
# ---------------------------------------------------------------------------

def generate_dashboard(
    results: List[ReplicationResult], config, output_path: str = "reports/dashboard.html"
) -> None:
    """Genera el dashboard HTML interactivo y su captura PNG estática.

    Args:
        results: Resultados de todas las réplicas Monte Carlo.
        config: Configuración de la línea (dict con 'stations' y 'simulation').
        output_path: Ruta donde guardar el HTML del dashboard.
    """
    stations_ids = [m.station_id for m in results[0].station_metrics]
    station_names = {s.id: s.name for s in config["stations"]}

    df_oee = _build_oee_dataframe(results, stations_ids)
    avg_oee, avg_util = _compute_station_averages(results, stations_ids, df_oee)
    overall_oee_avg = float(np.mean(list(avg_oee.values())))
    bottleneck_sid = min(avg_oee, key=avg_oee.get)

    fig1 = _build_oee_bar_figure(df_oee, stations_ids, bottleneck_sid)
    fig2 = _build_oee_distribution_figure(df_oee, stations_ids)
    fig3 = _build_utilization_heatmap_figure(stations_ids, avg_util)
    fig4 = _build_time_balance_figure(results[-1])

    dash = _compose_dashboard(
        fig1, fig2, fig3, fig4,
        stations_ids=stations_ids,
        station_names=station_names,
        overall_oee_avg=overall_oee_avg,
        bottleneck_sid=bottleneck_sid,
        n_reps=len(results),
        config=config,
    )

    dash.write_html(output_path, include_plotlyjs="cdn")
    logger.info(
        "dashboard_html_generated",
        extra={"output_path": output_path, "artifact": "dashboard_html", "overall_oee": overall_oee_avg},
    )

    _export_dashboard_png(dash, output_path)


def _build_oee_dataframe(results: List[ReplicationResult], stations_ids: List[str]) -> pd.DataFrame:
    """Construye un DataFrame de OEE por réplica y estación."""
    return pd.DataFrame(
        [{"Réplica": r.replication, **{m.station_id: m.oee for m in r.station_metrics}} for r in results]
    )


def _compute_station_averages(
    results: List[ReplicationResult], stations_ids: List[str], df_oee: pd.DataFrame
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Calcula OEE y utilización promedio por estación, a través de réplicas."""
    avg_oee: Dict[str, float] = {}
    avg_util: Dict[str, float] = {}
    for sid in stations_ids:
        avg_oee[sid] = df_oee[sid].mean()
        utils = [m.utilization for r in results for m in r.station_metrics if m.station_id == sid]
        avg_util[sid] = float(np.mean(utils))
    return avg_oee, avg_util


def _build_oee_bar_figure(df_oee: pd.DataFrame, stations_ids: List[str], bottleneck_sid: str) -> go.Figure:
    """Gráfico 1: OEE por estación (barras + IC 95% + línea World-Class)."""
    fig = go.Figure()
    for sid in stations_ids:
        vals = df_oee[sid].dropna()
        mean, std, n = vals.mean(), vals.std(), len(vals)
        ci = 1.96 * std / np.sqrt(n) if n > 0 else 0
        is_bottleneck = sid == bottleneck_sid
        bar_color = COLOR_FAIL if is_bottleneck else COLOR_OEE
        label = f"⚠ {mean:.1%}" if is_bottleneck else f"{mean:.1%}"
        fig.add_trace(
            go.Bar(
                x=[sid],
                y=[mean],
                error_y=dict(type="data", array=[ci], visible=True, thickness=1.2, width=3),
                marker=dict(color=bar_color, line=dict(width=0)),
                name=sid,
                showlegend=False,
                text=[label],
                textposition="outside",
                textfont=dict(size=11, color="#333", family="Arial"),
            )
        )
    fig.add_hline(
        y=0.85,
        line_dash="dash",
        line_color=COLOR_WORLDCLASS,
        line_width=1.3,
        annotation_text="World-Class OEE (85%)",
        annotation_position="top left",
        annotation_font=dict(size=9, color=COLOR_WORLDCLASS),
    )
    fig.update_layout(
        title=dict(text="OEE Promedio por Estación", font=dict(size=13)),
        yaxis_title="OEE",
        yaxis=dict(tickformat=",.0%", range=[0, 1.0]),
        template="plotly_white",
        showlegend=False,
        height=320,
        margin=dict(l=40, r=20, t=35, b=30),
    )
    return fig


def _build_oee_distribution_figure(df_oee: pd.DataFrame, stations_ids: List[str]) -> go.Figure:
    """Gráfico 2: Distribución del OEE (boxplot) por estación."""
    fig = go.Figure()
    for sid in stations_ids:
        fig.add_trace(
            go.Box(
                y=df_oee[sid], name=sid, marker_color=COLOR_DIST, boxmean="sd", line=dict(width=1.2), showlegend=False
            )
        )
    fig.update_layout(
        title=dict(text="Distribución del OEE", font=dict(size=13)),
        yaxis_title="OEE",
        yaxis=dict(tickformat=",.0%"),
        template="plotly_white",
        showlegend=False,
        height=320,
        margin=dict(l=40, r=20, t=35, b=30),
    )
    return fig


def _build_utilization_heatmap_figure(stations_ids: List[str], avg_util: Dict[str, float]) -> go.Figure:
    """Gráfico 3: Mapa de calor de utilización promedio."""
    fig = go.Figure(
        data=go.Heatmap(
            z=[list(avg_util.values())],
            x=stations_ids,
            y=["Utilización"],
            colorscale=HEATMAP_SCALE,
            text=[[f"{v:.1%}" for v in avg_util.values()]],
            texttemplate="%{text}",
            textfont=dict(color="white", size=13),
            showscale=False,
        )
    )
    fig.update_layout(
        title=dict(text="Mapa de Calor de Utilización", font=dict(size=13)),
        template="plotly_white",
        height=180,
        margin=dict(l=40, r=20, t=35, b=20),
    )
    return fig


def _build_time_balance_figure(last_rep: ReplicationResult) -> go.Figure:
    """Gráfico 4: Balance de tiempos en % (última réplica)."""
    time_data = []
    for m in last_rep.station_metrics:
        total = m.total_time
        time_data.append(
            {
                "Estación": m.station_id,
                "Trabajo": m.working_time / total,
                "Fallo": m.downtime / total,
                "Bloqueo": m.blocked_time / total,
                "Inanición": m.starved_time / total,
            }
        )
    df_time = pd.DataFrame(time_data)
    fig = go.Figure(
        data=[
            go.Bar(name="Trabajo", x=df_time["Estación"], y=df_time["Trabajo"], marker_color=COLOR_WORK),
            go.Bar(name="Fallo", x=df_time["Estación"], y=df_time["Fallo"], marker_color=COLOR_FAIL),
            go.Bar(name="Bloqueo", x=df_time["Estación"], y=df_time["Bloqueo"], marker_color=COLOR_BLOCK),
            go.Bar(name="Inanición", x=df_time["Estación"], y=df_time["Inanición"], marker_color=COLOR_STARVE),
        ]
    )
    fig.update_layout(
        title=dict(text="Balance de Tiempos (%, última réplica)", font=dict(size=13)),
        yaxis_title="% del tiempo",
        yaxis=dict(tickformat=",.0%"),
        barmode="stack",
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, font=dict(size=9)),
        height=320,
        margin=dict(l=40, r=20, t=45, b=30),
    )
    return fig


def _compose_dashboard(
    fig1: go.Figure,
    fig2: go.Figure,
    fig3: go.Figure,
    fig4: go.Figure,
    *,
    stations_ids: List[str],
    station_names: Dict[str, str],
    overall_oee_avg: float,
    bottleneck_sid: str,
    n_reps: int,
    config,
) -> go.Figure:
    """Ensambla los cuatro gráficos individuales en un único dashboard 2x2."""
    axis_labels = [f"{sid}<br>{station_names.get(sid, sid)}" for sid in stations_ids]
    n_stations = len(stations_ids)

    dash = sp.make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "OEE Promedio por Estación",
            "Distribución del OEE",
            "Mapa de Calor de Utilización",
            "Balance de Tiempos (%)",
        ),
        specs=[[{"type": "bar"}, {"type": "box"}], [{"type": "heatmap"}, {"type": "bar"}]],
        vertical_spacing=0.22,
        horizontal_spacing=0.09,
    )
    for trace in fig1.data:
        dash.add_trace(trace, row=1, col=1)
    for trace in fig2.data:
        dash.add_trace(trace, row=1, col=2)
    for trace in fig3.data:
        dash.add_trace(trace, row=2, col=1)
    for trace in fig4.data:
        dash.add_trace(trace, row=2, col=2)

    dash.add_hline(y=0.85, line_dash="dash", line_color=COLOR_WORLDCLASS, line_width=1.2, row=1, col=1)

    for row, col in [(1, 1), (1, 2), (2, 1), (2, 2)]:
        dash.update_xaxes(tickmode="array", tickvals=stations_ids, ticktext=axis_labels, row=row, col=col)
    dash.update_yaxes(tickformat=",.0%", row=1, col=1)
    dash.update_yaxes(tickformat=",.0%", row=1, col=2)
    dash.update_yaxes(tickformat=",.0%", row=2, col=2)

    dash.update_layout(
        title=dict(
            text=(
                f"<b>Dashboard de Simulación – Línea de Envasado</b><br>"
                f'<span style="font-size:12px;color:#666">OEE Global: {overall_oee_avg:.1%}'
                f" &nbsp;·&nbsp; {n_stations} Estaciones &nbsp;·&nbsp; {n_reps} Réplicas</span>"
            ),
            x=0.5,
            y=0.97,
            font=dict(size=17, color="#222"),
        ),
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.08, xanchor="center", x=0.5, font=dict(size=10)),
        height=880,
        width=1050,
        margin=dict(l=40, r=20, t=110, b=175),
        font=dict(family="Arial, sans-serif"),
    )

    duration_h = config["simulation"]["duration_min"] / 60
    dash.add_annotation(
        text=(
            f"Simulación Monte Carlo · n={n_reps} réplicas · "
            f"Turno de {duration_h:.0f}h · Intervalos de confianza 95% · "
            f"⚠ Cuello de botella: {station_names.get(bottleneck_sid, bottleneck_sid)}"
        ),
        xref="paper",
        yref="paper",
        x=0.5,
        y=-0.19,
        showarrow=False,
        font=dict(size=9.5, color="#888"),
        xanchor="center",
    )
    return dash


def _export_dashboard_png(dash: go.Figure, output_path: str) -> None:
    """Exporta el dashboard también como PNG estático, listo para el README.

    Un fallo aquí (típicamente por falta de 'kaleido') no invalida el HTML
    ya generado, por eso se registra como advertencia recuperable en lugar
    de abortar toda la generación de reportes.

    Raises:
        ReporterError: Si falla la exportación del PNG. `recoverable=True`
            indica al llamador que puede registrar y continuar.
    """
    png_path = output_path.replace(".html", "_static.png")
    try:
        dash.write_image(png_path, width=1050, height=880, scale=2)
    except (RuntimeError, ValueError, OSError) as exc:
        raise ReporterError(
            f"No se pudo generar el PNG estatico del dashboard en {png_path}. "
            f"Verifica que 'kaleido' este instalado (pip install -U kaleido). Detalle: {exc}",
            artifact="dashboard_png",
            recoverable=True,
        ) from exc
    else:
        logger.info(
            "dashboard_png_generated",
            extra={"output_path": png_path, "artifact": "dashboard_png"},
        )


# ---------------------------------------------------------------------------
# Resumen ejecutivo en PNG (Matplotlib)
# ---------------------------------------------------------------------------

def generate_summary_png(
    results: List[ReplicationResult], config, output_path: str = "reports/summary.png"
) -> None:
    """Genera un resumen ejecutivo en PNG con estilo profesional y limpio.

    Args:
        results: Resultados de todas las réplicas Monte Carlo.
        config: Configuración de la línea.
        output_path: Ruta donde guardar el PNG resumen.

    Raises:
        ReporterError: Si falla la escritura del archivo PNG en disco.
    """
    _apply_matplotlib_style()
    stations_ids = [m.station_id for m in results[0].station_metrics]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    _plot_oee_summary(axes[0, 0], results, stations_ids)
    _plot_utilization_summary(axes[0, 1], results, stations_ids)
    _plot_throughput_summary(axes[1, 0], results, stations_ids)
    _plot_capability_summary(axes[1, 1], results, config)

    plt.tight_layout(pad=2.0)
    try:
        fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white", edgecolor="none")
    except OSError as exc:
        raise ReporterError(
            f"No se pudo guardar el resumen PNG en {output_path}. Detalle: {exc}",
            artifact="summary_png",
            recoverable=True,
        ) from exc
    finally:
        plt.close(fig)

    logger.info("summary_png_generated", extra={"output_path": output_path, "artifact": "summary_png"})


def _apply_matplotlib_style() -> None:
    plt.style.use("ggplot")
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.labelcolor": "#333333",
            "xtick.color": "#333333",
            "ytick.color": "#333333",
            "axes.edgecolor": "#cccccc",
            "axes.grid": True,
            "grid.alpha": 0.3,
            "grid.color": "#cccccc",
            "figure.facecolor": "white",
        }
    )


def _plot_oee_summary(ax, results: List[ReplicationResult], stations_ids: List[str]) -> None:
    oee_means, oee_cis = {}, {}
    for sid in stations_ids:
        vals = [m.oee for r in results for m in r.station_metrics if m.station_id == sid]
        oee_means[sid] = np.mean(vals)
        oee_cis[sid] = 1.96 * np.std(vals) / np.sqrt(len(vals))

    bars = ax.bar(
        stations_ids,
        [oee_means[s] for s in stations_ids],
        yerr=[oee_cis[s] for s in stations_ids],
        capsize=4,
        color=COLOR_OEE,
        edgecolor="white",
        linewidth=0.8,
    )
    ax.set_title("OEE Promedio por Estación")
    ax.set_ylabel("OEE")
    ax.set_ylim(0, 1.08)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.0, height + 0.02, f"{height:.1%}", ha="center", va="bottom", fontsize=8, color="black")


def _plot_utilization_summary(ax, results: List[ReplicationResult], stations_ids: List[str]) -> None:
    utils = {
        sid: np.mean([m.utilization for r in results for m in r.station_metrics if m.station_id == sid])
        for sid in stations_ids
    }
    bars = ax.bar(stations_ids, [utils[s] for s in stations_ids], color=COLOR_UTIL, edgecolor="white", linewidth=0.8)
    ax.set_title("Utilización Media")
    ax.set_ylabel("Utilización")
    ax.set_ylim(0, 1.08)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.0, height + 0.02, f"{height:.1%}", ha="center", va="bottom", fontsize=8, color="black")


def _plot_throughput_summary(ax, results: List[ReplicationResult], stations_ids: List[str]) -> None:
    thr = {
        sid: np.mean([m.throughput for r in results for m in r.station_metrics if m.station_id == sid])
        for sid in stations_ids
    }
    bars = ax.bar(stations_ids, [thr[s] for s in stations_ids], color=COLOR_THROUGHPUT, edgecolor="white", linewidth=0.8)
    ax.set_title("Throughput Medio (u/min)")
    ax.set_ylabel("Unidades/min")
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.0, height + 0.1, f"{height:.1f}", ha="center", va="bottom", fontsize=8, color="black")


def _plot_capability_summary(ax, results: List[ReplicationResult], config) -> None:
    cp_vals, cpk_vals, labels = [], [], []
    for r in results[:5]:
        m = r.station_metrics[0]
        cfg = config["stations"][0]
        cp, cpk = compute_cp_cpk(m.cycle_times, cfg.cycle_time_lsl, cfg.cycle_time_usl)
        if cp is not None:
            cp_vals.append(cp)
            cpk_vals.append(cpk)
            labels.append(f"R{r.replication}")

    if labels:
        x = np.arange(len(labels))
        width = 0.30
        ax.bar(x - width / 2, cp_vals, width, label="Cp", color=COLOR_CP, edgecolor="white")
        ax.bar(x + width / 2, cpk_vals, width, label="Cpk", color=COLOR_CPK, edgecolor="white")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=0, fontsize=8)
        ax.legend(fontsize=8, loc="upper right")

    ax.set_title("Cp / Cpk (Estación 1)")
    ax.set_ylabel("Índice")
    ax.axhline(y=1.33, color="red", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.text(0, 1.33, "1.33", fontsize=7, color="red", va="bottom")


# ---------------------------------------------------------------------------
# Reporte Excel multihoja
# ---------------------------------------------------------------------------

def generate_excel_report(
    results: List[ReplicationResult], config, output_path: str = "reports/report.xlsx"
) -> None:
    """Genera un libro Excel multihoja con datos numéricos de la simulación.

    Args:
        results: Resultados de todas las réplicas Monte Carlo.
        config: Configuración de la línea (no usada directamente hoy, se
            mantiene en la firma por consistencia con las demás funciones
            de este módulo y para futuras hojas que dependan de ella).
        output_path: Ruta donde guardar el archivo .xlsx.

    Raises:
        ReporterError: Si falla la escritura del archivo Excel en disco.
    """
    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            _write_summary_sheet(writer, results)
            _write_detail_sheet(writer, results[-1])
            _write_bottleneck_sheet(writer, results)
    except OSError as exc:
        raise ReporterError(
            f"No se pudo escribir el reporte Excel en {output_path}. Detalle: {exc}",
            artifact="excel_report",
            recoverable=True,
        ) from exc

    logger.info("excel_report_generated", extra={"output_path": output_path, "artifact": "excel_report"})


def _write_summary_sheet(writer: pd.ExcelWriter, results: List[ReplicationResult]) -> None:
    summary_rows = []
    for r in results:
        row = {"Réplica": r.replication, "OEE Global": r.overall_oee}
        for m in r.station_metrics:
            row[f"{m.station_id}_OEE"] = m.oee
            row[f"{m.station_id}_Util"] = m.utilization
        summary_rows.append(row)
    pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Resumen", index=False)


def _write_detail_sheet(writer: pd.ExcelWriter, last_rep: ReplicationResult) -> None:
    detail_rows = [
        {
            "Estación": m.station_id,
            "Trabajo (min)": m.working_time,
            "Fallo (min)": m.downtime,
            "Bloqueo (min)": m.blocked_time,
            "Inanición (min)": m.starved_time,
            "Unidades Buenas": m.good_units,
            "Disponibilidad": m.availability,
            "Rendimiento": m.performance,
            "Calidad": m.quality,
            "OEE": m.oee,
        }
        for m in last_rep.station_metrics
    ]
    pd.DataFrame(detail_rows).to_excel(writer, sheet_name="Detalle_Última_Réplica", index=False)


def _write_bottleneck_sheet(writer: pd.ExcelWriter, results: List[ReplicationResult]) -> None:
    bottle_rows = []
    for r in results:
        for b in r.bottlenecks[:3]:
            bottle_rows.append(
                {
                    "Réplica": r.replication,
                    "Estación": b.station_id,
                    "Utilización": b.utilization,
                    "Throughput": b.throughput,
                    "Score Compuesto": b.composite_score,
                }
            )
    pd.DataFrame(bottle_rows).to_excel(writer, sheet_name="Cuellos_Botella", index=False)