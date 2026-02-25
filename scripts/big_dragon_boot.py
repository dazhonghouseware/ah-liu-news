# -*- coding: utf-8 -*-
import os
import sys
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import feedparser
import time
import random
import json
import re
import shutil

# --- 配置区 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 自动读取本地 .env 文件中的 API_KEY
def get_api_key():
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=")[1].strip()
    return "YOUR_KEY_HERE"

API_KEY = get_api_key()
date_str = time.strftime("%Y-%m-%d")
STATUS_FILE = os.path.join(BASE_DIR, f"tiktok_script_{date_str}.md")
TXT_FILE = os.path.join(BASE_DIR, f"today_news_{date_str}.txt")
HTML_FILE = os.path.join(BASE_DIR, f"today_news_{date_str}.html")
BROADCAST_FILE = os.path.join(BASE_DIR, "news_broadcast.html")
IDENTIFIER_WRITER = "【大龙二号 · TikTok爆款文案策划】"
IDENTIFIER_EDITOR = "【大龙一号 · 新加坡本地新闻主编】"

FEEDS = {
    "CNA (Singapore)": "https://www.channelnewsasia.com/rssfeeds/8395986",
    "MSN (MustShareNews)": "https://mustsharenews.com/feed/",
}

SCRAPE_TARGETS = {
    "Zaobao (Singapore)": "https://www.zaobao.com.sg/news/singapore",
    "Mothership (Latest)": "https://mothership.sg/",
}

# --- 编码修正 ---
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # For older Python versions
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def security_check():
    print("========================================")
    print("   大龙自动化系统 (Big Dragon System)   ")
    print("========================================")
    # 正常运行时应该由用户输入，但为了自动化演示，我们这里打印欢迎语
    print("\n[OK] 身份验证通过！欢迎大龙王主人。")
    return True

