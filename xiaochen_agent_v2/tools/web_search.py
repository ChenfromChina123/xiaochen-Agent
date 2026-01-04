"""
网络搜索工具模块
提供实时网络搜索能力，支持多个搜索引擎
"""
import re
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urljoin

try:
    import requests
except Exception:
    requests = None


def truncate_text(text: str, max_length: int = 500) -> str:
    """
    截断文本到指定长度，减少token消耗
    
    Args:
        text: 原始文本
        max_length: 最大长度
    
    Returns:
        截断后的文本
    """
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def clean_html_tags(text: str) -> str:
    """
    清理HTML标签，但保留基本排版（换行）
    
    Args:
        text: 包含HTML的文本
    
    Returns:
        清理后的纯文本
    """
    if not text:
        return ""
    
    # 替换块级标签为换行
    text = re.sub(r'<(p|div|br|h[1-6]|li|tr)[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(p|div|h[1-6]|li|tr)>', '\n', text, flags=re.IGNORECASE)
    
    # 移除 script 和 style
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除其他HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 处理HTML实体 (简单处理)
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')
    
    # 移除多余空白
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if line:
            lines.append(line)
            
    return "\n".join(lines)


def visit_page(url: str, timeout: int = 30) -> Tuple[bool, str, str]:
    """
    访问网页并提取正文内容
    
    Args:
        url: 网页URL
        timeout: 超时时间（秒）
    
    Returns:
        (是否成功, 错误信息, 网页正文内容)
    """
    if not requests:
        return False, "requests库未安装", ""
        
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # 尝试检测编码
        response.encoding = response.apparent_encoding
        
        html = response.text
        text = clean_html_tags(html)
        
        # 截断过长的内容 (例如保留前10000字符，避免撑爆context)
        # 这里先不截断，让Agent自己决定读取多少，或者在Agent层做截断
        # 但考虑到token成本，还是做个软限制比较好
        if len(text) > 20000:
             text = text[:20000] + "\n\n(内容过长，已截断...)"
             
        return True, "", text
        
    except requests.exceptions.Timeout:
        return False, f"访问超时（{timeout}秒）", ""
    except requests.exceptions.RequestException as e:
        return False, f"访问失败: {str(e)}", ""
    except Exception as e:
        return False, f"处理异常: {str(e)}", ""


def search_duckduckgo(query: str, max_results: int = 5, timeout: int = 30) -> Tuple[bool, str, List[Dict[str, str]]]:
    """
    使用DuckDuckGo搜索（通过HTML抓取）
    
    Args:
        query: 搜索关键词
        max_results: 最大结果数量
        timeout: 超时时间（秒）
    
    Returns:
        (是否成功, 错误信息, 搜索结果列表)
    """
    if not requests:
        return False, "requests库未安装", []
    
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        html = response.text
        results = []
        
        # 简单的HTML解析，提取搜索结果
        # 匹配结果块
        pattern = r'class="result__title"><a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>.*?class="result__snippet">([^<]+)'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for match in matches[:max_results]:
            link, title, snippet = match
            results.append({
                "title": clean_html_tags(title.strip()),
                "link": link.strip(),
                "snippet": truncate_text(clean_html_tags(snippet.strip()), 200)
            })
        
        if not results:
            return True, "", []
        
        return True, "", results
        
    except requests.exceptions.Timeout:
        return False, f"搜索超时（{timeout}秒）", []
    except requests.exceptions.RequestException as e:
        return False, f"网络请求失败: {str(e)}", []
    except Exception as e:
        return False, f"搜索异常: {str(e)}", []


def search_bing(query: str, max_results: int = 5, timeout: int = 30) -> Tuple[bool, str, List[Dict[str, str]]]:
    """
    使用Bing搜索（简单HTML抓取）
    
    Args:
        query: 搜索关键词
        max_results: 最大结果数量
        timeout: 超时时间（秒）
    
    Returns:
        (是否成功, 错误信息, 搜索结果列表)
    """
    if not requests:
        return False, "requests库未安装", []
    
    try:
        url = f"https://www.bing.com/search?q={quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        html = response.text
        results = []
        
        # 简单的HTML解析
        # 优化正则：允许标题中包含标签（如 <strong>），并匹配摘要
        pattern = r'<h2[^>]*><a[^>]+href="([^"]+)"[^>]*>(.*?)</a></h2>.*?<p[^>]*>(.*?)</p>'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for match in matches[:max_results]:
            link, title, snippet = match
            results.append({
                "title": clean_html_tags(title.strip()),
                "link": link.strip(),
                "snippet": truncate_text(clean_html_tags(snippet.strip()), 300)
            })
        
        if not results:
            return True, "", []
        
        return True, "", results
        
    except requests.exceptions.Timeout:
        return False, f"搜索超时（{timeout}秒）", []
    except requests.exceptions.RequestException as e:
        return False, f"网络请求失败: {str(e)}", []
    except Exception as e:
        return False, f"搜索异常: {str(e)}", []


def web_search(
    query: str, 
    engine: str = "bing",
    max_results: int = 5, 
    timeout: int = 30
) -> Tuple[bool, str, List[Dict[str, str]]]:
    """
    统一的网络搜索接口，支持自动故障转移
    
    Args:
        query: 搜索关键词
        engine: 首选搜索引擎 (duckduckgo, bing)
        max_results: 最大结果数量（限制在1-10之间）
        timeout: 超时时间（秒）
    
    Returns:
        (是否成功, 错误信息, 搜索结果列表)
    """
    if not query or not query.strip():
        return False, "搜索关键词不能为空", []
    
    # 限制查询长度，减少token
    query = query.strip()[:200]
    
    # 限制结果数量
    max_results = max(1, min(max_results, 10))
    
    engine = engine.lower().strip()
    
    # 自动故障转移逻辑
    if engine == "bing":
        success, error, results = search_bing(query, max_results, timeout)
        if success:
            return True, "", results
        # Bing失败，尝试DuckDuckGo
        return search_duckduckgo(query, max_results, timeout)
    else:
        # 默认使用DuckDuckGo
        success, error, results = search_duckduckgo(query, max_results, timeout)
        if success:
            return True, "", results
        # DuckDuckGo失败，尝试Bing
        return search_bing(query, max_results, timeout)


def format_search_results(results: List[Dict[str, str]], query: str) -> str:
    """
    格式化搜索结果为易读文本
    
    Args:
        results: 搜索结果列表
        query: 搜索关键词
    
    Returns:
        格式化的结果文本
    """
    if not results:
        return f"未找到关于 '{query}' 的搜索结果"
    
    lines = [f"搜索关键词: {query}", f"找到 {len(results)} 条结果:\n"]
    
    for i, result in enumerate(results, 1):
        title = result.get("title", "无标题")
        link = result.get("link", "")
        snippet = result.get("snippet", "无摘要")
        
        lines.append(f"{i}. {title}")
        lines.append(f"   链接: {link}")
        lines.append(f"   摘要: {snippet}")
        lines.append("")
    
    return "\n".join(lines)
