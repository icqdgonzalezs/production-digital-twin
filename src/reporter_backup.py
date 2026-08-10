"""Generación de informes: dashboard HTML interactivo, PNG resumen, Excel."""
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.subplots as sp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import List
from src.models import ReplicationResult, StationMetrics, BottleneckInfo
from src.bottleneck import compute_cp_cpk

def generate_dashboard(results: List[ReplicationResult], config, output_path: str = "reports/dashboard.html"):
    """Crea dashboard interactivo con Plotly."""
    df_oee = pd.DataFrame([{
        'Réplica': r.replication,
        'OEE General': r.overall_oee,
        **{m.station_id: m.oee for m in r.station_metrics}
    } for r in results])

    stations_ids = [m.station_id for m in results[0].station_metrics]
    avg_oee = {sid: df_oee[sid].mean() for sid in stations_ids}
    avg_util = {}
    avg_throughput = {}
    for sid in stations_ids:
        vals_util = [m.utilization for r in results for m in r.station_metrics if m.station_id == sid]
        vals_th = [m.throughput for r in results for m in r.station_metrics if m.station_id == sid]
        avg_util[sid] = np.mean(vals_util)
        avg_throughput[sid] = np.mean(vals_th)

    fig1 = go.Figure()
    for sid in stations_ids:
        vals = df_oee[sid].dropna()
        mean = vals.mean()
        std = vals.std()
        n = len(vals)
        ci = 1.96 * std / np.sqrt(n) if n > 0 else 0
        fig1.add_trace(go.Bar(
            x=[sid], y=[mean],
            error_y=dict(type='data', array=[ci], visible=True),
            name=sid,
            text=[f'{mean:.3f} ± {ci:.3f}'], textposition='auto'
        ))
    fig1.update_layout(title='OEE por Estación (promedio e IC 95%)', yaxis_title='OEE', template='plotly_white')

    fig2 = go.Figure()
    for sid in stations_ids:
        fig2.add_trace(go.Violin(y=df_oee[sid], name=sid, box_visible=True, meanline_visible=True))
    fig2.update_layout(title='Distribución del OEE por Estación', yaxis_title='OEE', template='plotly_white')

    fig3 = go.Figure(data=go.Heatmap(
        z=[list(avg_util.values())],
        x=stations_ids,
        y=['Utilización'],
        colorscale='RdYlGn',
        text=[[f'{v:.2%}' for v in avg_util.values()]],
        texttemplate='%{text}'
    ))
    fig3.update_layout(title='Utilización Media por Estación', template='plotly_white', height=200)

    last_rep = results[-1]
    time_balance = []
    for m in last_rep.station_metrics:
        total = m.total_time
        time_balance.append({
            'Estación': m.station_id,
            'Trabajo': m.working_time,
            'Fallo': m.downtime,
            'Bloqueo': m.blocked_time,
            'Inanición': m.starved_time,
            'Otros': max(0, total - m.working_time - m.downtime - m.blocked_time - m.starved_time)
        })
    df_time = pd.DataFrame(time_balance)
    fig4 = go.Figure(data=[
        go.Bar(name='Trabajo', x=df_time['Estación'], y=df_time['Trabajo'], marker_color='#2ca02c'),
        go.Bar(name='Fallo', x=df_time['Estación'], y=df_time['Fallo'], marker_color='#d62728'),
        go.Bar(name='Bloqueo', x=df_time['Estación'], y=df_time['Bloqueo'], marker_color='#ff7f0e'),
        go.Bar(name='Inanición', x=df_time['Estación'], y=df_time['Inanición'], marker_color='#1f77b4')
    ])
    fig4.update_layout(title='Balance de Tiempos (última réplica)', yaxis_title='Minutos', barmode='stack', template='plotly_white')

    dash = sp.make_subplots(
        rows=2, cols=2,
        subplot_titles=('OEE promedio por Estación', 'Distribución OEE', 'Mapa de Calor Utilización', 'Balance de Tiempos'),
        specs=[[{"type": "bar"}, {"type": "violin"}],
               [{"type": "heatmap"}, {"type": "bar"}]],
        vertical_spacing=0.12,
        horizontal_spacing=0.10
    )
    for trace in fig1.data:
        dash.add_trace(trace, row=1, col=1)
    for trace in fig2.data:
        dash.add_trace(trace, row=1, col=2)
    for trace in fig3.data:
        dash.add_trace(trace, row=2, col=1)
    for trace in fig4.data:
        dash.add_trace(trace, row=2, col=2)

    dash.update_layout(
        title_text='Dashboard de Simulación – Línea de Envasado',
        title_x=0.5,
        template='plotly_white',
        showlegend=False,
        height=800
    )
    dash.write_html(output_path, include_plotlyjs='cdn')
    print(f"Dashboard HTML guardado en {output_path}")

