import arxiv
import google.generativeai as genai
import datetime
import os
import requests
import json

# 1. 配置与初始化
# 从环境变量读取密钥，确保安全
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
PUSHPLUS_TOKEN = os.getenv('PUSHPLUS_TOKEN')  # 新增：用于微信推送

if not GOOGLE_API_KEY:
    raise ValueError("Error: GOOGLE_API_KEY environment variable not set.")

genai.configure(api_key=GOOGLE_API_KEY)
# 使用 Flash 模型以平衡速度与长文本能力
model = genai.GenerativeModel('gemini-2.5-flash')

def get_latest_papers(topic="Machine Learning", max_results=3):
    """从 ArXiv 获取指定主题的最新论文"""
    print(f"🔍 正在检索关于 {topic} 的最新论文...")
    
    # 构造 search query，按提交时间倒序
    search = arxiv.Search(
        query=topic,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    papers_data = []
    for result in search.results():
        papers_data.append({
            "title": result.title,
            "abstract": result.summary,
            "url": result.entry_id,
            "published": result.published.strftime("%Y-%m-%d")
        })
    return papers_data

def generate_summary(paper):
    """调用 Gemini API 生成中文解读"""
    print(f"🤖 正在研读论文：{paper['title']} ...")
    
    prompt = f"""
    You are an expert academic researcher in Machine Learning. Please analyze the following paper metadata.
    
    Input Data:
    Title: {paper['title']}
    Abstract: {paper['abstract']}
    
    Requirements:
    1. Translate title to Simplified Chinese.
    2. Summarize core content (100-150 words) in Chinese. Be professional but accessible.
    3. List exactly 3 key innovation points (bullet points).
    4. Provide 2-3 tags (e.g., #CV, #LLM).
    5. Output strictly in Markdown format.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 解读失败: {e}"

def send_to_wechat(content):
    """通过 PushPlus 推送到微信"""
    if not PUSHPLUS_TOKEN:
        print("未配置 PUSHPLUS_TOKEN，跳过推送，仅本地打印。")
        return

    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": f"📅 AI 论文日报 ({datetime.date.today()})",
        "content": content,
        "template": "markdown"
    }
    try:
        response = requests.post(url, json=data)
        print(f"📨 推送结果: {response.text}")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

def main():
    # 你可以修改这里的 topic，例如 "Large Language Models" 或 "Diffusion Models"
    papers = get_latest_papers(topic="Machine Learning for PDE", max_results=5)
    
    daily_report = f"# 📅 AI 前沿论文日报 ({datetime.date.today()})\n\n"
    
    for paper in papers:
        summary = generate_summary(paper)
        daily_report += f"## {paper['title']}\n"
        daily_report += f"{summary}\n\n"
        daily_report += f"🔗 **原文链接**: [点击跳转]({paper['url']})\n"
        daily_report += "---\n\n"
    
    print("\n" + "="*20 + " 生成结果 " + "="*20 + "\n")
    print(daily_report)
    
    # 执行推送
    send_to_wechat(daily_report)

if __name__ == "__main__":
    main()
