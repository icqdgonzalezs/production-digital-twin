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
COLOR_OEE = '#1f77b4'        # azul marino
COLOR_UTIL = '#7f7f7f'       # gris medio
COLOR_THROUGHPUT = '#2ca02c' # verde apagado
COLOR_WORK = '#1f77b4'
COLOR_FAIL = '#d62728'
COLOR_BLOCK = '#ff7f0e'
COLOR_STARVE = '#7f7f7f'
COLOR_CP = '#9467bd'
COLOR_CPK = '#17becf'

def generate_dashboard(results: List[ReplicationResult], config, output_path: str = "reports/dashboard.html"):
    """Dashboard HTML interactivo con estilo profesional limpio."""
    # Datos base
    stations_ids = [m.station_id for m in results[0].station_metrics]
    n_stations = len(stations_ids)
    
    # DataFrame OEE
    df_oee = pd.DataFrame([{
        'Réplica': r.replication,
        **{m.station_id: m.oee for m in r.station_metrics}
    } for r in results])
    
    # Métricas agregadas
    avg_oee = {}
    avg_util = {}
    avg_th = {}
    for sid in stations_ids:
        vals_oee = df_oee[sid]
        avg_oee[sid] = vals_oee.mean()
        utils = [m.utilization for r in results for m in r.station_metrics if m.station_id == sid]
        ths = [m.throughput for r in results for m in r.station_metrics if m.station_id == sid]
        avg_util[sid] = np.mean(utils)
        avg_th[sid] = np.mean(ths)
    
    # --- Gráfico 1: OEE por estación (barras con IC 95%) ---
    fig1 = go.Figure()
    for sid in stations_ids:
        vals = df_oee[sid].dropna()
        mean = vals.mean()
        std = vals.std()
        n = len(vals)
        ci = 1.96 * std / np.sqrt(n) if n > 0 else 0
        fig1.add_trace(go.Bar(
            x=[sid], y=[mean],
            error_y=dict(type='data', array=[ci], visible=True, thickness=1.5),
            marker_color=COLOR_OEE,
            name=sid,
            text=[f'{mean:.1%}'], textposition='outside',
            textfont=dict(size=11, color='black')
        ))
    fig1.update_layout(
        title=dict(text='OEE Promedio por Estación', font=dict(size=14)),
        yaxis_title='OEE',
        yaxis=dict(tickformat=',.0%', range=[0, 1.05]),
        template='plotly_white',
        showlegend=False,
        height=350,
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    # --- Gráfico 2: Boxplot de OEE (reemplaza violín) ---
    fig2 = go.Figure()
    for sid in stations_ids:
        fig2.add_trace(go.Box(
            y=df_oee[sid],
            name=sid,
            marker_color=COLOR_OEE,
            boxmean='sd',
            line=dict(width=1)
        ))
    fig2.update_layout(
        title=dict(text='Distribución del OEE', font=dict(size=14)),
        yaxis_title='OEE',
        yaxis=dict(tickformat=',.0%'),
        template='plotly_white',
        showlegend=False,
        height=350,
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    # --- Gráfico 3: Mapa de calor de utilización (escala azul) ---
    fig3 = go.Figure(data=go.Heatmap(
        z=[list(avg_util.values())],
        x=stations_ids,
        y=['Utilización'],
        colorscale=[[0, '#deebf7'], [1, '#08519c']],
        text=[[f'{v:.1%}' for v in avg_util.values()]],
        texttemplate='%{text}',
        textfont=dict(color='white', size=12),
        showscale=False
    ))
    fig3.update_layout(
        title=dict(text='Utilización Media', font=dict(size=14)),
        template='plotly_white',
        height=200,
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    # --- Gráfico 4: Balance de tiempos (barras apiladas) ---
    last_rep = results[-1]
    time_data = []
    for m in last_rep.station_metrics:
        total = m.total_time
        time_data.append({
            'Estación': m.station_id,
            'Trabajo': m.working_time,
            'Fallo': m.downtime,
            'Bloqueo': m.blocked_time,
            'Inanición': m.starved_time
        })
    df_time = pd.DataFrame(time_data)
    fig4 = go.Figure(data=[
        go.Bar(name='Trabajo', x=df_time['Estación'], y=df_time['Trabajo'], marker_color=COLOR_WORK),
        go.Bar(name='Fallo', x=df_time['Estación'], y=df_time['Fallo'], marker_color=COLOR_FAIL),
        go.Bar(name='Bloqueo', x=df_time['Estación'], y=df_time['Bloqueo'], marker_color=COLOR_BLOCK),
        go.Bar(name='Inanición', x=df_time['Estación'], y=df_time['Inanición'], marker_color=COLOR_STARVE)
    ])
    fig4.update_layout(
        title=dict(text='Balance de Tiempos (última réplica)', font=dict(size=14)),
        yaxis_title='Minutos',
        barmode='stack',
        template='plotly_white',
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=350,
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    # --- Componer dashboard ---
    dash = sp.make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'OEE Promedio por Estación',
            'Distribución del OEE',
            'Mapa de Calor de Utilización',
            'Balance de Tiempos'
        ),
        specs=[[{"type": "bar"}, {"type": "box"}],
               [{"type": "heatmap"}, {"type": "bar"}]],
        vertical_spacing=0.10,
        horizontal_spacing=0.08
    )
    # Agregar trazas
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
        title_font=dict(size=16, color='#333'),
        template='plotly_white',
        showlegend=False,
        height=800,
        margin=dict(l=40, r=20, t=60, b=40)
    )
    dash.write_html(output_path, include_plotlyjs='cdn')
    print(f"Dashboard HTML guardado en {output_path}")


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
    
    # 1. OEE promedio con IC
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
    # Agregar etiquetas sobre barras
    for bar, sid in zip(bars, stations_ids):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{height:.1%}', ha='center', va='bottom', fontsize=8, color='black')
    
    # 2. Utilización media
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
    
    # 3. Throughput medio
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
    
    # 4. Cp/Cpk (primera estación)
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
    # Línea de referencia en 1.33
    ax.axhline(y=1.33, color='red', linestyle='--', linewidth=0.8, alpha=0.7)
    ax.text(0, 1.33, '1.33', fontsize=7, color='red', va='bottom')
    
    plt.tight_layout(pad=2.0)
    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    print(f"Resumen PNG guardado en {output_path}")


def generate_excel_report(results: List[ReplicationResult], config, output_path: str = "reports/report.xlsx"):
    """Libro Excel multihoja con datos numéricos."""
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Resumen de réplicas
        summary_rows = []
        for r in results:
            row = {'Réplica': r.replication, 'OEE Global': r.overall_oee}
            for m in r.station_metrics:
                row[f'{m.station_id}_OEE'] = m.oee
                row[f'{m.station_id}_Util'] = m.utilization
            summary_rows.append(row)
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Resumen', index=False)
        
        # Detalle última réplica
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
        
        # Cuellos de botella
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