def generate_summary_png(results: List[ReplicationResult], config, output_path: str = "reports/summary.png"):
    """Crea una figura PNG con resumen ejecutivo usando matplotlib (sin seaborn)."""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams.update({'font.size': 10, 'axes.titlesize': 12})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    stations_ids = [m.station_id for m in results[0].station_metrics]

    oee_means = {}
    oee_cis = {}
    for sid in stations_ids:
        vals = [r.overall_oee if sid == 'Total' else [m.oee for m in r.station_metrics if m.station_id == sid][0] for r in results]
        oee_means[sid] = np.mean(vals)
        oee_cis[sid] = 1.96 * np.std(vals) / np.sqrt(len(vals))
    ax = axes[0,0]
    ax.bar(stations_ids, [oee_means[s] for s in stations_ids],
           yerr=[oee_cis[s] for s in stations_ids], capsize=5, color='steelblue')
    ax.set_title('OEE Promedio por Estación')
    ax.set_ylabel('OEE')
    ax.set_ylim(0, 1)

    utils = {}
    for sid in stations_ids:
        utils[sid] = np.mean([m.utilization for r in results for m in r.station_metrics if m.station_id == sid])
    ax = axes[0,1]
    ax.bar(stations_ids, [utils[s] for s in stations_ids], color='goldenrod')
    ax.set_title('Utilización Media')
    ax.set_ylabel('Utilización')

    thr = {}
    for sid in stations_ids:
        thr[sid] = np.mean([m.throughput for r in results for m in r.station_metrics if m.station_id == sid])
    ax = axes[1,0]
    ax.bar(stations_ids, [thr[s] for s in stations_ids], color='seagreen')
    ax.set_title('Throughput Medio (u/min)')
    ax.set_ylabel('Unidades/min')

    cp_vals = []
    cpk_vals = []
    labels = []
    for r in results[:5]:
        for m in r.station_metrics[:1]:
            cfg_station = config['stations'][0]
            cp, cpk = compute_cp_cpk(m.cycle_times,
                                     cfg_station.cycle_time_lsl,
                                     cfg_station.cycle_time_usl)
            if cp is not None:
                cp_vals.append(cp)
                cpk_vals.append(cpk)
                labels.append(f'Rep {r.replication}')
    ax = axes[1,1]
    if labels:
        x = np.arange(len(labels))
        width = 0.35
        ax.bar(x - width/2, cp_vals, width, label='Cp', color='coral')
        ax.bar(x + width/2, cpk_vals, width, label='Cpk', color='mediumpurple')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45)
        ax.legend()
    ax.set_title('Cp / Cpk (Estación 1)')

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Resumen PNG guardado en {output_path}")

def generate_excel_report(results: List[ReplicationResult], config, output_path: str = "reports/report.xlsx"):
    """Genera un libro Excel con múltiples hojas."""
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        summary_rows = []
        for r in results:
            row = {'Réplica': r.replication, 'OEE Global': r.overall_oee}
            for m in r.station_metrics:
                row[f'{m.station_id}_OEE'] = m.oee
                row[f'{m.station_id}_Util'] = m.utilization
            summary_rows.append(row)
        df_summary = pd.DataFrame(summary_rows)
        df_summary.to_excel(writer, sheet_name='Resumen', index=False)

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
        pd.DataFrame(detail_rows).to_excel(writer, sheet_name='Detalle_Ultima_Rep', index=False)

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
