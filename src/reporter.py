"""Generación de informes profesionales: dashboard HTML, PNG resumen, Excel."""
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.subplots as sp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import List
from src.models import ReplicationResult
from src.bottleneck import compute_cp_cpk

# Paleta corporativa profesional
COLOR_OEE = '#264653'        # azul acero oscuro (gráfico 1: OEE por estación)
COLOR_DIST = '#2a9d8f'       # verde azulado (gráfico 2: distribución)
COLOR_UTIL = '#7f7f7f'       # gris medio
COLOR_THROUGHPUT = '#2ca02c' # verde apagado
HEATMAP_SCALE = [[0, '#f3e8f7'], [1, '#6a4c93']]  # púrpura (gráfico 3: heatmap)
COLOR_WORK = '#1f77b4'
COLOR_FAIL = '#d62728'
COLOR_BLOCK = '#ff7f0e'
COLOR_STARVE = '#7f7f7f'
COLOR_CP = '#9467bd'
COLOR_CPK = '#17becf'
COLOR_WORLDCLASS = '#e63946'  # rojo, línea de referencia World-Class OEE


def generate_dashboard(results: List[ReplicationResult], config, output_path: str = "reports/dashboard.html"):
    """Dashboard HTML interactivo con estilo profesional, listo para captura de pantalla."""
    stations_ids = [m.station_id for m in results[0].station_metrics]
    n_stations = len(stations_ids)
    n_reps = len(results)
    station_names = {s.id: s.name for s in config['stations']}
    axis_labels = [f'{sid}<br>{station_names.get(sid, sid)}' for sid in stations_ids]

    df_oee = pd.DataFrame([{
        'Réplica': r.replication,
        **{m.station_id: m.oee for m in r.station_metrics}
    } for r in results])

    avg_oee, avg_util = {}, {}
    for sid in stations_ids:
        avg_oee[sid] = df_oee[sid].mean()
        utils = [m.utilization for r in results for m in r.station_metrics if m.station_id == sid]
        avg_util[sid] = np.mean(utils)

    overall_oee_avg = np.mean(list(avg_oee.values()))
    bottleneck_sid = min(avg_oee, key=avg_oee.get)  # estación con menor OEE promedio

    # --- Gráfico 1: OEE por estación (barras + IC 95% + línea World-Class) ---
    fig1 = go.Figure()
    for sid in stations_ids:
        vals = df_oee[sid].dropna()
        mean, std, n = vals.mean(), vals.std(), len(vals)
        ci = 1.96 * std / np.sqrt(n) if n > 0 else 0
        is_bottleneck = (sid == bottleneck_sid)
        bar_color = COLOR_FAIL if is_bottleneck else COLOR_OEE
        label = f'⚠ {mean:.1%}' if is_bottleneck else f'{mean:.1%}'
        fig1.add_trace(go.Bar(
            x=[sid], y=[mean],
            error_y=dict(type='data', array=[ci], visible=True, thickness=1.2, width=3),
            marker=dict(color=bar_color, line=dict(width=0)),
            name=sid, showlegend=False,
            text=[label], textposition='outside',
            textfont=dict(size=11, color='#333', family='Arial')
        ))
    fig1.add_hline(y=0.85, line_dash='dash', line_color=COLOR_WORLDCLASS, line_width=1.3,
                    annotation_text='World-Class OEE (85%)', annotation_position='top left',
                    annotation_font=dict(size=9, color=COLOR_WORLDCLASS))
    fig1.update_layout(
        title=dict(text='OEE Promedio por Estación', font=dict(size=13)),
        yaxis_title='OEE', yaxis=dict(tickformat=',.0%', range=[0, 1.0]),
        template='plotly_white', showlegend=False,
        height=320, margin=dict(l=40, r=20, t=35, b=30)
    )

    # --- Gráfico 2: Distribución del OEE (boxplot) ---
    fig2 = go.Figure()
    for sid in stations_ids:
        fig2.add_trace(go.Box(
            y=df_oee[sid], name=sid, marker_color=COLOR_DIST,
            boxmean='sd', line=dict(width=1.2), showlegend=False
        ))
    fig2.update_layout(
        title=dict(text='Distribución del OEE', font=dict(size=13)),
        yaxis_title='OEE', yaxis=dict(tickformat=',.0%'),
        template='plotly_white', showlegend=False,
        height=320, margin=dict(l=40, r=20, t=35, b=30)
    )

    # --- Gráfico 3: Mapa de calor de utilización ---
    fig3 = go.Figure(data=go.Heatmap(
        z=[list(avg_util.values())], x=stations_ids, y=['Utilización'],
        colorscale=HEATMAP_SCALE,
        text=[[f'{v:.1%}' for v in avg_util.values()]],
        texttemplate='%{text}', textfont=dict(color='white', size=13),
        showscale=False
    ))
    fig3.update_layout(
        title=dict(text='Mapa de Calor de Utilización', font=dict(size=13)),
        template='plotly_white', height=180, margin=dict(l=40, r=20, t=35, b=20)
    )

    # --- Gráfico 4: Balance de tiempos en % (última réplica) ---
    last_rep = results[-1]
    time_data = []
    for m in last_rep.station_metrics:
        total = m.total_time
        time_data.append({
            'Estación': m.station_id,
            'Trabajo': m.working_time / total,
            'Fallo': m.downtime / total,
            'Bloqueo': m.blocked_time / total,
            'Inanición': m.starved_time / total
        })
    df_time = pd.DataFrame(time_data)
    fig4 = go.Figure(data=[
        go.Bar(name='Trabajo', x=df_time['Estación'], y=df_time['Trabajo'], marker_color=COLOR_WORK),
        go.Bar(name='Fallo', x=df_time['Estación'], y=df_time['Fallo'], marker_color=COLOR_FAIL),
        go.Bar(name='Bloqueo', x=df_time['Estación'], y=df_time['Bloqueo'], marker_color=COLOR_BLOCK),
        go.Bar(name='Inanición', x=df_time['Estación'], y=df_time['Inanición'], marker_color=COLOR_STARVE)
    ])
    fig4.update_layout(
        title=dict(text='Balance de Tiempos (%, última réplica)', font=dict(size=13)),
        yaxis_title='% del tiempo', yaxis=dict(tickformat=',.0%'),
        barmode='stack', template='plotly_white', showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='right', x=1, font=dict(size=9)),
        height=320, margin=dict(l=40, r=20, t=45, b=30)
    )

    # --- Componer dashboard ---
    dash = sp.make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'OEE Promedio por Estación', 'Distribución del OEE',
            'Mapa de Calor de Utilización', 'Balance de Tiempos (%)'
        ),
        specs=[[{"type": "bar"}, {"type": "box"}],
               [{"type": "heatmap"}, {"type": "bar"}]],
        vertical_spacing=0.22, horizontal_spacing=0.09
    )
    for trace in fig1.data:
        dash.add_trace(trace, row=1, col=1)
    for trace in fig2.data:
        dash.add_trace(trace, row=1, col=2)
    for trace in fig3.data:
        dash.add_trace(trace, row=2, col=1)
    for trace in fig4.data:
        dash.add_trace(trace, row=2, col=2)

    dash.add_hline(y=0.85, line_dash='dash', line_color=COLOR_WORLDCLASS,
                    line_width=1.2, row=1, col=1)

    dash.update_xaxes(tickmode='array', tickvals=stations_ids, ticktext=axis_labels, row=1, col=1)
    dash.update_xaxes(tickmode='array', tickvals=stations_ids, ticktext=axis_labels, row=1, col=2)
    dash.update_xaxes(tickmode='array', tickvals=stations_ids, ticktext=axis_labels, row=2, col=1)
    dash.update_xaxes(tickmode='array', tickvals=stations_ids, ticktext=axis_labels, row=2, col=2)
    dash.update_yaxes(tickformat=',.0%', row=1, col=1)
    dash.update_yaxes(tickformat=',.0%', row=1, col=2)
    dash.update_yaxes(tickformat=',.0%', row=2, col=2)

    dash.update_layout(
        title=dict(
            text=(f'<b>Dashboard de Simulación – Línea de Envasado</b><br>'
                  f'<span style="font-size:12px;color:#666">OEE Global: {overall_oee_avg:.1%}'
                  f' &nbsp;·&nbsp; {n_stations} Estaciones &nbsp;·&nbsp; {n_reps} Réplicas</span>'),
            x=0.5, y=0.97, font=dict(size=17, color='#222')
        ),
        template='plotly_white', showlegend=True,
        legend=dict(orientation='h', yanchor='top', y=-0.08, xanchor='center', x=0.5, font=dict(size=10)),
        height=880, width=1050,
        margin=dict(l=40, r=20, t=110, b=175),
        font=dict(family='Arial, sans-serif')
    )

    duration_h = config['simulation']['duration_min'] / 60
    dash.add_annotation(
        text=(f"Simulación Monte Carlo · n={n_reps} réplicas · "
              f"Turno de {duration_h:.0f}h · Intervalos de confianza 95% · "
              f"⚠ Cuello de botella: {station_names.get(bottleneck_sid, bottleneck_sid)}"),
        xref='paper', yref='paper', x=0.5, y=-0.19,
        showarrow=False, font=dict(size=9.5, color='#888'),
        xanchor='center'
    )
    dash.write_html(output_path, include_plotlyjs='cdn')
    print(f"Dashboard HTML guardado en {output_path}")

    # Exportar también como PNG nítido, listo para el README
    png_path = output_path.replace('.html', '_static.png')
    try:
        dash.write_image(png_path, width=1050, height=880, scale=2)
        print(f"Captura estática del dashboard guardada en {png_path}")
    except Exception as e:
        print(f"Aviso: no se pudo generar el PNG estático del dashboard ({e}). "
              f"Verifica que 'kaleido' esté instalado (pip install -U kaleido).")


