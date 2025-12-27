import requests
import json
import urllib3

# 抑制SSL警告（若开启verify=False时使用）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===================== 配置项（替换为你的火山方舟信息） =====================
ARK_API_KEY = "6261fd4e-7ac5-46de-95a6-f68f00243230"  # 替换为你的真实API Key
API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
MODEL_ID = "doubao-seed-1-6-251015"  # 与响应中的模型一致
# ===========================================================================

def call_ark_stream_match_response():
    """适配真实响应格式的流式脚本（捕获reasoning_content）"""
    # 1. 构造请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ARK_API_KEY}"
    }

    # 2. 构造请求体（无需多余配置，基础流式即可）
    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "user",
                "content": "天空为什么是蓝色的？请详细解释，分点说明，需要推理过程。"
            }
        ],
        "stream": True  # 仅开启流式，思考内容由模型自动返回（字段为reasoning_content）
    }

    try:
        print(f"正在调用火山方舟流式接口（模型：{MODEL_ID}）")
        print("✅ 流式响应已开启，正在实时接收推理过程与回复...\n")
        
        # 3. 发送请求（按需开启verify=False，解决SSL问题）
        response = requests.post(
            url=API_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=60,
            stream=True,
            verify=False  # 若有SSL错误则保留，无错误可删除
        )

        response.raise_for_status()

        # 4. 初始化存储变量
        full_reasoning = ""  # 完整推理/思考内容
        full_content = ""    # 完整回复内容
        token_usage = None
        finish_reason = None

        # 5. 逐行解析真实流式响应
        for line in response.iter_lines():
            if not line:
                continue  # 跳过空行

            # 解码并过滤SSE格式
            line_str = line.decode("utf-8").strip()
            if not line_str.startswith("data: "):
                continue

            data_str = line_str[len("data: "):]
            if data_str == "[DONE]":
                break  # 流式结束

            # 解析JSON片段（适配真实响应格式）
            try:
                chunk_data = json.loads(data_str)
                choice = chunk_data.get("choices", [{}])[0]
                delta = choice.get("delta", {})

                # 提取推理内容（关键：reasoning_content）
                reasoning_chunk = delta.get("reasoning_content", "")
                # 提取回复内容
                content_chunk = delta.get("content", "")
                # 提取结束原因和Token消耗
                finish_reason = choice.get("finish_reason", finish_reason)
                token_usage = chunk_data.get("usage", token_usage)

                # 实时打印推理内容（青色标注，区分回复）
                if reasoning_chunk:
                    print(f"\033[36m【推理过程】{reasoning_chunk}\033[0m", end="", flush=True)
                    full_reasoning += reasoning_chunk

                # 实时打印回复内容（绿色标注）
                if content_chunk:
                    print(f"\033[32m{content_chunk}\033[0m", end="", flush=True)
                    full_content += content_chunk

            except json.JSONDecodeError:
                # 忽略无效JSON片段，不中断流式解析
                continue

        # 6. 流式结束后汇总信息
        print("\n\n" + "="*60)
        print(f"✅ 流式响应接收完成！")
        # 打印完整推理过程
        print(f"\n【完整推理/思考过程】：\n{full_reasoning if full_reasoning else '模型未返回推理内容'}")
        # 打印完整回复内容
        print(f"\n【完整回复内容】：\n{full_content}")
        # 打印结束原因
        if finish_reason:
            print(f"\n【结束原因】：{finish_reason}（stop=正常结束，length=长度限制）")
        # 打印Token消耗（仅最终chunk有有效数据）
        if token_usage:
            print(f"\n【Token消耗统计】：")
            print(f"  - 总消耗：{token_usage.get('total_tokens', '未知')}")
            print(f"  - 请求消耗：{token_usage.get('prompt_tokens', '未知')}")
            print(f"  - 回复消耗：{token_usage.get('completion_tokens', '未知')}")

        return {
            "full_reasoning": full_reasoning,
            "full_content": full_content,
            "finish_reason": finish_reason,
            "token_usage": token_usage
        }

    except requests.exceptions.HTTPError as e:
        if response.status_code == 400:
            try:
                error_detail = response.json()
                print(f"\n❌ 400错误详情：{error_detail}")
            except:
                print("\n❌ 400 Bad Request：请求体格式错误")
        elif response.status_code == 401:
            print("\n❌ 401未授权：火山方舟API密钥无效")
        else:
            print(f"\n❌ HTTP错误 {response.status_code}：{e}")
    except requests.exceptions.SSLError:
        print("\n❌ SSL连接错误：已开启verify=False，若仍报错请升级Python依赖或更换Python版本")
    except Exception as e:
        print(f"\n❌ 调用失败：{str(e)}")
    return None

if __name__ == "__main__":
    # 执行适配真实响应的流式调用
    call_ark_stream_match_response()