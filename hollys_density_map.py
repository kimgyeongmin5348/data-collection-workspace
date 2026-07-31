"""
할리스 매장 상권 분석 모던 대시보드 리포트 생성 스크립트

실행:
    python main.py

결과물:
    output/hollys_report.html (브라우저로 열어보면 완전히 새로워진 대시보드 형태를 확인할 수 있습니다)
"""

import base64
import io
import os
import platform
import json

import folium
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
SOURCE_DIR = "source"
OUTPUT_DIR = "output"

STORE_GEO = f"{SOURCE_DIR}/hollys_store_geo_kakao_final.csv"
ANALYSIS = f"{SOURCE_DIR}/hollys_population_analysis.csv"
GEOJSON = f"{SOURCE_DIR}/skorea-provinces-2018-geo.json"
REPORT_HTML = f"{OUTPUT_DIR}/hollys_report.html"


def set_korean_font():
    system = platform.system()
    if system == "Windows":
        family = "Malgun Gothic"
    elif system == "Darwin":
        family = "AppleGothic"
    else:
        family = "NanumBarunGothic"
    plt.rcParams["font.family"] = family
    plt.rcParams["axes.unicode_minus"] = False


def load_data():
    store_path = STORE_GEO if os.path.exists(STORE_GEO) else "hollys_store_geo_kakao_final.csv"
    
    if os.path.exists(ANALYSIS):
        df_merge = pd.read_csv(ANALYSIS)
    else:
        df_store_temp = pd.read_csv(store_path)
        store_count = df_store_temp["시도"].value_counts().reset_index()
        store_count.columns = ["시도", "매장수"]
        pop_path = f"{SOURCE_DIR}/population_sido.csv" if os.path.exists(f"{SOURCE_DIR}/population_sido.csv") else "population_sido.csv"
        df_pop = pd.read_csv(pop_path)
        df_merge = store_count.merge(df_pop, on="시도", how="inner")
        df_merge["10만명당_매장수"] = (df_merge["매장수"] / df_merge["인구"]) * 100000

    df_store = pd.read_csv(store_path)
    
    geojson_path = GEOJSON if os.path.exists(GEOJSON) else "source/skorea-provinces-2018-geo.json"
    with open(geojson_path, encoding="utf-8") as f:
        geo = json.load(f)
        
    return df_store, df_merge, geo


def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    return f'<img src="data:image/png;base64,{encoded}" style="width:100%; height:auto; border-radius: 8px;">'


def make_barplot_html(df_merge: pd.DataFrame) -> str:
    # 모던한 스타일의 그래프 배경 및 색상 적용
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#ffffff')
    ax.set_facecolor('#ffffff')
    
    data = df_merge.sort_values("10만명당_매장수", ascending=False)
    
    # 그라데이션 느낌을 주는 단일 세련된 컬러톤 사용
    bars = ax.bar(data["시도"], data["10만명당_매장수"], color="#e74c3c", alpha=0.85, width=0.6, edgecolor="#c0392b", linewidth=1)
    
    ax.set_title("시도별 인구 10만 명당 할리스 매장 밀도", fontsize=13, fontweight='bold', pad=15, color="#2c3e50")
    ax.set_xlabel("지역 (시도)", fontsize=10, fontweight='bold', color="#7f8c8d")
    ax.set_ylabel("10만 명당 매장 수", fontsize=10, fontweight='bold', color="#7f8c8d")
    
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9, color="#34495e")
    plt.setp(ax.get_yticklabels(), fontsize=9, color="#34495e")
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#bdc3c7')
    ax.spines['bottom'].set_color('#bdc3c7')
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4),  # 4 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, color='#2c3e50', fontweight='bold')

    fig.tight_layout()
    return fig_to_base64(fig)


def make_map_html(df_store: pd.DataFrame, df_merge: pd.DataFrame, geo: dict) -> str:
    m = folium.Map(location=[36.2, 127.8], zoom_start=7, tiles="CartoDB positron")

    folium.Choropleth(
        geo_data=geo,
        data=df_merge,
        columns=["시도", "10만명당_매장수"],
        key_on="feature.properties.name",
        fill_color="YlOrRd",
        fill_opacity=0.65,
        line_opacity=0.4,
        legend_name="10만명당 매장 수",
    ).add_to(m)

    ok = df_store.dropna(subset=["위도", "경도"])
    for _, row in ok.iterrows():
        name = row.get('매장명', '할리스 매장')
        addr = row.get('주소', '')
        popup_content = f"<div style='font-family:sans-serif;'><b>{name}</b><br><span style='font-size:11px; color:#555;'>{addr}</span></div>"
        
        folium.CircleMarker(
            location=[row["위도"], row["경도"]],
            radius=3.5,
            popup=folium.Popup(popup_content, max_width=250),
            color="#2980b9", fill=True, fill_color="#3498db", fill_opacity=0.9,
            weight=1,
            tooltip=name
        ).add_to(m)

    return m.get_root().render()