def generate_summary_png(results: List[ReplicationResult], config, output_path: str = "reports/summary.png"):
    """Resumen ejecutivo en PNG con estilo profesional y limpio."""
    plt.style.use('ggplot')
    plt.rcParams.update({
        'font.size': 9,
        'axes.titlesize': 11,
        'axes.titleweight': 'bold',
        'axes.labelcolor': '#333333',
        'xtick.color': '#333333',
        'ytick.color': '#333333',
        'axes.edgecolor': '#cccccc',
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.color': '#cccccc',
        'figure.facecolor': 'white'
    })

    stations_ids = [m.station_id for m in results[0].station_metrics]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    oee_means = {}
    oee_cis = {}
    for sid in stations_ids:
        vals = []
        for r in results:
            for m in r.station_metrics:
                if m.station_id == sid:
                    vals.append(m.oee)
                    break
        oee_means[sid] = np.mean(vals)
        oee_cis[sid] = 1.96 * np.std(vals) / np.sqrt(len(vals))

    ax = axes[0,0]
    bars = ax.bar(stations_ids, [oee_means[s] for s in stations_ids],
                  yerr=[oee_cis[s] for s in stations_ids],
                  capsize=4, color=COLOR_OEE, edgecolor='white', linewidth=0.8)
    ax.set_title('OEE Promedio por Estación')
    ax.set_ylabel('OEE')
    ax.set_ylim(0, 1.08)
    for bar, sid in zip(bars, stations_ids):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{height:.1%}', ha='center', va='bottom', fontsize=8, color='black')

    utils = {}
    for sid in stations_ids:
        utils[sid] = np.mean([m.utilization for r in results for m in r.station_metrics if m.station_id == sid])
    ax = axes[0,1]
    bars = ax.bar(stations_ids, [utils[s] for s in stations_ids],
                  color=COLOR_UTIL, edgecolor='white', linewidth=0.8)
    ax.set_title('Utilización Media')
    ax.set_ylabel('Utilización')
    ax.set_ylim(0, 1.08)
    for bar, sid in zip(bars, stations_ids):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{height:.1%}', ha='center', va='bottom', fontsize=8, color='black')

    thr = {}
    for sid in stations_ids:
        thr[sid] = np.mean([m.throughput for r in results for m in r.station_metrics if m.station_id == sid])
    ax = axes[1,0]
    bars = ax.bar(stations_ids, [thr[s] for s in stations_ids],
                  color=COLOR_THROUGHPUT, edgecolor='white', linewidth=0.8)
    ax.set_title('Throughput Medio (u/min)')
    ax.set_ylabel('Unidades/min')
    for bar, sid in zip(bars, stations_ids):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.1f}', ha='center', va='bottom', fontsize=8, color='black')

    ax = axes[1,1]
    cp_vals = []
    cpk_vals = []
    labels = []
    for r in results[:5]:
        m = r.station_metrics[0]
        cfg = config['stations'][0]
        cp, cpk = compute_cp_cpk(m.cycle_times, cfg.cycle_time_lsl, cfg.cycle_time_usl)
        if cp is not None:
            cp_vals.append(cp)
            cpk_vals.append(cpk)
            labels.append(f'R{r.replication}')
    if labels:
        x = np.arange(len(labels))
        width = 0.30
        ax.bar(x - width/2, cp_vals, width, label='Cp', color=COLOR_CP, edgecolor='white')
        ax.bar(x + width/2, cpk_vals, width, label='Cpk', color=COLOR_CPK, edgecolor='white')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=0, fontsize=8)
        ax.legend(fontsize=8, loc='upper right')
    ax.set_title('Cp / Cpk (Estación 1)')
    ax.set_ylabel('Índice')
    ax.axhline(y=1.33, color='red', linestyle='--', linewidth=0.8, alpha=0.7)
    ax.text(0, 1.33, '1.33', fontsize=7, color='red', va='bottom')

    plt.tight_layout(pad=2.0)
    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    print(f"Resumen PNG guardado en {output_path}")


