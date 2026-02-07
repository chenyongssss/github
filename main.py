import arxiv
import google.generativeai as genai
import datetime
import os
import requests
import time # 引入时间库

# 1. 配置与初始化
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
PUSHPLUS_TOKEN = os.getenv('PUSHPLUS_TOKEN')

if not GOOGLE_API_KEY:
    raise ValueError("Error: GOOGLE_API_KEY environment variable not set.")

genai.configure(api_key=GOOGLE_API_KEY)
# 使用 Pro 模型
model = genai.GenerativeModel('gemini-2.5-flash')

def get_latest_papers(topic, max_results=5):
    """从 ArXiv 获取指定主题的最新论文（防限流版）"""
    print(f"🔍 正在检索关于 {topic} 的最新论文...")
    
    # 构造 search query
    search = arxiv.Search(
        query=topic,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    # 🌟 关键修改：使用 Client 来控制请求频率
    # page_size: 每次请求获取多少篇
    # delay_seconds: 请求间隔时间（防封号）
    # num_retries: 失败自动重试次数
    client = arxiv.Client(
        page_size=5,
        delay_seconds=3,
        num_retries=3
    )

    papers_data = []
    try:
        # 使用 client.results(search) 替代原来的 search.results()
        for result in client.results(search):
            papers_data.append({
                "title": result.title,
                "abstract": result.summary,
                "url": result.entry_id,
                "published": result.published.strftime("%Y-%m-%d")
            })
    except Exception as e:
        print(f"⚠️ ArXiv 检索出错 (可能是网络波动): {e}")
        # 如果出错，返回空列表，避免整个程序崩溃
        return []
        
    return papers_data

def generate_summary(paper):
    """调用 Gemini API 生成中文解读"""
    print(f"🤖 正在研读论文：{paper['title']} ...")
    
    prompt = f"""
    You are an expert academic researcher. Please analyze the following paper metadata.
    
    Input Data:
    Title: {paper['title']}
    Abstract: {paper['abstract']}
    
    Requirements:
    1. Translate title to Simplified Chinese.
    2. Summarize core content (100-150 words) in Chinese. Be professional but accessible.
    3. List exactly 3 key innovation points (bullet points).
    4. Provide 2-3 tags (e.g., #SciML, #PDE).
    5. Output strictly in Markdown format.
    """
    
    try:
        # 增加一个小的延迟，避免 Gemini API 也过载
        time.sleep(2)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 解读失败: {e}"

def send_to_wechat(content):
    """通过 PushPlus 推送到微信"""
    if not PUSHPLUS_TOKEN:
        print("⚠️ 未配置 PUSHPLUS_TOKEN，跳过推送。")
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
    # --- 针对你 Research Experience 定制的查询 ---
    # 我们稍微简化了查询语句，去掉了括号嵌套，使其更符合 ArXiv 的偏好
    # 重点关注 SciML, Neural Operators 和 Transport/Hamiltonian
    custom_topic = '("Scientific Machine Learning" OR "Neural Operator" OR "Flow Matching" OR "Hamiltonian Neural")'
    
    # 获取论文
    papers = get_latest_papers(topic=custom_topic, max_results=3)
    
    if not papers:
        print("❌ 本次未检索到论文或连接被拒绝，请稍后再试。")
        return

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