# ---------------------------------------------------------------------------
# 대시보드 HTML 템플릿 (사이드바 + 카드 레이아웃)
# ---------------------------------------------------------------------------
DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>할리스 커피 상권 분석 대시보드</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
      font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
      margin: 0;
      padding: 0;
      background-color: #f4f6f9;
      color: #333;
      display: flex;
      min-height: 100vh;
  }}
  /* 사이드바 스타일 */
  sidebar {{
      width: 280px;
      background-color: #1e293b;
      color: #fff;
      padding: 30px 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
  }}
  sidebar h2 {{
      font-size: 20px;
      color: #f8fafc;
      margin-top: 0;
      border-bottom: 2px solid #334155;
      padding-bottom: 15px;
  }}
  .badge {{
      background: #e74c3c;
      color: white;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: bold;
      text-transform: uppercase;
  }}
  .sidebar-info {{
      font-size: 13px;
      color: #94a3b8;
      line-height: 1.6;
      margin-top: 20px;
  }}
  /* 메인 컨텐츠 영역 */
  .main-content {{
      flex: 1;
      padding: 40px;
      overflow-y: auto;
  }}
  header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 30px;
  }}
  header h1 {{
      margin: 0;
      font-size: 26px;
      color: #1e293b;
  }}
  header p {{
      margin: 5px 0 0 0;
      color: #64748b;
      font-size: 14px;
  }}
  /* 카드 컨테이너 */
  .card {{
      background: #ffffff;
      border-radius: 12px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
      padding: 24px;
      margin-bottom: 30px;
  }}
  .card h3 {{
      margin-top: 0;
      font-size: 16px;
      color: #334155;
      border-left: 4px solid #e74c3c;
      padding-left: 10px;
      margin-bottom: 20px;
  }}
  .grid-2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 30px;
  }}
  @media (max-width: 1200px) {{
      .grid-2 {{ grid-template-columns: 1fr; }}
      body {{ flex-direction: column; }}
      sidebar {{ width: 100%; }}
  }}
  iframe {{
      width: 100%;
      height: 500px;
      border: none;
      border-radius: 8px;
  }}
  /* 테이블 디자인 */
  table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
  }}
  th {{
      background-color: #f1f5f9;
      color: #475569;
      font-weight: 600;
      padding: 12px;
      border-bottom: 2px solid #e2e8f0;
  }}
  td {{
      padding: 10px 12px;
      border-bottom: 1px solid #f1f5f9;
      color: #334155;
  }}
  tr:hover {{ background-color: #f8fafc; }}
</style>
</head>
<body>

  <!-- 사이드바 -->
  <sidebar>
    <div>
      <span class="badge">Analytics Dashboard</span>
      <h2>☕ Holly's BI</h2>
      <div class="sidebar-info">
        <p><b>데이터 소스:</b><br>· 할리스 공식 매장 정보<br>· 행정구역별 인구수 데이터<br>· 카카오 로컬 좌표 변환 API</p>
        <p><b>분석 지표:</b><br>지역별 인구수 대비 매장 밀도 및 상권 분포 현황 시각화</p>
      </div>
    </div>
    <div style="font-size: 11px; color: #64748b; border-top: 1px solid #334155; padding-top: 15px;">
      Designed for Store Expansion Strategy
    </div>
  </sidebar>

  <!-- 메인 패널 -->
  <div class="main-content">
    <header>
      <div>
        <h1>할리스 커피 상권 분석 대시보드</h1>
        <p>인구 밀도 기반 지역별 매장 분포 및 인프라 현황 종합 리포트</p>
      </div>
    </header>

    <!-- 1단: 지도와 그래프 배치 -->
    <div class="grid-2">
      <div class="card">
        <h3>📍 지역별 분포 및 매장 위치 지도</h3>
        <iframe srcdoc="{map_srcdoc}"></iframe>
      </div>
      <div class="card">
        <h3>📊 인구 10만 명당 매장 밀도</h3>
        {barplot}
      </div>
    </div>

    <!-- 2단: 상세 데이터 테이블 -->
    <div class="card">
      <h3>📋 시도별 상세 분석 데이터</h3>
      <div style="overflow-x: auto;">
        {table}
      </div>
    </div>
  </div>

</body>
</html>
"""


def build_dashboard():
    set_korean_font()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df_store, df_merge, geo = load_data()

    barplot_html = make_barplot_html(df_merge)
    
    # 순위표에 정렬 적용
    df_sorted = df_merge.sort_values("10만명당_매장수", ascending=False).round(2)
    table_html = df_sorted.to_html(index=False, classes="dashboard-table")
    
    map_html = make_map_html(df_store, df_merge, geo)
    map_srcdoc = map_html.replace('"', "&quot;")

    final_html = DASHBOARD_TEMPLATE.format(
        barplot=barplot_html,
        table=table_html,
        map_srcdoc=map_srcdoc,
    )

    with open(REPORT_HTML, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"모던 대시보드 생성 완료: {REPORT_HTML}")


if __name__ == "__main__":
    build_dashboard()