def generate_excel_report(results: List[ReplicationResult], config, output_path: str = "reports/report.xlsx"):
    """Libro Excel multihoja con datos numéricos."""
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        summary_rows = []
        for r in results:
            row = {'Réplica': r.replication, 'OEE Global': r.overall_oee}
            for m in r.station_metrics:
                row[f'{m.station_id}_OEE'] = m.oee
                row[f'{m.station_id}_Util'] = m.utilization
            summary_rows.append(row)
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Resumen', index=False)

        last = results[-1]
        detail_rows = []
        for m in last.station_metrics:
            detail_rows.append({
                'Estación': m.station_id,
                'Trabajo (min)': m.working_time,
                'Fallo (min)': m.downtime,
                'Bloqueo (min)': m.blocked_time,
                'Inanición (min)': m.starved_time,
                'Unidades Buenas': m.good_units,
                'Disponibilidad': m.availability,
                'Rendimiento': m.performance,
                'Calidad': m.quality,
                'OEE': m.oee
            })
        pd.DataFrame(detail_rows).to_excel(writer, sheet_name='Detalle_Última_Réplica', index=False)

        bottle_rows = []
        for r in results:
            for b in r.bottlenecks[:3]:
                bottle_rows.append({
                    'Réplica': r.replication,
                    'Estación': b.station_id,
                    'Utilización': b.utilization,
                    'Throughput': b.throughput,
                    'Score Compuesto': b.composite_score
                })
        pd.DataFrame(bottle_rows).to_excel(writer, sheet_name='Cuellos_Botella', index=False)

    print(f"Reporte Excel guardado en {output_path}")
