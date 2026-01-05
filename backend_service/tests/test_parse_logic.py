
def mock_parse(result):
    formatted_data = []
    if result and isinstance(result, list) and len(result) > 0 and result[0] is not None:
        for line in result[0]:
            try:
                if not isinstance(line, list) or len(line) < 2:
                    continue
                    
                box = line[0]
                res = line[1]
                
                if isinstance(res, tuple) or isinstance(res, list):
                    if len(res) >= 2:
                        text, score = res[0], res[1]
                    else:
                        text, score = res[0], 0.0
                else:
                    text, score = str(res), 0.0
                    
                formatted_data.append({
                    "text": text,
                    "box": box,
                    "score": score
                })
            except Exception as e:
                print(f"Error: {e}")
    return formatted_data

# 测试正常情况
res1 = [ [ [ [[0,0],[1,0],[1,1],[0,1]], ("hello", 0.9) ] ] ]
print(f"Test 1: {mock_parse(res1)}")

# 测试只有文本的情况
res2 = [ [ [ [[0,0],[1,0],[1,1],[0,1]], ["world"] ] ] ]
print(f"Test 2: {mock_parse(res2)}")

# 测试只有字符串的情况
res3 = [ [ [ [[0,0],[1,0],[1,1],[0,1]], "simple text" ] ] ]
print(f"Test 3: {mock_parse(res3)}")
