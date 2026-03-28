import time
from xiaochen_agent_v2.utils.web_search import web_search

def run_search_test(query, description):
    print(f"\n{'='*20}\n测试场景: {description}\n查询词: [{query}]\n{'='*20}")
    start_time = time.time()
    success, error, results = web_search(query, max_results=3)
    duration = time.time() - start_time
    
    if success:
        print(f"✅ 搜索成功 (耗时: {duration:.2f}s)")
        if not results:
            print("⚠️  警告: 返回结果为空列表 []")
        for i, res in enumerate(results):
            print(f"[{i+1}] {res['title']}")
            print(f"    Link: {res['link']}")
            print(f"    Snippet: {res['snippet'][:100]}...")
    else:
        print(f"❌ 搜索失败 (耗时: {duration:.2f}s)")
        print(f"    Error: {error}")

def main():
    test_cases = [
        ("Python requests documentation", "英文技术文档"),
        ("2024年巴黎奥运会金牌榜", "中文时事/数字"),
        ("C++ std::vector用法", "包含特殊字符的编程问题"),
        ("Rust 语言官网", "寻找官方网站 (类似 DeepSeek 场景)"),
    ]
    
    print("开始通用网络搜索测试...")
    for query, desc in test_cases:
        run_search_test(query, desc)
        # 避免请求过快被封禁
        time.sleep(2)

if __name__ == "__main__":
    main()
