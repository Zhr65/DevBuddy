import json
from openai import OpenAI

client = OpenAI(
    api_key = "",
    base_url = "",
)
MODEL = ""

def get_weather(city: str) -> str:
    return f"{city}的天气是晴朗的"
    # 实际实现中，从天气API获取天气数据

TOOLS = {
    "get_weather": get_weather,
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "funtion": {
            "name": "get_weather",
            "description": "Get the weather in a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {                        "description": "The city to get the weather for",
                        "type": "string",
                    },
                },
                "required": ["city"],
            },
            "return_direct": True,
        }
    }
]
messages = [
    {"role": "system", "content": "你是一个天气助手，只能回答关于天气的问题。"}
]

def run_agent(user_input: str, max_steps: int = 5) -> str:
    messages.append({"role": "user", "content": user_input})

    for step in range(max_steps):
        resp = client.chat.completions.create(
            model = MODEL,
            messages = messages,
            tools = TOOLS_SCHEMA,
            temperature = 0.3,
        )
        msg = resp.choices[0].message

        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                tool_name = tc.function.name
                print(f"  [Agent 想调用工具] {tool_name}({args})")
                result = TOOLS[tool_name](**args)
                print(f"  [工具返回结果] {result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
                continue
            else:
                messages.append({"role": "assistant", "content": msg.content})
                return msg.content
        return "Agent 超出最大步数"
                

def main():
    print("=== 模块3 Function Calling Agent（q 退出）===\n")
    while True:
        user_input = input("你> ").strip()
        if user_input.lower() == "q":
            break
        if not user_input:
            continue
        print("AI>", run_agent(user_input), "\n")       


if __name__ == "__main__":
    main()