def fetch_all_news():
    news_items = []
    headers = {'User-Agent': 'Mozilla/5.0...'}
    
    # RSS Feeds
    for source, url in FEEDS.items():
        print(f"大龙一号正在读取 {source} RSS...")
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                news_items.append({"source": source, "title": entry.title, "url": entry.link})
        except: pass

    # Scrape Zaobao
    print("大龙一号正在抓取联合早报...")
    try:
        resp = requests.get(SCRAPE_TARGETS["Zaobao (Singapore)"], timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.select('a.cursor-pointer.touch-auto:not(.content-image)')
        for link in links[:12]:
            t = link.get_text().strip()
            if len(t) < 5: continue
            href = link.get('href', '')
            url = href if href.startswith('http') else "https://www.zaobao.com.sg" + href
            news_items.append({"source": "Zaobao", "title": t, "url": url})
    except: pass

    # Scrape Mothership
    print("大龙一号正在抓取 Mothership...")
    try:
        resp = requests.get(SCRAPE_TARGETS["Mothership (Latest)"], timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        headings = soup.select('.post-item h1 a, .post-item h2 a')
        for h in headings[:10]:
            news_items.append({"source": "Mothership", "title": h.get_text().strip(), "url": h.get('href', '')})
    except: pass
    
    return news_items

def process_with_ai(news_list):
    print(f"大龙二号正在使用 AI 生成全套文案...")
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    random.shuffle(news_list)
    pool = news_list[:15]
    
    prompt = f"""
你现在的身份是：{IDENTIFIER_EDITOR} 兼 {IDENTIFIER_WRITER}。
任务：从以下素材中选出 6 条最值得关注的新加坡本地民生新闻，并生成 JSON 格式的数据。

JSON 结构要求：
{{
  "date": "{date_str}",
  "news": [
    {{
      "id": 1,
      "title": "抓人标题",
      "full_title": "用于播报的详细标题",
      "deep_report": "深度爆料详情。请通过多段落（每段 2-3 句话）和加粗关键信息来增加可读性。直接返回带换行符的纯文本即可。",
      "summary": "150字左右的精简摘要，用于快速阅读",
      "broadcast_text": "用于语音播报的口语化文案，250字左右，语气地道",
      "url": "来源链接",
      "tiktok": {{
         "visual": "画面建议",
         "audio": "TikTok爆款口播（含Singlish，语气要抓人）"
      }}
    }}
  ]
}}

素材池：{pool}
"""
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"AI 失败: {e}")
    return None

def update_all_files(data):
    date = data["date"]
    news = data["news"]
    
    # 1. TXT (精简版)
    with open(TXT_FILE, "w", encoding="utf-8") as f:
        f.write(f"新加坡新闻简报 - {date}\n\n" + "\n\n".join([f"{n['id']}. {n['title']}\n{n['summary']}" for n in news]))
    
    # 2. TikTok Script & Deep Report (Markdown - 用户最喜欢的详细版)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 🎬 大龙全网爆料日报 ({date})\n\n")
        f.write(f"> 身份：{IDENTIFIER_WRITER}\n\n---\n\n")
        for n in news:
            f.write(f"## 📌 第{n['id']}条：{n['title']}\n\n")
            f.write(f"### 📖 深度爆料详情\n{n['deep_report']}\n\n")
            f.write(f"### 🎬 TikTok 爆款脚本策划\n")
            f.write(f"| 画面建议 | 口播文案 |\n| :--- | :--- |\n| {n['tiktok']['visual']} | {n['tiktok']['audio']} |\n\n")
            f.write(f"🔗 [查看原文详情]({n['url']})\n\n---\n\n")

    # 3. HTML (深度详情网页版)
    # 我们直接生成完整的 HTML，不再依赖正则替换，避免出错
    items_html = "".join([f'''
    <div class="news-item">
      <div class="news-tag">#{n["id"]} 今日头条</div>
      <h2>{n["title"]}</h2>
      <div class="summary-box">
        <strong>💡 核心摘要：</strong>{n["summary"]}
      </div>
      <div class="report-box" style="white-space: pre-wrap;">
        {n["deep_report"]}
      </div>
      <div class="action-area">
        <a href="{n["url"]}" target="_blank" class="link-btn">阅读官方来源 →</a>
      </div>
    </div>''' for n in news])

    html_template = f"""<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>新加坡每日深度新闻简报 — {date}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@700;900&family=Outfit:wght@300;400;600&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');
    
    :root {{
      --primary: #8e0000;
      --accent: #ffd700;
      --bg: #fdfcfb;
      --text: #2c3e50;
      --card-bg: #ffffff;
    }}

    body {{ 
      font-family: 'Noto Sans SC', sans-serif; 
      font-size: 18px; 
      line-height: 1.8; 
      background: var(--bg); 
      color: var(--text); 
      padding: 20px;
      margin: 0;
    }}

    .container {{ max-width: 800px; margin: 0 auto; }}

    .header {{ 
      background: linear-gradient(135deg, #1a1a1a, #4a0000); 
      color: white; 
      border-radius: 24px; 
      padding: 60px 20px; 
      margin-bottom: 40px; 
      text-align: center; 
      box-shadow: 0 20px 40px rgba(0,0,0,0.15);
      position: relative;
      overflow: hidden;
    }}

    .header::after {{
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      background: radial-gradient(circle at top right, rgba(255,215,0,0.1), transparent);
    }}

    .editor-id {{ 
      font-size: 16px; 
      color: var(--accent); 
      font-weight: 700; 
      letter-spacing: 2px;
      text-transform: uppercase;
      margin-bottom: 15px;
    }}

    .header h1 {{ 
      font-family: 'Noto Serif SC', serif;
      font-size: 42px; 
      margin: 0;
      font-weight: 900;
      text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }}

    .meta {{ opacity: 0.8; font-size: 14px; margin-top: 10px; }}

    .news-item {{ 
      background: var(--card-bg); 
      border-radius: 24px; 
      padding: 40px; 
      margin-bottom: 40px; 
      box-shadow: 0 10px 30px rgba(0,0,0,0.04); 
      border: 1px solid rgba(0,0,0,0.03);
      transition: transform 0.3s ease;
    }}
    
    .news-item:hover {{ transform: translateY(-5px); }}

    .news-tag {{
      display: inline-block;
      background: rgba(142,0,0,0.05);
      color: var(--primary);
      font-size: 12px;
      font-weight: 700;
      padding: 4px 12px;
      border-radius: 100px;
      margin-bottom: 15px;
    }}

    .news-item h2 {{ 
      font-family: 'Noto Serif SC', serif;
      font-size: 28px; 
      font-weight: 900; 
      margin-top: 0;
      margin-bottom: 25px;
      color: #1a1a1a;
      line-height: 1.3;
    }}

    .summary-box {{
      background: #fbfbfb;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 25px;
      border-left: 4px solid var(--primary);
      font-size: 17px;
    }}

    .report-box {{
      font-size: 19px;
      color: #445;
      line-height: 2;
      border-top: 1px dashed #eee;
      padding-top: 25px;
    }}

    .link-btn {{ 
      display: inline-block;
      text-decoration: none; 
      color: white; 
      background: #1a1a1a; 
      padding: 12px 28px; 
      border-radius: 100px; 
      font-size: 15px; 
      font-weight: 600;
      transition: all 0.2s;
    }}
    
    .link-btn:hover {{ background: var(--primary); transform: scale(1.05); }}

    .action-area {{ margin-top: 30px; text-align: right; }}

    .footer {{ text-align: center; color: #999; padding: 60px 0; font-size: 14px; }}

    @media (max-width: 600px) {{
      .header h1 {{ font-size: 32px; }}
      .news-item {{ padding: 25px; }}
      .news-item h2 {{ font-size: 24px; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="editor-id">{IDENTIFIER_EDITOR}</div>
      <h1>新加坡每日深度简报</h1>
      <div class="meta">{date} ｜ 实时更新 ｜ 深度解析</div>
    </div>
    {items_html}
    <div class="footer">
      <strong>大龙自动化系统</strong> 为您呈现<br>
      让阅读更有深度 ｜ {date}
    </div>
  </div>
</body>
</html>"""
    with open(HTML_FILE, "w", encoding="utf-8") as f: f.write(html_template)

    # 4. Broadcast HTML (播报版)
    try:
        if os.path.exists(BROADCAST_FILE):
            with open(BROADCAST_FILE, "r", encoding="utf-8") as f:
                bc_content = f.read()
            
            bc_news = [{"t": n["full_title"], "c": f"<p>{n['broadcast_text'].replace('\\n', '</p><p>')}</p>"} for n in news]
            bc_content = re.sub(r'const news = \[.*?\];', f'const news = {json.dumps(bc_news, ensure_ascii=False)};', bc_content, flags=re.DOTALL)
            bc_content = re.sub(r'const introScript = ".*?";', f'const introScript = "各位老板好！今天是{date}，大龙一号为您播报6条本地要闻。";', bc_content)
            bc_content = re.sub(r'<div class="meta-info">.*?</div>', f'<div class="meta-info">{date} ｜ 主编：大龙一号</div>', bc_content)
            with open(BROADCAST_FILE, "w", encoding="utf-8") as f: f.write(bc_content)
    except: pass

def main():
    if not security_check(): return
    news_pool = fetch_all_news()
    if not news_pool: return
    data = process_with_ai(news_pool)
    if data:
        update_all_files(data)
        
        # 同步为 index.html 供 Netlify 部署
        index_file = os.path.join(BASE_DIR, "index.html")
        shutil.copy(HTML_FILE, index_file)
        print(f"✅ 今日 ({data['date']}) 所有详细素材已就绪！已更新 index.html")
        
        # 自动推送到 GitHub 以触发 Netlify 部署
        print("🚀 正在自动推送到 GitHub...")
        os.system("git add .")
        os.system('git commit -m "Auto-update news"')
        os.system("git push origin main")
        
        # 自动打开最重要的两个文件
        if os.name == 'nt':
            os.startfile(HTML_FILE)
            os.startfile(STATUS_FILE)

if __name__ == "__main__":
    main()
